#!/usr/bin/env python3
"""Informational Bitcoin market-data tracker.

Fetches public Bitcoin market data from CoinGecko, stores optional local
snapshots, and reports descriptive statistics. It does not place trades,
connect to wallets, or make price predictions.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = (
    "https://api.coingecko.com/api/v3/coins/bitcoin"
    "?localization=false&tickers=false&market_data=true"
    "&community_data=false&developer_data=false&sparkline=false"
)
HISTORY_FILE = Path("bitcoin_price_history.json")


def fetch_json(url: str, timeout: int = 15) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "BitcoinTracker/1.0",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def normalize_market_data(payload: dict[str, Any]) -> dict[str, Any]:
    market = payload.get("market_data") or {}
    current = market.get("current_price") or {}
    high = market.get("high_24h") or {}
    low = market.get("low_24h") or {}
    market_cap = market.get("market_cap") or {}
    volume = market.get("total_volume") or {}
    change = market.get("price_change_percentage_24h")

    if current.get("usd") is None:
        raise ValueError("API response did not include a USD Bitcoin price")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "CoinGecko",
        "price_usd": float(current["usd"]),
        "high_24h_usd": float(high["usd"]) if high.get("usd") is not None else None,
        "low_24h_usd": float(low["usd"]) if low.get("usd") is not None else None,
        "market_cap_usd": float(market_cap["usd"]) if market_cap.get("usd") is not None else None,
        "volume_24h_usd": float(volume["usd"]) if volume.get("usd") is not None else None,
        "change_24h_percent": float(change) if change is not None else None,
    }


def demo_snapshot() -> dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Offline demo",
        "price_usd": 64250.00,
        "high_24h_usd": 65180.00,
        "low_24h_usd": 62940.00,
        "market_cap_usd": 1_270_000_000_000.00,
        "volume_24h_usd": 31_500_000_000.00,
        "change_24h_percent": 1.84,
    }


def load_history(path: Path = HISTORY_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    snapshots = payload.get("snapshots", [])
    if not isinstance(snapshots, list):
        raise ValueError("History file has an invalid snapshots field")
    return snapshots


def save_snapshot(snapshot: dict[str, Any], path: Path = HISTORY_FILE) -> int:
    snapshots = load_history(path)
    snapshots.append(snapshot)
    path.write_text(
        json.dumps({"version": 1, "snapshots": snapshots}, indent=2),
        encoding="utf-8",
    )
    return len(snapshots)


def summarize(snapshots: list[dict[str, Any]]) -> dict[str, float | int]:
    prices = [float(row["price_usd"]) for row in snapshots if row.get("price_usd") is not None]
    if not prices:
        return {"count": 0}
    return {
        "count": len(prices),
        "minimum": min(prices),
        "maximum": max(prices),
        "average": statistics.fmean(prices),
        "latest": prices[-1],
    }


def money(value: float | None) -> str:
    return "Unavailable" if value is None else f"${value:,.2f}"


def compact_money(value: float | None) -> str:
    if value is None:
        return "Unavailable"
    for amount, suffix in ((1_000_000_000_000, "T"), (1_000_000_000, "B"), (1_000_000, "M")):
        if abs(value) >= amount:
            return f"${value / amount:,.2f}{suffix}"
    return money(value)


def print_snapshot(snapshot: dict[str, Any]) -> None:
    change = snapshot.get("change_24h_percent")
    change_text = "Unavailable" if change is None else f"{change:+.2f}%"
    print("Bitcoin Tracker")
    print("=" * 48)
    print(f"Price:            {money(snapshot.get('price_usd'))}")
    print(f"24-hour change:   {change_text}")
    print(f"24-hour high:     {money(snapshot.get('high_24h_usd'))}")
    print(f"24-hour low:      {money(snapshot.get('low_24h_usd'))}")
    print(f"Market cap:       {compact_money(snapshot.get('market_cap_usd'))}")
    print(f"24-hour volume:   {compact_money(snapshot.get('volume_24h_usd'))}")
    print(f"Updated:          {snapshot['timestamp']}")
    print(f"Source:           {snapshot['source']}")


def command_snapshot(args: argparse.Namespace) -> int:
    if args.offline_demo:
        snapshot = demo_snapshot()
    else:
        try:
            snapshot = normalize_market_data(fetch_json(API_URL))
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            print(f"Unable to fetch live market data: {error}", file=sys.stderr)
            print("Run with --offline-demo to test without network access.", file=sys.stderr)
            return 1

    print_snapshot(snapshot)
    if not args.no_save:
        count = save_snapshot(snapshot, Path(args.history_file))
        print(f"\nSaved local snapshot #{count} to {args.history_file}")
    return 0


def command_history(args: argparse.Namespace) -> int:
    snapshots = load_history(Path(args.history_file))
    if not snapshots:
        print("No saved snapshots yet.")
        return 0
    limit = max(1, args.limit)
    for row in snapshots[-limit:]:
        change = row.get("change_24h_percent")
        change_text = "n/a" if change is None else f"{float(change):+.2f}%"
        print(f"{row['timestamp']}  {money(float(row['price_usd'])):>14}  24h {change_text:>8}  {row.get('source', 'Unknown')}")
    return 0


def command_report(args: argparse.Namespace) -> int:
    snapshots = load_history(Path(args.history_file))
    report = summarize(snapshots)
    if report["count"] == 0:
        print("No saved snapshots available for a report.")
        return 0
    print("Saved Snapshot Summary")
    print("=" * 48)
    print(f"Snapshots: {report['count']}")
    print(f"Minimum:   {money(float(report['minimum']))}")
    print(f"Maximum:   {money(float(report['maximum']))}")
    print(f"Average:   {money(float(report['average']))}")
    print(f"Latest:    {money(float(report['latest']))}")
    print("\nThese are descriptive statistics, not a price forecast.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track informational Bitcoin market data.")
    parser.add_argument(
        "--history-file",
        default=str(HISTORY_FILE),
        help="Local JSON snapshot file (default: bitcoin_price_history.json)",
    )
    subparsers = parser.add_subparsers(dest="command")

    snapshot = subparsers.add_parser("snapshot", help="Fetch and optionally save current market data")
    snapshot.add_argument("--offline-demo", action="store_true", help="Use clearly labeled sample data")
    snapshot.add_argument("--no-save", action="store_true", help="Display without saving a snapshot")
    snapshot.set_defaults(handler=command_snapshot)

    history = subparsers.add_parser("history", help="Display recent local snapshots")
    history.add_argument("--limit", type=int, default=10)
    history.set_defaults(handler=command_history)

    report = subparsers.add_parser("report", help="Summarize saved snapshot prices")
    report.set_defaults(handler=command_report)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        args.command = "snapshot"
        args.offline_demo = False
        args.no_save = False
        args.handler = command_snapshot
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
