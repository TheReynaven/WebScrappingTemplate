"""Aggregate statistics over the scraped catalogue."""

import duckdb


def summary(conn: duckdb.DuckDBPyConnection) -> dict[str, float]:
    """Total number of books plus average, minimum and maximum price."""
    row = conn.execute(
        "SELECT count(*), avg(price), min(price), max(price) FROM books"
    ).fetchone()
    if row is None:
        return {"total": 0, "avg_price": 0.0, "min_price": 0.0, "max_price": 0.0}
    total, avg_price, min_price, max_price = row
    return {
        "total": total,
        "avg_price": avg_price or 0.0,
        "min_price": min_price or 0.0,
        "max_price": max_price or 0.0,
    }


def rating_distribution(conn: duckdb.DuckDBPyConnection) -> list[tuple[int, int]]:
    """Number of books per rating, from 1 to 5 stars."""
    return conn.execute(
        "SELECT rating, count(*) FROM books GROUP BY rating ORDER BY rating"
    ).fetchall()


def top_books(
    conn: duckdb.DuckDBPyConnection, limit: int = 10
) -> list[tuple[str, float, int, str]]:
    """Best books ordered by descending rating and price."""
    return conn.execute(
        """
        SELECT title, price, rating, availability
        FROM books
        ORDER BY rating DESC, price DESC
        LIMIT ?
        """,
        [limit],
    ).fetchall()
