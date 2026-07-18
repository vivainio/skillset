"""Tests for CLI command wiring via CliRunner."""

from unittest.mock import patch

from typer.testing import CliRunner

from skillset.cli import app

runner = CliRunner()


def test_list_invokes_cmd_list():
    with patch("skillset.cli.cmd_list") as mock:
        runner.invoke(app, ["list"])
        mock.assert_called_once_with(prune=False, available=False)


def test_list_prune():
    with patch("skillset.cli.cmd_list") as mock:
        runner.invoke(app, ["list", "--prune"])
        mock.assert_called_once_with(prune=True, available=False)


def test_list_available():
    with patch("skillset.cli.cmd_list") as mock:
        runner.invoke(app, ["list", "--available"])
        mock.assert_called_once_with(prune=False, available=True)


def test_add_invokes_cmd_add():
    with patch("skillset.cli.cmd_add") as mock:
        runner.invoke(app, ["add", "owner/repo"])
        mock.assert_called_once()
        kwargs = mock.call_args[1]
        assert kwargs["repo"] == "owner/repo"


def test_add_with_options():
    with patch("skillset.cli.cmd_add") as mock:
        runner.invoke(app, ["add", "owner/repo", "--global", "--copy", "-s", "skill-a"])
        kwargs = mock.call_args[1]
        assert kwargs["g"] is True
        assert kwargs["copy"] is True
        assert kwargs["skills"] == ["skill-a"]


def test_remove_invokes_cmd_remove():
    with patch("skillset.cli.cmd_remove") as mock:
        runner.invoke(app, ["remove", "skill-a"])
        mock.assert_called_once_with(name="skill-a", g=False, interactive=False)


def test_add_interactive_flag():
    with patch("skillset.cli.cmd_add") as mock:
        runner.invoke(app, ["add", "-i"])
        kwargs = mock.call_args[1]
        assert kwargs["interactive"] is True


def test_remove_interactive_flag():
    with patch("skillset.cli.cmd_remove") as mock:
        runner.invoke(app, ["remove", "-i"])
        mock.assert_called_once_with(name=None, g=False, interactive=True)


def test_update_invokes_cmd_update():
    with patch("skillset.cli.cmd_update") as mock:
        runner.invoke(app, ["update"])
        mock.assert_called_once_with(file=None, g=False, new="ask", repair=False)


def test_update_repair_flag():
    with patch("skillset.cli.cmd_update") as mock:
        runner.invoke(app, ["update", "--repair"])
        mock.assert_called_once_with(file=None, g=False, new="ask", repair=True)


def test_init_invokes_cmd_init():
    with patch("skillset.cli.cmd_init") as mock:
        runner.invoke(app, ["init"])
        mock.assert_called_once_with(g=False)


def test_init_global():
    with patch("skillset.cli.cmd_init") as mock:
        runner.invoke(app, ["init", "--global"])
        mock.assert_called_once_with(g=True)


def test_install_skills_invokes_global_handler_without_options():
    with patch("skillset.cli.cmd_install_skills") as mock:
        result = runner.invoke(app, ["install-skills"])

        assert result.exit_code == 0
        mock.assert_called_once_with()


def test_install_skills_rejects_global_option():
    result = runner.invoke(app, ["install-skills", "--global"])

    assert result.exit_code != 0
    assert "No such option" in result.output


def test_clean_invokes_cmd_clean():
    with patch("skillset.cli.cmd_clean") as mock:
        runner.invoke(app, ["clean"])
        mock.assert_called_once_with(g=False)


def test_main_function():
    with patch("skillset.cli.app") as mock_app:
        from skillset.cli import main

        main()
        mock_app.assert_called_once()


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    # typer with no_args_is_help=True exits with code 0 or 2 depending on version
    assert result.exit_code in (0, 2)
    assert "Usage" in result.output or "Manage" in result.output
