"""Tests for skillset.__init__ version detection."""

from importlib.metadata import PackageNotFoundError
from unittest.mock import patch


def test_version_fallback_when_not_installed() -> None:
    with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
        # Re-import to trigger the except branch
        import importlib

        import skillset

        importlib.reload(skillset)
        assert skillset.__version__ == "0.0.0"


def test_version_from_metadata() -> None:
    import skillset

    # When installed, version comes from metadata
    assert isinstance(skillset.__version__, str)
    assert len(skillset.__version__) > 0
