from __future__ import annotations

import json
from pathlib import Path

from src.models import FetchResult, SourceType


class Storage:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def _result_path(self, r: FetchResult) -> Path:
        if r.source == SourceType.ZSXQ:
            group = r.group_name or "default"
            base = self.data_dir / "zsxq" / group
        else:
            code = r.stock_code or "unknown"
            base = self.data_dir / code / r.source.value
        month = r.published_at[:7]  # YYYY-MM
        return base / month / f"{r.id}.json"

    def exists(self, r: FetchResult) -> bool:
        return self._result_path(r).exists()

    def save(self, r: FetchResult) -> Path:
        path = self._result_path(r)
        if path.exists():
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(r.to_dict(), ensure_ascii=False, indent=2))
        return path
