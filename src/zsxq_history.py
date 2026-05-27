"""Track last-fetched state per zsxq group for incremental fetching."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class ZsxqHistory:
    """Persist latest message info per group to detect new messages."""

    def __init__(self, data_dir: Path):
        self._path = data_dir / "zsxq" / "history.json"
        self._data: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        if self._path.exists():
            return json.loads(self._path.read_text())
        return {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2)
        )

    def latest(self, group_name: str) -> dict | None:
        """Return {published_at, preview} for a group, or None."""
        return self._data.get(group_name)

    def update(self, group_name: str, published_at: str, content: str) -> None:
        """Record the latest message for a group."""
        self._data[group_name] = {
            "published_at": published_at,
            "preview": content[:2],
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._save()

    def is_new(self, group_name: str, published_at: str, content: str) -> bool:
        """Check if a message is newer than what we've seen."""
        prev = self.latest(group_name)
        if prev is None:
            return True
        if published_at <= prev["published_at"]:
            return False
        # Same timestamp → check preview (content changed but timestamp didn't)
        if published_at == prev["published_at"] and content[:2] == prev.get("preview"):
            return False
        return True
