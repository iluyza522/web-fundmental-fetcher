from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional


class SourceType(str, Enum):
    CNINFO = "cninfo"
    EASTMONEY_REPORT = "eastmoney_report"
    EASTMONEY_NEWS = "eastmoney_news"
    ZSXQ = "zsxq"


def _compute_id(source: str, title: str, published_at: str) -> str:
    raw = f"{source}|{title}|{published_at}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class FetchResult:
    source: SourceType
    title: str
    content: str
    published_at: str

    # Optional common fields
    stock_code: Optional[str] = None
    stock_name: Optional[str] = None
    summary: Optional[str] = None
    url: Optional[str] = None
    authors: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    # ZSXQ-specific
    group_name: Optional[str] = None
    mentions_stocks: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not hasattr(self, "_id"):
            self._id = _compute_id(self.source.value, self.title, self.published_at)

    @property
    def id(self) -> str:
        return self._id if hasattr(self, "_id") else _compute_id(
            self.source.value, self.title, self.published_at
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        d["source"] = self.source.value
        d.pop("_id", None)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> FetchResult:
        data["source"] = SourceType(data["source"])
        return cls(**data)
