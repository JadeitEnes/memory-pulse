import asyncio
import random
from abc import abstractmethod
from typing import ClassVar

import httpx

from app.core.logging import get_logger
from app.infrastructure.collectors.base_collector import BaseCollector
from app.schemas.price import PriceCreateSchema

logger = get_logger(__name__)

_USER_AGENTS: list[str] = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) " "Gecko/20100101 Firefox/126.0"),
]


class BaseHttpCollector(BaseCollector):
    """HTTP scraper base with retry, exponential back-off, and rate limiting.

    Subclasses implement `collect()` and call `_fetch()` for HTTP access.
    On 403/429/503 the request is retried with increasing delays so the
    target server is not hammered.
    """

    MAX_RETRIES: ClassVar[int] = 3
    REQUEST_DELAY: ClassVar[float] = 2.5  # seconds between requests
    TIMEOUT: ClassVar[float] = 20.0

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def _fetch(self, url: str, params: dict | None = None) -> httpx.Response:
        """Fetch URL with retry + exponential back-off on rate-limit responses."""
        last_exc: Exception = RuntimeError("No attempts made")

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=self.TIMEOUT,
                    follow_redirects=True,
                    headers=self._headers(),
                ) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    logger.debug("http_fetch_ok", url=url, status=response.status_code)
                    return response

            except httpx.HTTPStatusError as exc:
                last_exc = exc
                status = exc.response.status_code
                if status in (403, 429, 503):
                    wait = (2**attempt) * 5.0  # 5s, 10s, 20s
                    logger.warning(
                        "http_rate_limited",
                        url=url,
                        status=status,
                        attempt=attempt + 1,
                        retry_in=wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise

            except httpx.RequestError as exc:
                last_exc = exc
                wait = 2.0**attempt
                logger.warning(
                    "http_request_error",
                    url=url,
                    error=str(exc),
                    attempt=attempt + 1,
                    retry_in=wait,
                )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(wait)

        raise last_exc

    @abstractmethod
    async def collect(self) -> list[PriceCreateSchema]: ...
