"""Consume the JSON endpoint behind quotes.toscrape.com/scroll, no browser.

The site's infinite scroll calls /api/quotes?page=N over AJAX (visible in the
DevTools Network tab), so a plain HTTP client is enough.
"""

from collections import Counter
from typing import Any

import httpx

API_URL = "https://quotes.toscrape.com/api/quotes"


def fetch_all_quotes() -> list[dict[str, Any]]:
    """Paginate the JSON endpoint until has_next is false."""
    quotes: list[dict[str, Any]] = []
    page = 1
    with httpx.Client(timeout=10.0) as client:
        while True:
            data: dict[str, Any] = client.get(API_URL, params={"page": page}).json()
            quotes.extend(data["quotes"])
            if not data["has_next"]:
                return quotes
            page += 1


def main() -> None:
    """Print the total number of quotes and the 5 most frequent authors."""
    quotes = fetch_all_quotes()
    authors: Counter[str] = Counter(quote["author"]["name"] for quote in quotes)
    print(f"Total quotes: {len(quotes)}")
    for author, count in authors.most_common(5):
        print(f"{count:>3}  {author}")


if __name__ == "__main__":
    main()
