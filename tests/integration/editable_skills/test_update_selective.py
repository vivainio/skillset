"""Sync respects skill selections in editable entries."""

import shutil
import textwrap
from pathlib import Path

import pytest

from skillset.commands import cmd_update
from tests.support import LocalEnv

from .conftest import FIXTURES, installed_skills


def _write_entry(
    toml_path: Path,
    source: Path,
    enabled: list[str],
    disabled: list[str] | None = None,
) -> None:
    body = textwrap.dedent(f"""\
        skills:
          editable-skills:
            editable: true
            source: {source}
            enabled: {enabled!r}
    """)
    if disabled:
        body += f"    disabled: {disabled!r}\n"
    toml_path.write_text(body)


class TestSyncEditableSelective:
    def test_sync_only_links_enabled(self, local_env: LocalEnv) -> None:
        """Write yaml manually with alpha+gamma enabled, beta disabled."""
        _write_entry(
            local_env.toml_path,
            FIXTURES,
            enabled=["alpha", "gamma"],
            disabled=["beta"],
        )

        cmd_update(file=str(local_env.toml_path))

        installed = installed_skills(local_env.skills_dir)
        assert "alpha" in installed
        assert "gamma" in installed
        assert "beta" not in installed

    def test_sync_removes_disabled_skill(self, local_env: LocalEnv) -> None:
        """If beta was previously linked, sync removes it when listed in disabled."""
        local_env.skills_dir.mkdir(parents=True, exist_ok=True)
        (local_env.skills_dir / "beta").symlink_to(FIXTURES / "beta")

        _write_entry(
            local_env.toml_path,
            FIXTURES,
            enabled=["alpha", "gamma"],
            disabled=["beta"],
        )

        cmd_update(file=str(local_env.toml_path))

        assert not (local_env.skills_dir / "beta").exists()

    def test_sync_removes_stale_symlink_when_skill_deleted_from_source(
        self, local_env: LocalEnv, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """If an enabled skill is removed from the source dir, its symlink is cleaned up."""
        editable_dir = tmp_path / "editable-skills"
        shutil.copytree(FIXTURES, editable_dir)

        _write_entry(
            local_env.toml_path,
            editable_dir,
            enabled=["alpha", "beta", "gamma"],
        )

        cmd_update(file=str(local_env.toml_path))
        assert installed_skills(local_env.skills_dir) == {"alpha", "beta", "gamma"}

        # Remove beta from the source directory
        shutil.rmtree(editable_dir / "beta")

        cmd_update(file=str(local_env.toml_path))

        installed = installed_skills(local_env.skills_dir)
        assert "alpha" in installed
        assert "gamma" in installed
        assert "beta" not in installed

        output = capsys.readouterr().out
        assert "removed from source" in output
