"""Tests for CLI."""
from click.testing import CliRunner
from src.cli import main


def test_cli_search_no_code():
    runner = CliRunner()
    result = runner.invoke(main, ["search"])
    assert result.exit_code != 0


def test_cli_config_no_args():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["config"])
        assert result.exit_code == 0
        assert "data dir" in result.output.lower() or "cookie" in result.output.lower()


def test_cli_zsxq_list_no_cookie():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["zsxq", "list"])
        assert result.exit_code == 0 or "cookie" in result.output.lower()


def test_cli_xueqiu_search_no_symbol():
    runner = CliRunner()
    result = runner.invoke(main, ["xueqiu", "search"])
    assert result.exit_code != 0
