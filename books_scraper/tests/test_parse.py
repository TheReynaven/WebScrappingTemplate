"""Parsing tests against a real HTML snapshot of page 1."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from scraper.models import Book
from scraper.parse import clean_price, find_next_url, parse_page, parse_rating

FIXTURE = Path(__file__).parent / "fixtures" / "page1.html"
PAGE_URL = "https://books.toscrape.com/index.html"


@pytest.fixture()
def page_html() -> str:
    """Real HTML of the first catalogue page."""
    return FIXTURE.read_text(encoding="utf-8")


def test_parse_page_extracts_twenty_books(page_html: str) -> None:
    books = parse_page(page_html, PAGE_URL)
    assert len(books) == 20


def test_first_book_has_clean_fields(page_html: str) -> None:
    first = parse_page(page_html, PAGE_URL)[0]
    assert first["title"] == "A Light in the Attic"
    assert first["price"] == 51.77
    assert first["rating"] == 3
    assert str(first["url"]).startswith("https://books.toscrape.com/catalogue/")


def test_clean_price_strips_currency_symbols() -> None:
    assert clean_price("£51.77") == 51.77
    assert clean_price("Â£13.50") == 13.50
    with pytest.raises(ValueError):
        clean_price("gratis")


def test_parse_rating_maps_word_to_int() -> None:
    assert parse_rating(["star-rating", "Three"]) == 3
    with pytest.raises(ValueError):
        parse_rating(["star-rating", "Eleven"])


def test_find_next_url_is_absolute(page_html: str) -> None:
    next_url = find_next_url(page_html, PAGE_URL)
    assert next_url == "https://books.toscrape.com/catalogue/page-2.html"
    assert find_next_url("<html><body></body></html>", PAGE_URL) is None


def test_book_model_rejects_dirty_record() -> None:
    with pytest.raises(ValidationError):
        Book.model_validate(
            {
                "title": "",
                "price": -1.0,
                "rating": 9,
                "availability": "In stock",
                "url": "https://books.toscrape.com/x",
            }
        )
