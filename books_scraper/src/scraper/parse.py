import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def _class_list(tag: Tag) -> list[str]:
    value = tag.get("class")
    if value is None:
        return []
    if isinstance(value, str):
        return value.split()
    return list(value)


def clean_price(raw: str) -> float:
    digits = re.sub(r"[^\d.]", "", raw)
    if not digits:
        raise ValueError(f"Unreadable price: {raw!r}")
    return float(digits)


def parse_rating(css_classes: list[str]) -> int:
    for css_class in css_classes:
        if css_class in RATING_WORDS:
            return RATING_WORDS[css_class]
    raise ValueError(f"Unrecognized rating in classes: {css_classes!r}")


def parse_page(html: str, page_url: str) -> list[dict[str, object]]:
    soup = BeautifulSoup(html, "lxml")
    books: list[dict[str, object]] = []
    for article in soup.select("article.product_pod"):
        anchor = article.select_one("h3 > a")
        price_tag = article.select_one("p.price_color")
        rating_tag = article.select_one("p.star-rating")
        availability_tag = article.select_one("p.instock.availability")
        if not (anchor and price_tag and rating_tag and availability_tag):
            continue
        books.append(
            {
                "title": anchor.get("title", anchor.text.strip()),
                "price": clean_price(price_tag.text),
                "rating": parse_rating(_class_list(rating_tag)),
                "availability": " ".join(availability_tag.text.split()),
                "url": urljoin(page_url, str(anchor["href"])),
            }
        )
    return books


def find_next_url(html: str, page_url: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    link = soup.select_one("li.next > a")
    return urljoin(page_url, str(link["href"])) if link else None
