"""Fetcher for 巨潮资讯 (CNINFO) company announcements."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from src.fetchers.base import Fetcher
from src.models import FetchResult, SourceType
from src.utils.http import create_client

_BASE_URL = "http://www.cninfo.com.cn/new/fulltextSearch/full"


def _ms_timestamp_to_iso(ts: int) -> str:
    """Convert Unix millisecond timestamp to ISO-8601 string."""
    if not ts:
        return "2026-01-01T00:00:00"
    dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


class CninfoFetcher(Fetcher):
    source = SourceType.CNINFO

    async def fetch(
        self,
        stock_code: Optional[str] = None,
        stock_name: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 50,
    ) -> list[FetchResult]:
        if not stock_code:
            return []

        results: list[FetchResult] = []

        async with create_client(timeout=20.0) as client:
            params = {
                "searchkey": stock_code,
                "sdate": f"{since or '2025-01-01'}",
                "edate": "2026-12-31",
                "isfulltext": "false",
                "sortName": "pubdate",
                "sortType": "desc",
                "pageNum": 1,
            }
            resp = await client.get(_BASE_URL, params=params)
            data = resp.json()

            for item in data.get("announcements") or []:
                pub_ts = item.get("announcementTime", 0)
                pub_iso = _ms_timestamp_to_iso(pub_ts)
                adjunct_url = item.get("adjunctUrl", "")
                announcement_id = item.get("announcementId", "")

                results.append(
                    FetchResult(
                        source=self.source,
                        title=item.get("announcementTitle", ""),
                        content="",
                        summary=item.get("announcementTitle", ""),
                        published_at=pub_iso,
                        stock_code=stock_code,
                        url=(
                            f"http://www.cninfo.com.cn/new/disclosure/detail"
                            f"?stockCode={stock_code}"
                            f"&announcementId={announcement_id}"
                        )
                        if announcement_id
                        else (f"http://www.cninfo.com.cn/{adjunct_url}" if adjunct_url else ""),
                        tags=["公告"],
                    )
                )

        return results[:limit]
