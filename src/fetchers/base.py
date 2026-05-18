from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.models import FetchResult, SourceType


class Fetcher(ABC):
    source: SourceType

    @property
    def name(self) -> str:
        return self.source.value

    @abstractmethod
    async def fetch(
        self,
        stock_code: Optional[str] = None,
        stock_name: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 50,
    ) -> list[FetchResult]:
        ...
