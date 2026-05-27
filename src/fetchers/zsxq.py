"""Fetcher for 知识星球 (ZSXQ) group content."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import unquote

import httpx

logger = logging.getLogger(__name__)

from src.fetchers.base import Fetcher
from src.models import FetchResult, SourceType
from src.utils.http import create_client

_TAG_RE = re.compile(r"<[^>]+>")
_LINK_RE = re.compile(r'<e\s+type="web"\s+href="([^"]+)"[^>]*/?>')


def _extract_links_and_clean(text: str) -> str:
    """从 zsxq 富文本中提取链接，拼接到文本末尾，再清除 HTML 标签。"""
    links = []
    for m in _LINK_RE.finditer(text):
        href = unquote(m.group(1))
        links.append(href)

    cleaned = _TAG_RE.sub("", text).strip()
    if links:
        cleaned += "\n\n链接:\n" + "\n".join(links)
    return cleaned


class ZsxqFetcher(Fetcher):
    source = SourceType.ZSXQ

    def __init__(self, cookie: str = ""):
        if not cookie:
            raise ValueError("ZSXQ fetcher requires a cookie")
        self.cookie = cookie

    async def list_groups(self) -> list[dict]:
        async with create_client(cookie=self.cookie) as client:
            for attempt in range(5):
                resp = await client.get("https://api.zsxq.com/v2/groups")
                if resp.status_code != 200:
                    await asyncio.sleep(2)
                    continue
                data = resp.json()
                groups = data.get("resp_data", {}).get("groups", [])
                if groups:
                    return groups
                await asyncio.sleep(1.5)
            return []

    async def fetch(
        self,
        stock_code: Optional[str] = None,
        stock_name: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 200,
    ) -> list[FetchResult]:
        import random
        results: list[FetchResult] = []
        async with create_client(cookie=self.cookie) as client:
            # Must call groups first in the same session; zsxq API is
            # aggressive with rate limiting — randomize delays
            groups: list[dict] = []
            for attempt in range(5):
                await asyncio.sleep(random.uniform(1, 3))
                resp = await client.get("https://api.zsxq.com/v2/groups")
                if resp.status_code != 200:
                    logger.warning(f"groups API status={resp.status_code}, retry {attempt+1}")
                    continue
                data = resp.json()
                # Log API error if present
                if "succeeded" in data and not data["succeeded"]:
                    logger.warning(f"groups API error: {data.get('error', {}).get('message', 'unknown')}")
                    continue
                groups = data.get("resp_data", {}).get("groups", [])
                if groups:
                    break

            for group in groups:
                group_id = group.get("group_id")
                name = group.get("name", "")
                try:
                    topics = await self._fetch_topics(
                        client, group_id, limit - len(results)
                    )
                except Exception:
                    continue
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
                            metadata={
                                "images": t.get("images", []),
                                "files": t.get("files", []),
                            },
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
            params: dict = {"count": min(limit - len(topics), 40)}
            if end_id:
                params["end_id"] = end_id

            for attempt in range(3):
                try:
                    resp = await client.get(url, params=params)
                    if resp.status_code != 200:
                        if attempt < 2:
                            await asyncio.sleep(2)
                            continue
                        resp.raise_for_status()
                    data = resp.json()
                    break
                except Exception:
                    if attempt < 2:
                        await asyncio.sleep(2)
                        continue
                    # All retries exhausted, skip this batch
                    return topics
            items = data.get("resp_data", {}).get("topics", [])
            if not items:
                break

            for item in items:
                talk = item.get("talk", {})
                raw = talk.get("text", "")
                if isinstance(raw, str):
                    full_text = _extract_links_and_clean(raw)
                else:
                    full_text = "".join(
                        p.get("text", "") for p in raw if isinstance(p, dict)
                    )

                # Extract images
                images = []
                for img in talk.get("images", []):
                    orig = img.get("original", {}) or {}
                    large = img.get("large", {}) or {}
                    url = orig.get("url") or large.get("url", "")
                    if url:
                        images.append({
                            "url": url,
                            "width": orig.get("width"),
                            "height": orig.get("height"),
                        })

                # Extract file attachments
                files = []
                for f in talk.get("files", []):
                    files.append({
                        "name": f.get("name", ""),
                        "size": f.get("size", 0),
                        "url": f.get("url", ""),
                        "download_url": f.get("download_url", ""),
                    })

                topics.append(
                    {
                        "title": (full_text[:80] or "无标题"),
                        "text": full_text,
                        "create_time": item.get("create_time", ""),
                        "topic_id": item.get("topic_id", ""),
                        "images": images,
                        "files": files,
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
                    full_text = _extract_links_and_clean(raw) if isinstance(raw, str) else ""

                    images = []
                    for img in talk.get("images", []):
                        orig = img.get("original", {}) or {}
                        large = img.get("large", {}) or {}
                        url = orig.get("url") or large.get("url", "")
                        if url:
                            images.append({
                                "url": url,
                                "width": orig.get("width"),
                                "height": orig.get("height"),
                            })

                    files = []
                    for f in talk.get("files", []):
                        files.append({
                            "name": f.get("name", ""),
                            "size": f.get("size", 0),
                            "url": f.get("url", ""),
                            "download_url": f.get("download_url", ""),
                        })

                    topics.append({
                        "title": (full_text[:80] or "无标题"),
                        "text": full_text,
                        "create_time": item.get("create_time", ""),
                        "topic_id": item.get("topic_id", ""),
                        "images": images,
                        "files": files,
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
