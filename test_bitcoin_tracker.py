import json
import tempfile
import unittest
from pathlib import Path

import bitcoin_tracker


class BitcoinTrackerTests(unittest.TestCase):
    def test_normalize_market_data(self):
        payload = {
            "market_data": {
                "current_price": {"usd": 65000},
                "high_24h": {"usd": 66000},
                "low_24h": {"usd": 63000},
                "market_cap": {"usd": 1_280_000_000_000},
                "total_volume": {"usd": 30_000_000_000},
                "price_change_percentage_24h": 2.5,
            }
        }
        result = bitcoin_tracker.normalize_market_data(payload)
        self.assertEqual(result["price_usd"], 65000.0)
        self.assertEqual(result["change_24h_percent"], 2.5)
        self.assertEqual(result["source"], "CoinGecko")

    def test_save_and_summarize(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "history.json"
            first = bitcoin_tracker.demo_snapshot()
            second = dict(first, price_usd=65000.0)
            bitcoin_tracker.save_snapshot(first, path)
            bitcoin_tracker.save_snapshot(second, path)
            rows = bitcoin_tracker.load_history(path)
            summary = bitcoin_tracker.summarize(rows)
            self.assertEqual(summary["count"], 2)
            self.assertEqual(summary["minimum"], first["price_usd"])
            self.assertEqual(summary["maximum"], 65000.0)

    def test_invalid_history_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "history.json"
            path.write_text(json.dumps({"snapshots": "not-a-list"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                bitcoin_tracker.load_history(path)


if __name__ == "__main__":
    unittest.main()
