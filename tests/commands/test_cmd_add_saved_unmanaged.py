from skillset.commands import cmd_add
from skillset.manifest import load_manifest
from tests.support import Env


def test_add_restores_saved_unmanaged_skill_globally(env: Env) -> None:
    stored = env.home / ".claude" / ".skillset" / "skills" / "personal"
    stored.mkdir(parents=True)
    (stored / "SKILL.md").write_text("# Personal\n")

    cmd_add(repo="personal", g=True)

    installed = env.home / ".claude" / "skills" / "personal"
    assert installed.is_symlink()
    assert installed.resolve() == stored
    assert load_manifest() == {}
