"""DuckDB persistence and CSV/Parquet exports."""

from pathlib import Path

import duckdb

from scraper.models import Book

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    title        TEXT NOT NULL,
    price        DOUBLE NOT NULL,
    rating       INTEGER NOT NULL,
    availability TEXT NOT NULL,
    url          TEXT PRIMARY KEY
)
"""


class BookStore:
    """Book repository backed by a DuckDB file."""

    def __init__(self, db_path: Path) -> None:
        self.conn = duckdb.connect(str(db_path))
        self.conn.execute(SCHEMA)

    def upsert(self, books: list[Book]) -> None:
        """Insert books, replacing duplicates by URL."""
        if not books:
            return
        rows = [
            (book.title, book.price, book.rating, book.availability, str(book.url))
            for book in books
        ]
        self.conn.executemany(
            "INSERT OR REPLACE INTO books VALUES (?, ?, ?, ?, ?)", rows
        )

    def count(self) -> int:
        """Total number of stored books."""
        row = self.conn.execute("SELECT count(*) FROM books").fetchone()
        return int(row[0]) if row else 0

    def export(self, destination: Path, fmt: str) -> None:
        """Export the books table to CSV or Parquet depending on fmt."""
        options = "(FORMAT PARQUET)" if fmt == "parquet" else "(FORMAT CSV, HEADER)"
        self.conn.execute(f"COPY books TO '{destination.as_posix()}' {options}")

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
