"""Corsair retail price collector.

Newegg is now behind Cloudflare's Managed Challenge (JS + TLS
fingerprinting) — no amount of header tuning gets past it, and building
a bypass would mean actively defeating a bot-detection system, which
this project isn't going to do. Corsair's storefront search sits behind
plain Cloudflare (no active challenge as of 2026-09-25) and, being a
Next.js app, ships its full result set as server-rendered JSON
(`__NEXT_DATA__`) — no HTML scraping needed at all.

Retail → wholesale correlation:
  DDR5/DDR4 kit price / kit capacity ≈ consumer DRAM spot proxy
  NVMe SSD price / SSD capacity ≈ NAND TLC spot proxy

Why category filtering matters:
  A capacity keyword like "32gb ddr5" also matches prebuilt PCs and
  workstations that happen to include that RAM — their prices (often
  10-20x a RAM kit) would badly skew a naive median. Corsair's product
  JSON tags every item with `categories[].url_path`, so real memory/SSD
  products are filtered by category rather than by price sanity checks.
"""

import asyncio
import json
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

_SEARCH_URL = "https://www.corsair.com/us/en/search"

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)
_CAPACITY_RE = re.compile(r"(\d+)\s*(GB|TB)", re.I)

_TARGETS: list[dict[str, Any]] = [
    {
        "keyword": "32gb ddr5",
        "component": MemoryComponent.DDR5,
        "segment": MarketSegment.CONSUMER,
        "category": "memory",
        "note": "Corsair DDR5 desktop kits",
    },
    {
        "keyword": "ddr4 32gb",
        "component": MemoryComponent.DDR4,
        "segment": MarketSegment.CONSUMER,
        "category": "memory",
        "note": "Corsair DDR4 desktop kits",
    },
    {
        "keyword": "1tb nvme ssd",
        "component": MemoryComponent.NAND_TLC,
        "segment": MarketSegment.CONSUMER_SSD,
        "category": "data-storage",
        "note": "Corsair NVMe SSDs (MP600/MP700 series)",
    },
]


def _capacity_gb(label: str) -> float | None:
    """Parse a capacity string like '32GB (2 x 16GB)' or '1TB' into GB."""
    m = _CAPACITY_RE.search(label)
    if not m:
        return None
    value = float(m.group(1))
    return value * 1000 if m.group(2).upper() == "TB" else value


def _median(values: list[float]) -> float:
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


class CorsairCollector(BaseHttpCollector):
    """Collect retail memory/SSD prices from Corsair's storefront search."""

    REQUEST_DELAY = 3.0  # be polite — 3 s between searches

    async def collect(self) -> list[PriceCreateSchema]:
        results: list[PriceCreateSchema] = []
        now = datetime.now(timezone.utc)

        for target in _TARGETS:
            try:
                price_per_gb = await self._fetch_median_price_per_gb(target)
                if price_per_gb is None:
                    logger.warning("corsair_no_prices", keyword=target["keyword"])
                    continue

                results.append(
                    PriceCreateSchema(
                        component=target["component"],
                        market_segment=target["segment"],
                        price_value=Decimal(str(round(price_per_gb, 4))),
                        price_unit=PriceUnit.USD_PER_GB,
                        currency="USD",
                        data_source=DataSource.CORSAIR,
                        source_url=_SEARCH_URL,
                        recorded_at=now,
                        notes=target["note"],
                    )
                )
                logger.info(
                    "corsair_price_collected",
                    component=target["component"].value,
                    price_per_gb=round(price_per_gb, 4),
                )
                await asyncio.sleep(self.REQUEST_DELAY)

            except Exception as exc:
                logger.error("corsair_collect_error", keyword=target["keyword"], error=str(exc))

        return results

    async def _fetch_median_price_per_gb(self, target: dict[str, Any]) -> float | None:
        """Search Corsair and return the median per-GB price across matching listings."""
        try:
            response = await self._fetch(_SEARCH_URL, params={"q": target["keyword"]})
        except Exception as exc:
            logger.warning("corsair_fetch_failed", keyword=target["keyword"], error=str(exc))
            return None

        return self._parse_next_data_prices(response.text, target["category"])

    def _parse_next_data_prices(self, html: str, category: str) -> float | None:
        """Pull product results out of the page's embedded __NEXT_DATA__ JSON."""
        match = _NEXT_DATA_RE.search(html)
        if not match:
            logger.warning("corsair_next_data_missing")
            return None

        try:
            payload = json.loads(match.group(1))
            items = payload["props"]["pageProps"]["firstPageOfResults"]["data"]["products"][
                "items"
            ]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("corsair_next_data_unparseable", error=str(exc))
            return None

        prices_per_gb: list[float] = []
        for item in items:
            categories = {c["url_path"] for c in (item.get("categories") or [])}
            if category not in categories:
                continue  # a prebuilt PC / workstation bundling this part, not the part itself

            capacity_gb = self._item_capacity_gb(item)
            price = self._item_price(item)
            if not capacity_gb or not price:
                continue

            per_gb = price / capacity_gb
            if 0.01 < per_gb < 100:  # sanity filter
                prices_per_gb.append(per_gb)

        return _median(prices_per_gb) if prices_per_gb else None

    def _item_capacity_gb(self, item: dict[str, Any]) -> float | None:
        for option in item.get("configurable_options") or []:
            if option.get("attribute_code") != "Capacity":
                continue
            for value in option.get("values") or []:
                capacity = _capacity_gb(value.get("label", ""))
                if capacity:
                    return capacity
        # SimpleProduct (e.g. SSDs) has no configurable options — read the name instead.
        return _capacity_gb(item.get("name", ""))

    def _item_price(self, item: dict[str, Any]) -> float | None:
        try:
            return float(item["price_range"]["minimum_price"]["final_price"]["value"])
        except (KeyError, TypeError, ValueError):
            return None
