"""Typer CLI with the crawl, stats and export commands."""

import logging
from enum import Enum
from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from scraper import analyze
from scraper.fetch import Fetcher
from scraper.models import Book
from scraper.parse import find_next_url, parse_page
from scraper.storage import BookStore

BASE_URL = "https://books.toscrape.com/"

app = typer.Typer(help="Scraper for the books.toscrape.com catalogue")
console = Console()
logger = logging.getLogger("scraper")

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, show_path=False, rich_tracebacks=True)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)


class ExportFormat(str, Enum):
    """Supported export formats."""

    csv = "csv"
    parquet = "parquet"


def _stars(rating: int) -> str:
    """Rating as stars, with an ASCII fallback for non-UTF-8 consoles."""
    char = "★" if "utf" in (console.options.encoding or "").lower() else "*"
    return char * rating


def _validate_records(records: list[dict[str, object]]) -> list[Book]:
    """Validate each record with pydantic; invalid ones are logged and dropped."""
    books: list[Book] = []
    for record in records:
        try:
            books.append(Book.model_validate(record))
        except ValidationError as exc:
            logger.warning("Record dropped (%s): %s", record.get("title"), exc)
    return books


def _print_summary(store: BookStore) -> None:
    """Print the summary table and the rating distribution."""
    stats = analyze.summary(store.conn)
    table = Table(title="Crawl summary", title_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right", style="green")
    table.add_row("Total books", str(stats["total"]))
    table.add_row("Average price", f"£{stats['avg_price']:.2f}")
    table.add_row("Minimum price", f"£{stats['min_price']:.2f}")
    table.add_row("Maximum price", f"£{stats['max_price']:.2f}")
    console.print(table)

    distribution = Table(title="Rating distribution", title_style="bold cyan")
    distribution.add_column("Rating", style="bold")
    distribution.add_column("Books", justify="right", style="green")
    for rating, count in analyze.rating_distribution(store.conn):
        distribution.add_row(_stars(rating), str(count))
    console.print(distribution)


@app.command()
def crawl(
    pages: int = typer.Option(50, min=1, help="Maximum number of pages to crawl"),
    delay: float = typer.Option(0.4, min=0.0, help="Seconds between requests"),
    db: Path = typer.Option(Path("books.duckdb"), help="Target DuckDB file"),
) -> None:
    """Walk the catalogue and persist each valid book into DuckDB."""
    fetcher = Fetcher(delay=delay)
    store = BookStore(db)
    try:
        if not fetcher.robots_allows(BASE_URL):
            logger.error("robots.txt disallows access; aborting")
            raise typer.Exit(code=1)

        total_books = 0
        url: str | None = BASE_URL
        columns = (
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        )
        with Progress(*columns, console=console) as progress:
            task = progress.add_task("Pages", total=pages)
            for page_number in range(1, pages + 1):
                response = fetcher.get(url)
                books = _validate_records(parse_page(response.text, url))
                store.upsert(books)
                total_books += len(books)
                progress.update(
                    task, advance=1, description=f"Pages · {total_books} books"
                )
                url = find_next_url(response.text, url)
                if url is None:
                    logger.info("Last page reached (%d)", page_number)
                    break
                fetcher.pause()

        logger.info("Crawl finished: %d books in %s", store.count(), db)
        _print_summary(store)
    finally:
        fetcher.close()
        store.close()


@app.command()
def stats(
    db: Path = typer.Option(Path("books.duckdb"), help="DuckDB file to query"),
) -> None:
    """Show the top 10 books by rating and price."""
    if not db.exists():
        logger.error("%s does not exist; run the crawl command first", db)
        raise typer.Exit(code=1)
    store = BookStore(db)
    try:
        table = Table(title="Top 10 books by rating and price", title_style="bold cyan")
        table.add_column("Title", max_width=48)
        table.add_column("Price", justify="right", style="green")
        table.add_column("Rating", justify="center")
        table.add_column("Availability")
        for title, price, rating, availability in analyze.top_books(store.conn):
            table.add_row(title, f"£{price:.2f}", _stars(rating), availability)
        console.print(table)
    finally:
        store.close()


@app.command()
def export(
    format: ExportFormat = typer.Option(ExportFormat.csv, help="Output format"),
    db: Path = typer.Option(Path("books.duckdb"), help="Source DuckDB file"),
    output: Path | None = typer.Option(None, help="Destination file (optional)"),
) -> None:
    """Export the books table to CSV or Parquet."""
    if not db.exists():
        logger.error("%s does not exist; run the crawl command first", db)
        raise typer.Exit(code=1)
    destination = output or Path(f"books.{format.value}")
    store = BookStore(db)
    try:
        store.export(destination, format.value)
        logger.info("Exported %d books to %s", store.count(), destination)
    finally:
        store.close()
