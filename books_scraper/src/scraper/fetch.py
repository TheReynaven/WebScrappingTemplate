"""HTTP client with retries, rate limiting and an identifiable User-Agent."""

import logging
import random
import time
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

USER_AGENT = "BooksScraperDemo/1.0 (educational project)"

logger = logging.getLogger(__name__)


class ServerError(Exception):
    """A 5xx response that warrants a retry."""


class Fetcher:
    """Wraps httpx with retries on transient failures and pauses between requests."""

    def __init__(self, delay: float = 0.4, timeout: float = 10.0) -> None:
        self.delay = delay
        self.client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )

    @retry(
        retry=retry_if_exception_type((ServerError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=8),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def get(self, url: str) -> httpx.Response:
        """Fetch a URL, retrying only on 5xx or timeout."""
        response = self.client.get(url)
        if response.status_code >= 500:
            raise ServerError(f"HTTP {response.status_code} at {url}")
        response.raise_for_status()
        return response

    def pause(self) -> None:
        """Sleep the configured delay with random jitter of ±30%."""
        time.sleep(self.delay * random.uniform(0.7, 1.3))

    def robots_allows(self, base_url: str) -> bool:
        """Query robots.txt and report whether scraping is allowed."""
        robots_url = urljoin(base_url, "/robots.txt")
        try:
            response = self.client.get(robots_url)
        except httpx.HTTPError as exc:
            logger.warning("Could not read %s (%s); assuming allowed", robots_url, exc)
            return True
        if response.status_code == 404:
            logger.info("robots.txt not found at %s: scraping allowed", base_url)
            return True
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        allowed = parser.can_fetch(USER_AGENT, base_url)
        verdict = "allowed" if allowed else "DISALLOWED"
        logger.info("robots.txt checked: scraping %s for %s", verdict, USER_AGENT)
        return allowed

    def close(self) -> None:
        """Close the underlying HTTP connection."""
        self.client.close()
