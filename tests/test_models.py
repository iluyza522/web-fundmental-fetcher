"""Tests for data models."""
from src.models import FetchResult, SourceType


def test_fetch_result_minimal():
    r = FetchResult(
        source=SourceType.CNINFO,
        title="测试公告",
        content="正文",
        published_at="2026-05-18T10:00:00",
    )
    assert r.id is not None
    assert len(r.id) == 16
    assert r.stock_code is None


def test_fetch_result_full():
    r = FetchResult(
        source=SourceType.ZSXQ,
        title="测试帖",
        content="内容",
        published_at="2026-05-18T10:00:00",
        stock_code="000001",
        stock_name="平安银行",
        url="https://zsxq.com/123",
        authors=["作者"],
        tags=["讨论"],
        group_name="某星球",
        mentions_stocks=["000001"],
    )
    assert r.group_name == "某星球"
    assert r.mentions_stocks == ["000001"]


def test_fetch_result_id_deterministic():
    r1 = FetchResult(
        source=SourceType.CNINFO,
        title="公告",
        content="内容",
        published_at="2026-05-18T10:00:00",
    )
    r2 = FetchResult(
        source=SourceType.CNINFO,
        title="公告",
        content="内容",
        published_at="2026-05-18T10:00:00",
    )
    assert r1.id == r2.id


def test_fetch_result_id_different_source():
    r1 = FetchResult(
        source=SourceType.CNINFO,
        title="X",
        content="C",
        published_at="2026-05-18T10:00:00",
    )
    r2 = FetchResult(
        source=SourceType.EASTMONEY_REPORT,
        title="X",
        content="C",
        published_at="2026-05-18T10:00:00",
    )
    assert r1.id != r2.id


def test_fetch_result_to_dict():
    r = FetchResult(
        source=SourceType.CNINFO,
        title="公告",
        content="内容",
        published_at="2026-05-18T10:00:00",
        stock_code="000001",
    )
    d = r.to_dict()
    assert d["id"] == r.id
    assert d["source"] == "cninfo"
    assert d["stock_code"] == "000001"
