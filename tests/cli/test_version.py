"""Tests for skillset CLI --version flag."""

from typer.testing import CliRunner

from skillset.cli import app

runner = CliRunner()


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "skillset" in result.output
