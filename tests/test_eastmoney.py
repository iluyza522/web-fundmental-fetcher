"""Tests for eastmoney fetcher."""
import pytest
from src.fetchers.eastmoney import EastmoneyReportFetcher, EastmoneyNewsFetcher


@pytest.mark.asyncio
async def test_eastmoney_report_fetch():
    f = EastmoneyReportFetcher()
    results = await f.fetch(stock_code="000001", limit=5)
    assert len(results) > 0
    for r in results:
        assert r.source.value == "eastmoney_report"
        assert r.title


@pytest.mark.asyncio
async def test_eastmoney_news_fetch():
    f = EastmoneyNewsFetcher()
    results = await f.fetch(stock_code="000001", limit=5)
    assert len(results) > 0
    for r in results:
        assert r.source.value == "eastmoney_news"
        assert r.title


@pytest.mark.asyncio
async def test_eastmoney_no_stock_code():
    f = EastmoneyReportFetcher()
    results = await f.fetch(limit=5)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_eastmoney_news_no_stock_code():
    f = EastmoneyNewsFetcher()
    results = await f.fetch(limit=5)
    assert len(results) == 0
