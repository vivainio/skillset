"""Git repository operations — clone, pull, parse specs."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Literal, overload

from skillset.paths import get_cache_dir, get_legacy_cache_dir


def _git_env() -> dict[str, str]:
    """Env that prevents git from prompting interactively for credentials.

    Without this, an HTTPS clone of a private repo blocks waiting for a
    password instead of failing fast and letting the SSH fallback run.
    """
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "true"  # /usr/bin/true exits 0 with no output
    env["SSH_ASKPASS"] = "true"
    env.pop("GIT_USERNAME", None)
    env.pop("GIT_PASSWORD", None)
    return env


@overload
def _git(
    *args: str,
    cwd: Path | None = None,
    check: bool = False,
    capture_output: bool = False,
    text: Literal[False] = False,
) -> subprocess.CompletedProcess[bytes]: ...


@overload
def _git(
    *args: str,
    cwd: Path | None = None,
    check: bool = False,
    capture_output: bool = False,
    text: Literal[True],
) -> subprocess.CompletedProcess[str]: ...


def _git(
    *args: str,
    cwd: Path | None = None,
    check: bool = False,
    capture_output: bool = False,
    text: bool = False,
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str]:
    """subprocess.run for git with the no-prompt env baked in."""
    return subprocess.run(
        ["git", *args],
        env=_git_env(),
        cwd=cwd,
        check=check,
        capture_output=capture_output,
        text=text,
    )


def parse_repo_spec(spec: str) -> tuple[str, str]:
    """Parse 'owner/repo' into (owner, repo)."""
    parts = spec.strip().split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid repo format: {spec}. Use 'owner/repo'")
    return parts[0], parts[1]


def parse_github_url(url: str) -> tuple[str, str, str | None, str | None] | None:
    """Parse a GitHub tree URL into (owner, repo, branch, subpath) or None.

    Handles:
      https://github.com/owner/repo
      https://github.com/owner/repo/tree/branch/path/to/subdir
    """
    import re

    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+)(?:/(.+))?)?/?$", url)
    if not m:
        return None
    return m.group(1), m.group(2).removesuffix(".git"), m.group(3), m.group(4)


def get_repo_dir(owner: str, repo: str) -> Path:
    """Get a repo directory, retaining an existing legacy clone when present."""
    current = get_cache_dir() / owner / repo
    legacy = get_legacy_cache_dir() / owner / repo
    if current.exists() or current.is_symlink() or not (legacy.exists() or legacy.is_symlink()):
        return current
    return legacy


def clone_or_pull(owner: str, repo: str, ref: str | None = None) -> Path:
    """Clone repo if not exists, or pull if it does. Returns repo path.

    If ref is set, checks out that branch/tag/sha after cloning or fetching.
    """
    repo_dir = get_repo_dir(owner, repo)
    https_url = f"https://github.com/{owner}/{repo}.git"
    ssh_url = f"git@github.com:{owner}/{repo}.git"

    if repo_dir.exists():
        try:
            _fetch_or_pull(repo_dir, ref, ssh_url)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else ""
            stdout = e.stdout.decode() if e.stdout else ""
            msg = stderr or stdout or "(no output)"
            print(f"Warning: git update failed in {repo_dir}:\n{msg}")
    else:
        print(f"Cloning {owner}/{repo}...")
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            _git("clone", https_url, str(repo_dir), check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            # If HTTPS fails (e.g., auth failed for private repo), try SSH
            stderr = e.stderr.decode() if e.stderr else ""
            if _is_https_auth_failure(stderr) or e.returncode == 128:
                print("HTTPS failed, trying SSH...")
                _git("clone", ssh_url, str(repo_dir), check=True, capture_output=True)
            else:
                raise
        if ref:
            _checkout_ref(repo_dir, ref)

    return repo_dir


def _is_https_auth_failure(stderr: str) -> bool:
    """Match HTTPS auth/not-found errors that should trigger SSH fallback."""
    return "Authentication failed" in stderr or "Repository not found" in stderr


def _fetch_or_pull(repo_dir: Path, ref: str | None, ssh_url: str) -> None:
    """Fetch (with ref) or pull (without). Retry over SSH on HTTPS auth failure."""
    args = ("fetch", "--tags", "--prune", "origin") if ref else ("pull",)
    try:
        _git(*args, cwd=repo_dir, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        if not _is_https_auth_failure(stderr):
            raise
        print("HTTPS failed, switching origin to SSH...")
        _git(
            "remote",
            "set-url",
            "origin",
            ssh_url,
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        _git(*args, cwd=repo_dir, check=True, capture_output=True)
    if ref:
        _checkout_ref(repo_dir, ref)


def _checkout_ref(repo_dir: Path, ref: str) -> None:
    """Check out ref and fast-forward if it tracks a remote branch."""
    _git("checkout", ref, cwd=repo_dir, check=True, capture_output=True)
    # No-op for detached HEAD (tags/SHAs); fast-forwards a tracking branch.
    _git("merge", "--ff-only", cwd=repo_dir, check=False, capture_output=True)


def get_head_sha(repo_dir: Path) -> str | None:
    """Return the full HEAD commit SHA for repo_dir, or None if unavailable."""
    try:
        result = _git("rev-parse", "HEAD", cwd=repo_dir, check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    sha = result.stdout.strip()
    return sha or None


def clone_to_temp(owner: str, repo: str, ref: str | None = None) -> Path:
    """Clone repo to a temp directory (caller must clean up). Returns repo path."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="skillset-"))
    repo_dir = tmp_dir / repo
    https_url = f"https://github.com/{owner}/{repo}.git"
    ssh_url = f"git@github.com:{owner}/{repo}.git"

    label = f"{owner}/{repo}" + (f"@{ref}" if ref else "")
    print(f"Cloning {label} (no-cache)...")
    clone_args = ["clone", "--depth", "1"]
    if ref:
        clone_args += ["--branch", ref]
    try:
        _git(*clone_args, https_url, str(repo_dir), check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        if _is_https_auth_failure(stderr) or e.returncode == 128:
            print("HTTPS failed, trying SSH...")
            _git(*clone_args, ssh_url, str(repo_dir), check=True, capture_output=True)
        else:
            raise
    return repo_dir
