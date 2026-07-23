"""Tests for skillset.__main__ entry point."""

from unittest.mock import patch


def test_main_module_calls_main() -> None:
    with patch("skillset.cli.main") as mock_main:
        import runpy

        # Run __main__ as a module
        runpy.run_module("skillset", run_name="__main__")
        mock_main.assert_called_once()
