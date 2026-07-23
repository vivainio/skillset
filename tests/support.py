"""Shared typed values used by test fixtures."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Env:
    home: Path
    project: Path
    tmp: Path


@dataclass(frozen=True)
class LocalEnv(Env):
    toml_path: Path
    skills_dir: Path
