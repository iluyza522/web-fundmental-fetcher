from __future__ import annotations

from pathlib import Path

import toml

_DEFAULT_DATA_DIR = Path.home() / ".fundamental-data"


class Config:
    def __init__(
        self,
        data_dir: Path | str = _DEFAULT_DATA_DIR,
        zsxq_cookie: str = "",
    ):
        self.data_dir = Path(data_dir)
        self.zsxq_cookie = zsxq_cookie

    def to_dict(self) -> dict:
        return {
            "data_dir": str(self.data_dir),
            "zsxq_cookie": self.zsxq_cookie,
        }


def load_config(path: str | Path | None = None) -> Config:
    path = Path(path) if path else Path("config.toml")
    if not path.exists():
        return Config()
    raw = toml.load(path)
    data = raw.get("config", raw)
    return Config(
        data_dir=data.get("data_dir", _DEFAULT_DATA_DIR),
        zsxq_cookie=data.get("zsxq_cookie", ""),
    )


def save_config(config: Config, path: str | Path = Path("config.toml")) -> None:
    path = Path(path)
    path.write_text(toml.dumps({"config": config.to_dict()}))
