# Bitcoin Tracker

Bitcoin Tracker is an informational dashboard and command-line tool for viewing public Bitcoin market data. It displays the current USD price, 24-hour change, high, low, market capitalization, volume, and historical price charts.

The project does not connect to wallets, place trades, recommend transactions, or predict future prices.

## Web dashboard

Open `bitcoin_tracker.html` directly in a modern browser. For the most reliable browser behavior, serve the folder locally:

```bash
python -m http.server 8000
```

Then visit `http://localhost:8000/bitcoin_tracker.html`.

The page requests public market data from CoinGecko. If the request is unavailable or rate-limited, it switches to clearly labeled demonstration data.

## Python tracker

The Python tool uses only the standard library.

Fetch and save a live snapshot:

```bash
python bitcoin_tracker.py snapshot
```

Test without network access:

```bash
python bitcoin_tracker.py snapshot --offline-demo
```

View recent saved snapshots:

```bash
python bitcoin_tracker.py history --limit 10
```

Summarize saved prices:

```bash
python bitcoin_tracker.py report
```

## Tests

```bash
python -m unittest -v
```

## Data source

Live market data is requested from the public CoinGecko API. Availability and rate limits are controlled by the data provider.

## Notice

This project is for education and informational market tracking. It does not provide financial advice.
