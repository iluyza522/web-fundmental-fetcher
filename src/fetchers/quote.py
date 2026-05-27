"""Fetcher for real-time stock market cap from 东方财富 via Playwright."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from playwright.async_api import async_playwright

from src.models import StockQuote, _format_market_cap


def _quote_page_url(stock_code: str) -> str:
    code = stock_code.strip()
    market = "sh" if code.startswith(("6", "9")) else "sz"
    return f"https://quote.eastmoney.com/{market}{code}.html"


def _parse_market_cap(text: str) -> tuple[float, str]:
    """Parse Chinese market cap text like '1.59万亿' to (yuan, display_str)."""
    text = text.strip().replace(",", "")
    m = re.match(r"([\d.]+)\s*万亿", text)
    if m:
        return float(m.group(1)) * 1e12, text
    m = re.match(r"([\d.]+)\s*亿", text)
    if m:
        return float(m.group(1)) * 1e8, text
    m = re.match(r"([\d.]+)\s*万", text)
    if m:
        return float(m.group(1)) * 1e4, text
    return 0.0, text


async def fetch_market_cap(stock_code: str) -> StockQuote:
    """Fetch current market cap for an A-share stock using browser.

    Navigates to the Eastmoney stock quote page, waits for the finance
    table to load, then extracts market cap from the DOM.

    Args:
        stock_code: Stock code, e.g. '600519', '000001'

    Returns:
        StockQuote with market cap and name
    """
    url = _quote_page_url(stock_code)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
        )

        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        # Extract stock name from title: "泰晶科技(603738)_最新价格_..."
        title = await page.title()
        name_match = re.match(r"(.+?)\(", title)
        name = name_match.group(1) if name_match else ""

        # Extract market cap from .finance4 table
        # Layout: header row (总市值, 净资产, ...) then data row (name, 180.9亿, ...)
        market_cap_text = ""
        finance = await page.query_selector(".finance4")
        if finance:
            rows = await finance.query_selector_all("tr")
            if len(rows) >= 2:
                cells = await rows[1].query_selector_all("td")
                if len(cells) >= 2:
                    market_cap_text = (await cells[1].inner_text()).strip()

        await browser.close()

    market_cap, display_str = _parse_market_cap(market_cap_text)

    return StockQuote(
        stock_code=stock_code,
        stock_name=name,
        market_cap=market_cap,
        market_cap_str=display_str or _format_market_cap(market_cap),
        updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
