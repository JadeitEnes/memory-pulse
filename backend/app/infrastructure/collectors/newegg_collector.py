"""Newegg retail price collector.

Scrapes Newegg search results for memory products and converts retail
prices to per-GB figures that approximate wholesale market trends.

Retail → wholesale correlation:
  DDR5 kit price / kit capacity ≈ consumer DRAM spot proxy
  NVMe SSD price / SSD capacity ≈ NAND TLC spot proxy

Why Newegg over Amazon:
  Newegg's search results return structured JSON (application/json) via a
  public GraphQL-like endpoint when the Accept header requests JSON, making
  parsing more stable than regex-scraping Amazon HTML.
"""

import asyncio
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.core.logging import get_logger
from app.domain.entities.enums import (
    DataSource,
    MarketSegment,
    MemoryComponent,
    PriceUnit,
)
from app.infrastructure.collectors.base_http_collector import BaseHttpCollector
from app.schemas.price import PriceCreateSchema

logger = get_logger(__name__)

# Newegg search endpoint — returns JSON when called with correct headers
_SEARCH_URL = "https://www.newegg.com/p/pl"

# Each entry defines one search and how to map results to our schema.
# capacity_gb: the advertised size we search for (used to compute $/GB)
_TARGETS: list[dict[str, Any]] = [
    {
        "keyword": "ddr5 32gb desktop ram",
        "component": MemoryComponent.DDR5,
        "segment": MarketSegment.CONSUMER,
        "capacity_gb": 32,
        "note": "DDR5 consumer desktop — 32 GB kit",
    },
    {
        "keyword": "ddr4 32gb desktop ram",
        "component": MemoryComponent.DDR4,
        "segment": MarketSegment.CONSUMER,
        "capacity_gb": 32,
        "note": "DDR4 consumer desktop — 32 GB kit",
    },
    {
        "keyword": "nvme ssd 2tb m.2",
        "component": MemoryComponent.NAND_TLC,
        "segment": MarketSegment.CONSUMER_SSD,
        "capacity_gb": 2000,
        "note": "NVMe TLC SSD — 2 TB",
    },
    {
        "keyword": "nvme ssd 1tb m.2",
        "component": MemoryComponent.NAND_QLC,
        "segment": MarketSegment.CONSUMER_SSD,
        "capacity_gb": 1000,
        "note": "NVMe QLC SSD — 1 TB",
    },
]

# Regex patterns to extract prices from HTML (fallback if JSON unavailable)
_PRICE_RE = re.compile(r"\$\s*([\d,]+\.?\d*)")
_DOLLARS_RE = re.compile(r"([\d,]+)\.([\d]{2})")


def _parse_price_text(text: str) -> float | None:
    """Extract the first USD price from a string like '$129.99' or '129 . 99'."""
    m = _PRICE_RE.search(text)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return None


def _median(values: list[float]) -> float:
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


class NeweggCollector(BaseHttpCollector):
    """Collect retail memory prices from Newegg search pages."""

    REQUEST_DELAY = 3.0  # be polite — 3 s between category requests

    async def collect(self) -> list[PriceCreateSchema]:
        results: list[PriceCreateSchema] = []
        now = datetime.now(timezone.utc)

        for target in _TARGETS:
            try:
                price_per_gb = await self._fetch_median_price_per_gb(target)
                if price_per_gb is None:
                    logger.warning(
                        "newegg_no_prices",
                        keyword=target["keyword"],
                    )
                    continue

                results.append(
                    PriceCreateSchema(
                        component=target["component"],
                        market_segment=target["segment"],
                        price_value=Decimal(str(round(price_per_gb, 4))),
                        price_unit=PriceUnit.USD_PER_GB,
                        currency="USD",
                        data_source=DataSource.NEWEGG,
                        source_url=_SEARCH_URL,
                        recorded_at=now,
                        notes=target["note"],
                    )
                )
                logger.info(
                    "newegg_price_collected",
                    component=target["component"].value,
                    price_per_gb=round(price_per_gb, 4),
                )
                await asyncio.sleep(self.REQUEST_DELAY)

            except Exception as exc:
                logger.error(
                    "newegg_collect_error",
                    keyword=target["keyword"],
                    error=str(exc),
                )

        return results

    async def _fetch_median_price_per_gb(self, target: dict[str, Any]) -> float | None:
        """Search Newegg and return the median per-GB price across listings."""
        try:
            response = await self._fetch(
                _SEARCH_URL,
                params={
                    "d": target["keyword"],
                    "Order": "PRICE",  # sort by price ascending
                    "PageSize": "36",
                },
            )
        except Exception as exc:
            logger.warning("newegg_fetch_failed", keyword=target["keyword"], error=str(exc))
            return None

        return self._parse_html_prices(response.text, target["capacity_gb"])

    def _parse_html_prices(self, html: str, capacity_gb: int) -> float | None:
        """Parse Newegg search result HTML and extract per-GB prices."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        # Newegg item cards — current price is in .price-current strong + sup
        prices: list[float] = []

        for item in soup.select(".item-cell"):
            # Skip sponsored / combo items
            if item.select_one(".item-promo"):
                continue

            price_el = item.select_one(".price-current")
            if not price_el:
                continue

            # price-current contains: <strong>129</strong><sup>.99</sup>
            strong = price_el.select_one("strong")
            sup = price_el.select_one("sup")
            if strong:
                dollars_text = strong.get_text(strip=True).replace(",", "")
                cents_text = sup.get_text(strip=True).lstrip(".") if sup else "00"
                try:
                    price = float(f"{dollars_text}.{cents_text}")
                    if 10 < price < 5000:  # sanity filter
                        prices.append(price)
                except ValueError:
                    continue

        if not prices:
            # Fallback: regex scan entire page for dollar amounts
            raw = _PRICE_RE.findall(html)
            for raw_price in raw[:50]:
                try:
                    p = float(raw_price.replace(",", ""))
                    if 10 < p < 5000:
                        prices.append(p)
                except ValueError:
                    continue

        if not prices:
            return None

        # Use median to ignore outlier bundles / combos
        median_price = _median(prices)
        return median_price / capacity_gb
