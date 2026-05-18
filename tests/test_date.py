"""Tests for date utilities."""
from src.utils.date import parse_date, days_ago_iso


def test_parse_date_iso():
    assert parse_date("2026-05-18T10:00:00") == "2026-05-18T10:00:00"


def test_parse_date_cn():
    assert parse_date("2026-05-18 10:00:00") == "2026-05-18T10:00:00"


def test_days_ago_iso():
    result = days_ago_iso(0)
    from datetime import date
    assert result.startswith(str(date.today()))
