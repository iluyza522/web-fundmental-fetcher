"""
雪球 (Xueqiu) stock community scraper.

Uses Playwright to bypass WAF and make API calls from within the browser
context, ensuring the anti-scraping md5 signature is computed automatically.
"""

import asyncio
import json
import logging
from enum import Enum
from typing import Optional

from playwright.async_api import Browser, Page, BrowserContext
from cloakbrowser import launch_async

from .xueqiu_models import CommunityPost, APIResponse, RecommendUser, StockCommunity

logger = logging.getLogger(__name__)

BASE_URL = "https://xueqiu.com"


class SortBy(str, Enum):
    TIME = "time"    # 新帖 - 按时间倒序
    ALPHA = "alpha"  # 热帖 - 按热度排序（算法排序）


class Source(str, Enum):
    ALL = "all"
    USER = "user"
    NEWS = "news"


class XueqiuScraper:
    """Scrape stock community data from Xueqiu (雪球)."""

    def __init__(self, headless: bool = True, timeout_ms: int = 30000):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()

    async def start(self):
        """Launch browser and navigate to Xueqiu to establish session."""
        self._browser = await launch_async(
            headless=self.headless,
        )
        self._context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.timeout_ms)

        # Navigate to homepage first to pass WAF and set cookies
        logger.info("Navigating to Xueqiu to establish session...")
        await self._page.goto(BASE_URL, wait_until="domcontentloaded")
        await asyncio.sleep(2)

        # Verify we're past the WAF
        page_title = await self._page.title()
        if "雪球" not in page_title:
            logger.warning(f"WAF challenge may not have been passed. Title: {page_title}")
        logger.info(f"Session established. Title: {page_title}")

    async def stop(self):
        """Close browser."""
        if self._browser:
            await self._browser.close()

    async def _api_call(self, path: str, params: dict | None = None) -> dict:
        """Make an API call from within the browser context.

        This ensures the anti-scraping md5 signature is computed by the page's
        JavaScript automatically.
        """
        if not self._page:
            raise RuntimeError("Scraper not started. Call start() first.")

        query_string = ""
        if params:
            query_string = "?" + "&".join(
                f"{k}={v}" for k, v in params.items() if v is not None
            )

        url = f"{BASE_URL}{path}{query_string}"

        js_code = f"""
        (async () => {{
            try {{
                const response = await fetch('{url}', {{
                    headers: {{
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    }},
                }});
                if (!response.ok) {{
                    throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                }}
                const text = await response.text();
                return JSON.parse(text);
            }} catch (e) {{
                return {{ error: e.message }};
            }}
        }})()
        """

        result = await self._page.evaluate(js_code)

        if isinstance(result, dict) and "error" in result:
            raise RuntimeError(
                f"API call failed: {result['error']} (url: {url})"
            )

        return result

    @staticmethod
    def _parse_post(raw: dict) -> CommunityPost:
        """Parse a raw post dict into a CommunityPost model."""
        user_data = raw.get("user", {})
        return CommunityPost(
            id=raw["id"],
            user_id=raw["user_id"],
            user={
                "id": user_data.get("id", 0),
                "screen_name": user_data.get("screen_name", ""),
                "profile": user_data.get("profile", ""),
                "followers_count": user_data.get("followers_count", 0),
                "friends_count": user_data.get("friends_count", 0),
                "status_count": user_data.get("status_count", 0),
                "description": user_data.get("description", ""),
                "verified": user_data.get("verified", False),
                "verified_type": user_data.get("verified_type", 0),
                "verified_description": user_data.get("verified_description", ""),
                "gender": user_data.get("gender", ""),
                "province": user_data.get("province", ""),
                "city": user_data.get("city", ""),
                "profile_image_url": user_data.get("profile_image_url", ""),
                "photo_domain": user_data.get("photo_domain", ""),
                "stocks_count": user_data.get("stocks_count", 0),
            },
            created_at=raw.get("created_at", 0),
            description=raw.get("description", ""),
            text=raw.get("text", ""),
            title=raw.get("title", ""),
            target=raw.get("target", ""),
            source=raw.get("source", ""),
            reply_count=raw.get("reply_count", 0),
            like_count=raw.get("like_count", 0),
            fav_count=raw.get("fav_count", 0),
            view_count=raw.get("view_count", 0),
            retweet_count=raw.get("retweet_count", 0),
            reward_count=raw.get("reward_count", 0),
            hot=raw.get("hot", False),
            controversial=raw.get("controversial", False),
            truncated=raw.get("truncated", False),
            can_edit=raw.get("canEdit", True),
            editable=raw.get("editable", True),
            is_answer=raw.get("is_answer", False),
            is_bonus=raw.get("is_bonus", False),
            is_reward=raw.get("is_reward", False),
            is_refused=raw.get("is_refused", False),
            mark=raw.get("mark", 0),
            pic=raw.get("pic", ""),
            flags=raw.get("flags", 0),
            time_before=raw.get("timeBefore", ""),
            comment_id=raw.get("commentId", 0),
        )

    async def _navigate_to_stock(self, symbol: str):
        """Navigate to a stock page to ensure the stock context is loaded."""
        url = f"{BASE_URL}/S/{symbol}"
        logger.info(f"Navigating to stock page: {url}")
        await self._page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(1.5)

        # Check if redirected to login or captcha
        current_url = self._page.url
        if "S/" not in current_url:
            logger.warning(f"May have hit a block. URL: {current_url}")

    async def get_community_posts(
        self,
        symbol: str,
        page: int = 1,
        count: int = 10,
        sort: SortBy = SortBy.TIME,
        source: Source | str = Source.ALL,
        comment: int = 0,
        hl: int = 0,
        *,
        _navigated: bool = False,
    ) -> APIResponse:
        """Fetch community posts for a stock symbol.

        Args:
            symbol: Stock symbol, e.g. 'SH600519'
            page: Page number (1-indexed)
            count: Posts per page (max ~20)
            sort: Sort by time or hot
            source: Post source filter
            comment: Only show posts with comments
            hl: Highlight
        """
        if not _navigated:
            await self._navigate_to_stock(symbol)

        params = {
            "count": count,
            "comment": comment,
            "symbol": symbol,
            "hl": hl,
            "source": source.value if isinstance(source, Source) else source,
            "sort": sort.value if isinstance(sort, SortBy) else sort,
            "page": page,
            "q": "",
            "type": 11,
        }

        data = await self._api_call("/query/v1/symbol/search/status.json", params)

        posts = [self._parse_post(item) for item in data.get("list", [])]

        return APIResponse(
            about=data.get("about", ""),
            count=data.get("count", 0),
            key=data.get("key", ""),
            items=posts,
            max_page=data.get("maxPage"),
        )

    async def get_recommended_users(
        self, symbol: str, start: int = 0, count: int = 14
    ) -> list[RecommendUser]:
        """Fetch users who focus on this stock."""
        await self._navigate_to_stock(symbol)

        params = {
            "type": 1,
            "code": symbol,
            "start": start,
            "count": count,
        }

        data = await self._api_call("/recommend/pofriends.json", params)

        return [
            RecommendUser(
                id=u.get("id", 0),
                screen_name=u.get("screen_name", ""),
                profile=u.get("profile", ""),
                followers_count=u.get("followers_count", 0),
                friends_count=u.get("friends_count", 0),
                status_count=u.get("status_count", 0),
                stocks_count=u.get("stocks_count", 0),
                description=u.get("description", ""),
                verified=u.get("verified", False),
                verified_type=u.get("verified_type", 0),
                province=u.get("province", ""),
                city=u.get("city", ""),
                gender=u.get("gender", ""),
                profile_image_url=u.get("profile_image_url", ""),
                follow_me=u.get("follow_me", False),
                following=u.get("following", False),
            )
            for u in data.get("friends", [])
        ]

    async def get_stock_community(
        self,
        symbol: str,
        max_pages: int = 3,
        posts_per_page: int = 20,
        sort: SortBy = SortBy.TIME,
        before: int | None = None,
    ) -> StockCommunity:
        """Fetch complete stock community data with metadata.

        Args:
            symbol: Stock symbol e.g. 'SH600519'
            max_pages: Maximum pages of posts to fetch
            posts_per_page: Posts per page
            sort: Sort order
            before: Unix timestamp (ms) — only return posts older than this.
        """
        if before and sort == SortBy.ALPHA:
            logger.info("alpha sort + before: hot posts span a wide time range, "
                        "no early-stop optimization")

        await self._navigate_to_stock(symbol)

        total_followers = await self._get_total_followers()

        all_posts = []
        total_count = 0
        hit_boundary = False
        for p in range(1, max_pages + 1):
            if hit_boundary:
                break
            try:
                response = await self.get_community_posts(
                    symbol=symbol,
                    page=p,
                    count=posts_per_page,
                    sort=sort,
                    _navigated=True,
                )
                if p == 1:
                    total_count = response.count

                kept = 0
                if before:
                    for post in response.items:
                        if post.created_at < before:
                            all_posts.append(post)
                            kept += 1
                    # Early-stop only for time sort (chronological order)
                    if sort == SortBy.TIME and response.items and all(
                        post.created_at < before for post in response.items
                    ):
                        hit_boundary = True
                else:
                    all_posts.extend(response.items)
                    kept = len(response.items)

                logger.info(
                    f"Fetched page {p}: {len(response.items)} posts "
                    f"(kept {kept})"
                )
                # No more pages available
                if not response.items:
                    break
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to fetch page {p}: {e}")
                break

        return StockCommunity(
            symbol=symbol,
            total_followers=total_followers,
            posts=all_posts,
            total_posts=total_count,
        )

    async def _get_total_followers(self) -> int:
        """Extract total follower count from the stock page."""
        try:
            text = await self._page.text_content("text=人关注了该股票")
            if text:
                import re
                match = re.search(r"(\d[\d,]*)\s*人关注", text)
                if match:
                    return int(match.group(1).replace(",", ""))
        except Exception:
            pass
        return 0

    async def get_hot_posts(self, max_pages: int = 3) -> list[CommunityPost]:
        """Fetch hot/trending posts from the Xueqiu homepage.

        Uses the /statuses/hot/listV3.json endpoint which returns the
        algorithmically ranked hot posts shown on the homepage.

        Args:
            max_pages: Maximum pages to fetch (each page ~20 posts).
        """
        # Start session (navigates to homepage to pass WAF)
        if not self._page or not self._browser:
            await self.start()

        # Use the anonymous recommend API (works without login).
        # category=205 is the homepage "recommended" feed.
        last_id = ""
        all_posts = []
        for p in range(1, max_pages + 1):
            try:
                params = {"category": 205, "page": p}
                if last_id:
                    params["last_id"] = last_id
                data = await self._api_call(
                    "/recommend-proxy/anonymous_recommend.json",
                    params,
                )
                items = data.get("list", [])
                posts = [self._parse_post(item) for item in items]
                all_posts.extend(posts)
                logger.info(f"Fetched hot page {p}: {len(posts)} posts")
                if not items:
                    break
                # Use last_id for cursor-based pagination
                last_id = items[-1].get("id", "") if items else ""
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to fetch hot page {p}: {e}")
                break

        return all_posts

    async def search_posts(
        self,
        keyword: str,
        max_pages: int = 3,
        count: int = 10,
        sort: SortBy = SortBy.TIME,
    ) -> list[CommunityPost]:
        """Search Xueqiu posts by keyword.

        Uses the /query/v1/search/status.json endpoint.

        Args:
            keyword: Search keyword.
            max_pages: Maximum pages to fetch.
            count: Posts per page (default 10).
            sort: SortBy.TIME (latest) or SortBy.ALPHA (comprehensive).
        """
        if not self._page or not self._browser:
            await self.start()

        # sortId: 1=comprehensive, 2=latest
        sort_id = 2 if sort == SortBy.TIME else 1

        all_posts = []
        for p in range(1, max_pages + 1):
            try:
                data = await self._api_call(
                    "/query/v1/search/status.json",
                    {"q": keyword, "sortId": sort_id, "count": count, "page": p},
                )
                items = data.get("list", [])
                posts = [self._parse_post(item) for item in items]
                all_posts.extend(posts)
                logger.info(
                    f"Searched page {p}/{data.get('maxPage', '?')}: "
                    f"{len(posts)} posts"
                )
                if not items or p >= data.get("maxPage", p):
                    break
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to search page {p}: {e}")
                break

        return all_posts

    async def get_stock_info(self, symbol: str) -> dict:
        """Get basic stock quote info."""
        await self._navigate_to_stock(symbol)

        data = await self._api_call(
            f"/stock/v5/stock/quote.json",
            {"symbol": symbol, "extend": "detail"},
        )
        return data
