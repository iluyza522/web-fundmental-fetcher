from datetime import datetime, timedelta, date


def parse_date(s: str) -> str:
    """Normalize various date formats to ISO 8601."""
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return s


def days_ago_iso(days: int) -> str:
    dt = date.today() - timedelta(days=days)
    return dt.strftime("%Y-%m-%d")
