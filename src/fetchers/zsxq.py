"""Fetcher for 知识星球 (ZSXQ) group content."""

from __future__ import annotations

import asyncio
import re
from typing import Optional

import httpx

from src.fetchers.base import Fetcher
from src.models import FetchResult, SourceType
from src.utils.http import create_client

_TAG_RE = re.compile(r"<[^>]+>")


class ZsxqFetcher(Fetcher):
    source = SourceType.ZSXQ

    def __init__(self, cookie: str = ""):
        if not cookie:
            raise ValueError("ZSXQ fetcher requires a cookie")
        self.cookie = cookie

    async def list_groups(self) -> list[dict]:
        async with create_client(cookie=self.cookie) as client:
            resp = await client.get("https://api.zsxq.com/v2/groups")
            resp.raise_for_status()
            data = resp.json()
            return data.get("resp_data", {}).get("groups", [])

    async def fetch(
        self,
        stock_code: Optional[str] = None,
        stock_name: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 200,
    ) -> list[FetchResult]:
        results: list[FetchResult] = []
        async with create_client(cookie=self.cookie) as client:
            # Must call groups first in the same session
            resp = await client.get("https://api.zsxq.com/v2/groups")
            resp.raise_for_status()
            groups = resp.json().get("resp_data", {}).get("groups", [])

            for group in groups:
                group_id = group.get("group_id")
                name = group.get("name", "")
                topics = await self._fetch_topics(
                    client, group_id, limit - len(results)
                )
                for t in topics:
                    if since and t.get("create_time", "")[:10] < since:
                        continue
                    results.append(
                        FetchResult(
                            source=self.source,
                            title=t.get("title", ""),
                            content=t.get("text", ""),
                            published_at=(t.get("create_time") or "")[:19],
                            url=f"https://wx.zsxq.com/topic/{t.get('topic_id', '')}",
                            group_name=name,
                        )
                    )
        return results[:limit]

    async def _fetch_topics(
        self, client, group_id: str, limit: int
    ) -> list[dict]:
        topics: list[dict] = []
        url = f"https://api.zsxq.com/v2/groups/{group_id}/topics"
        end_id = None

        while len(topics) < limit:
            params: dict = {"count": min(limit - len(topics), 20)}
            if end_id:
                params["end_id"] = end_id

            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("resp_data", {}).get("topics", [])
            if not items:
                break

            for item in items:
                talk = item.get("talk", {})
                raw = talk.get("text", "")
                if isinstance(raw, str):
                    full_text = _TAG_RE.sub("", raw).strip()
                else:
                    full_text = "".join(
                        p.get("text", "") for p in raw if isinstance(p, dict)
                    )
                topics.append(
                    {
                        "title": (full_text[:80] or "无标题"),
                        "text": full_text,
                        "create_time": item.get("create_time", ""),
                        "topic_id": item.get("topic_id", ""),
                    }
                )
                if len(topics) >= limit:
                    break

            end_id = items[-1].get("topic_id") if items else None
            if not end_id:
                break
            await asyncio.sleep(0.5)

        return topics

    async def search_topics(
        self,
        keyword: str,
        group_id: str = "",
        limit: int = 50,
        client: httpx.AsyncClient | None = None,
    ) -> list[dict]:
        """Search topics by keyword using zsxq search API."""
        topics: list[dict] = []
        base = f"https://api.zsxq.com/v2/search/groups/{group_id}/topics"
        page = 1

        async def _do(client: httpx.AsyncClient) -> list[dict]:
            nonlocal page
            while len(topics) < limit:
                params = {
                    "keyword": keyword,
                    "count": min(limit - len(topics), 20),
                    "order_by": "default",
                    "index": page,
                }

                resp = await client.get(base, params=params)
                resp.raise_for_status()
                data = resp.json()
                items = data.get("resp_data", {}).get("topics", [])
                if not items:
                    break

                for item in items:
                    talk = item.get("talk", {})
                    raw = talk.get("text", "")
                    full_text = _TAG_RE.sub("", raw).strip() if isinstance(raw, str) else ""
                    topics.append({
                        "title": (full_text[:80] or "无标题"),
                        "text": full_text,
                        "create_time": item.get("create_time", ""),
                        "topic_id": item.get("topic_id", ""),
                    })
                    if len(topics) >= limit:
                        break

                page += 1
                await asyncio.sleep(0.5)
            return topics

        if client:
            return await _do(client)
        async with create_client(cookie=self.cookie) as c:
            await c.get("https://api.zsxq.com/v2/groups")
            return await _do(c)
