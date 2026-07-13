# Books Scraper

A professional scraper for the [books.toscrape.com](https://books.toscrape.com)
catalogue—a public site built specifically for practicing web scraping. It walks
all 50 catalogue pages, validates each of the ~1000 books with pydantic and
persists them into DuckDB, with exports to CSV and Parquet. Terminal output uses
[rich](https://github.com/Textualize/rich) (progress bar and tables) and the
whole interface is a [typer](https://typer.tiangolo.com/) CLI.

## Features

- **Automatic pagination** following the `next` link until the catalogue is exhausted.
- **Rate limiting** with a configurable delay + random jitter of ±30% to avoid
  producing a robotic request pattern.
- **Selective retries** with exponential backoff (tenacity): retries only on
  5xx and timeouts; a 404 is not retried.
- **Per-record validation** with pydantic: a dirty record raises a warning and is
  dropped, the pipeline never crashes.
- **Identifiable User-Agent** and a `robots.txt` check at startup.
- **DuckDB persistence** with native exports to CSV and Parquet.
- **Rich output** in the terminal: a live progress bar and summary, ratings and top 10 tables.

## Requirements

- Python 3.12+
- The dependencies in [`requirements.txt`](requirements.txt) (httpx, BeautifulSoup4 + lxml,
  pydantic, tenacity, DuckDB, rich, typer, pytest).

## Installation

```bash
python -m venv .venv
```

Activate the virtual environment depending on your shell:

```bash
.venv\Scripts\Activate.ps1     # Windows (PowerShell)
source .venv/Scripts/activate  # Windows (Git Bash)
source .venv/bin/activate      # Linux / macOS
```

And install the project with its dependencies:

```bash
pip install -r requirements.txt
pip install -e .
```

## Usage

```bash
# Full crawl (50 pages, ~1000 books)
python -m scraper crawl --pages 50 --delay 0.4 --db books.duckdb

# Top 10 books by rating and price
python -m scraper stats --db books.duckdb

# Export to CSV or Parquet
python -m scraper export --format csv
python -m scraper export --format parquet --output catalogue.parquet
```

Each command documents its options with `--help` (e.g. `python -m scraper crawl --help`).

### Sample output

When the crawl finishes it prints a summary like this:

```
       Crawl summary                 Rating distribution
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━┓        ┏━━━━━━━━┳━━━━━━━━┓
┃ Metric          ┃  Value ┃        ┃ Rating ┃  Books ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━┩        ┡━━━━━━━━╇━━━━━━━━┩
│ Total books     │   1000 │        │ ★      │    226 │
│ Average price   │ £35.07 │        │ ★★     │    196 │
│ Minimum price   │ £10.00 │        │ ★★★    │    203 │
│ Maximum price   │ £59.99 │        │ ★★★★   │    179 │
└─────────────────┴────────┘        │ ★★★★★  │    196 │
                                    └────────┴────────┘
```

## Project structure

```
books_scraper/
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── src/scraper/
│   ├── __main__.py      # enables `python -m scraper`
│   ├── cli.py           # typer CLI: crawl, stats, export
│   ├── fetch.py         # httpx client, retries, rate limit, robots.txt
│   ├── parse.py         # CSS selectors and extraction
│   ├── models.py        # pydantic Book model
│   ├── storage.py       # DuckDB + exports
│   └── analyze.py       # statistics
├── tests/
│   ├── fixtures/page1.html   # real HTML for network-free tests
│   └── test_parse.py
└── extras/
    └── api_discovery.py      # API discovery (see below)
```

## Tests

```bash
pytest
```

The tests run against a real HTML snapshot stored in `tests/fixtures/`, so they
make no network requests and are deterministic.

## Docker

```bash
docker build -t books-scraper .
docker run --rm -v "$PWD/data:/app/data" books-scraper crawl --db data/books.duckdb
```

## Extra: API discovery

`extras/api_discovery.py` scrapes the infinite scroll of
[quotes.toscrape.com/scroll](https://quotes.toscrape.com/scroll) **without a
headless browser**: in DevTools you can see the site paginates via AJAX against
`/api/quotes?page=N`, so that JSON is consumed directly.

```bash
python extras/api_discovery.py
```

## Design decisions

- **httpx instead of requests**: explicit timeouts by default, HTTP/2 and an
  identical API in sync and async mode; if concurrency is needed tomorrow, the
  migration is trivial.
- **DuckDB instead of SQLite/CSV**: an embedded analytical database (zero
  infrastructure) with full SQL for the statistics and native `COPY TO` to CSV
  and Parquet, without going through pandas.
- **No Selenium**: the content is static server-rendered HTML; a headless
  browser would multiply the cost for nothing. When a site loads data via
  JavaScript, the underlying JSON endpoint is looked up first in DevTools (see
  `extras/api_discovery.py`) and only if none exists is automating a browser
  considered.
- **Per-record validation, not per-batch**: a dirty record raises a warning and
  is dropped; the pipeline never crashes over a single defective record.
- **Selective retries**: tenacity retries with exponential backoff only on 5xx
  and timeouts. A 404 is a result, not a transient failure.

## Ethical note

This project scrapes only sites created explicitly for scraping practice. Even
so, it applies the good practices expected in production: it checks `robots.txt`
at startup, identifies itself with an honest User-Agent and spaces out requests
with delay + jitter so as not to load the server.
