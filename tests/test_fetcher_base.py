"""Tests for fetcher base class."""
from src.fetchers.base import Fetcher
from src.models import FetchResult, SourceType


class DummyFetcher(Fetcher):
    source = SourceType.CNINFO

    async def fetch(self, stock_code=None, stock_name=None, since=None, limit=50):
        return [
            FetchResult(
                source=self.source,
                title="test",
                content="test",
                published_at="2026-05-18T10:00:00",
                stock_code=stock_code,
            )
        ]


def test_fetcher_abstract():
    f = DummyFetcher()
    assert f.source == SourceType.CNINFO


def test_fetcher_name_property():
    f = DummyFetcher()
    assert f.name == "cninfo"
