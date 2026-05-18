"""Fetchers for 东方财富 (East Money) research reports and news."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Optional

from src.fetchers.base import Fetcher
from src.models import FetchResult, SourceType
from src.utils.http import create_client

_REPORT_BASE_URL = "https://reportapi.eastmoney.com/report/list"
_NEWS_SEARCH_URL = "https://search-api-web.eastmoney.com/search/jsonp"

_DAYS_LOOKBACK = 90


def _parse_jsonp(text: str) -> dict:
    """Strip the jQuery callback wrapper from a JSONP response."""
    match = re.search(r"jQuery\((.*)\)$", text.strip())
    if match:
        return json.loads(match.group(1))
    return json.loads(text)


class EastmoneyReportFetcher(Fetcher):
    source = SourceType.EASTMONEY_REPORT

    async def fetch(
        self,
        stock_code: Optional[str] = None,
        stock_name: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 50,
    ) -> list[FetchResult]:
        if not stock_code:
            return []

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        begin = since or "2025-01-01"

        results: list[FetchResult] = []

        async with create_client(timeout=20.0) as client:
            params = {
                "stockCode": stock_code,
                "pageSize": str(min(limit, 50)),
                "pageNo": "1",
                "beginTime": begin,
                "endTime": today,
                "qType": "0",
            }
            resp = await client.get(_REPORT_BASE_URL, params=params)
            data = resp.json()

            for item in data.get("data") or []:
                pub_date = item.get("publishDate", "")
                pub_iso = _normalize_datetime(pub_date)

                authors = _extract_authors(item)
                encode_url = item.get("encodeUrl", "")
                report_url = (
                    f"https://data.eastmoney.com/report/"
                    f"{encode_url}.html"
                    if encode_url
                    else ""
                )

                results.append(
                    FetchResult(
                        source=self.source,
                        title=item.get("title", ""),
                        content="",
                        summary=item.get("title", ""),
                        published_at=pub_iso,
                        stock_code=stock_code,
                        url=report_url,
                        authors=authors,
                        tags=["研报", item.get("indvInduName", "")].copy()
                        if item.get("indvInduName")
                        else ["研报"],
                        metadata={
                            "orgName": item.get("orgSName") or item.get("orgName", ""),
                            "rating": item.get("emRatingName", ""),
                            "industry": item.get("indvInduName", ""),
                            "stockName": item.get("stockName", ""),
                        },
                    )
                )

        return results[:limit]


class EastmoneyNewsFetcher(Fetcher):
    source = SourceType.EASTMONEY_NEWS

    async def fetch(
        self,
        stock_code: Optional[str] = None,
        stock_name: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 50,
    ) -> list[FetchResult]:
        if not stock_code:
            return []

        page_size = min(limit, 20)
        search_param = {
            "uid": "",
            "keyword": stock_code,
            "type": ["cmsArticleWebOld"],
            "client": "web",
            "clientType": "web",
            "clientVersion": "curr",
            "param": {
                "cmsArticleWebOld": {
                    "searchScope": "default",
                    "sort": "default",
                    "pageIndex": 1,
                    "pageSize": page_size,
                }
            },
        }
        results: list[FetchResult] = []

        async with create_client(timeout=20.0) as client:
            resp = await client.get(
                _NEWS_SEARCH_URL,
                params={
                    "cb": "jQuery",
                    "param": json.dumps(search_param, separators=(",", ":")),
                },
            )
            data = _parse_jsonp(resp.text)

            for item in data.get("result", {}).get("cmsArticleWebOld") or []:
                pub_date = item.get("date", "")
                pub_iso = _normalize_datetime(pub_date)

                results.append(
                    FetchResult(
                        source=self.source,
                        title=_strip_em_tags(item.get("title", "")),
                        content=item.get("content", ""),
                        summary=item.get("content", "")[:200],
                        published_at=pub_iso,
                        stock_code=stock_code,
                        url=item.get("url", ""),
                        tags=["新闻"],
                        metadata={
                            "mediaName": item.get("mediaName", ""),
                            "image": item.get("image", ""),
                        },
                    )
                )

        return results[:limit]


def _normalize_datetime(raw: str) -> str:
    """Normalize various datetime formats to ISO-8601."""
    if not raw:
        return "2026-01-01T00:00:00"
    # Handle "2026-05-18 00:00:00.000"
    raw = raw.strip()
    raw = raw.split(".")[0] if "." in raw else raw
    raw = raw.replace(" ", "T")
    if "T" not in raw:
        raw = f"{raw}T00:00:00"
    if raw.count("-") == 1:
        raw = f"2026-{raw}"
    return raw[:19]


def _extract_authors(item: dict) -> list[str]:
    """Extract author names from report item."""
    authors: list[str] = []
    researcher = item.get("researcher", "")
    if researcher:
        authors.append(researcher)
    raw_authors = item.get("author") or []
    for a in raw_authors:
        if isinstance(a, str) and "." in a:
            name = a.split(".", 1)[-1]
            if name and name not in authors:
                authors.append(name)
        elif isinstance(a, str) and a not in authors:
            authors.append(a)
    return authors


def _strip_em_tags(text: str) -> str:
    """Remove <em> highlighting tags from search results."""
    return re.sub(r"</?em>", "", text)
