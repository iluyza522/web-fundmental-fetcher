"""Tests for config."""
from pathlib import Path
from src.config import Config, load_config, _DEFAULT_DATA_DIR


def test_config_defaults():
    c = Config()
    assert c.data_dir == _DEFAULT_DATA_DIR
    assert c.zsxq_cookie == ""


def test_config_load_with_file(tmp_path):
    content = f"""
data_dir = "/tmp/ff-data"
zsxq_cookie = "test-cookie"
"""
    p = tmp_path / "config.toml"
    p.write_text(content)
    c = load_config(p)
    assert c.data_dir.resolve() == Path("/tmp/ff-data").resolve()
    assert c.zsxq_cookie == "test-cookie"


def test_config_to_dict():
    c = Config(zsxq_cookie="abc")
    d = c.to_dict()
    assert d["zsxq_cookie"] == "abc"
    assert d["data_dir"] == str(_DEFAULT_DATA_DIR)
