#!/usr/bin/env python3
"""Bump the project version, build the dist, and print the publish command.

Usage:
    python scripts/release.py <version>

``<version>`` is either an explicit semver string (``0.2.0``) or a bump
keyword (``major`` / ``minor`` / ``patch``) applied to the current version in
``pyproject.toml``. The script:

  1. rewrites ``version = "..."`` under ``[project]`` in ``pyproject.toml``,
  2. runs ``uv build`` (sdist + wheel into ``dist/``),
  3. prints the ``uv publish`` command to run by hand.

It deliberately does NOT publish, commit, or tag — those stay manual so a
release is never one fat-fingered command away from going public.
"""

from __future__ import annotations

import datetime
import re
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

# Match the top-level project version line only (anchored, single-quoted or
# double-quoted), so we never touch a `version` key nested elsewhere.
_VERSION_RE = re.compile(r'^(version\s*=\s*)["\'][^"\']*["\']', re.MULTILINE)
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _current_version() -> str:
    with open(PYPROJECT, "rb") as f:
        return tomllib.load(f)["project"]["version"]


def _bump(current: str, part: str) -> str:
    if not _SEMVER_RE.match(current):
        sys.exit(f"Current version '{current}' is not X.Y.Z; pass an explicit version.")
    major, minor, patch = (int(n) for n in current.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def _resolve_target(arg: str, current: str) -> str:
    if arg in ("major", "minor", "patch"):
        return _bump(current, arg)
    if _SEMVER_RE.match(arg):
        return arg
    sys.exit(f"Invalid version '{arg}'; use X.Y.Z or major/minor/patch.")


def _write_version(new: str) -> None:
    text = PYPROJECT.read_text()
    updated, n = _VERSION_RE.subn(rf'\g<1>"{new}"', text, count=1)
    if n != 1:
        sys.exit("Could not find the project version line in pyproject.toml.")
    PYPROJECT.write_text(updated)


def _roll_changelog(new: str, today: str) -> bool:
    """Promote the ``[Unreleased]`` notes to a dated ``[new]`` section.

    Inserts a fresh empty ``## [Unreleased]`` above a new
    ``## [new] - today`` heading; the prior unreleased entries become that
    version's body. No-op (returns False) if there is no ``## [Unreleased]``
    heading or the target version already has a section.
    """
    text = CHANGELOG.read_text()
    if f"## [{new}]" in text:
        return False
    marker = "## [Unreleased]\n"
    if marker not in text:
        return False
    replacement = f"## [Unreleased]\n\n## [{new}] - {today}\n"
    CHANGELOG.write_text(text.replace(marker, replacement, 1))
    return True


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/release.py <X.Y.Z | major | minor | patch>")

    current = _current_version()
    new = _resolve_target(sys.argv[1], current)

    if new == current:
        sys.exit(f"Version is already {current}; nothing to bump.")

    print(f"Bumping version {current} -> {new}")
    _write_version(new)

    today = datetime.date.today().isoformat()
    if _roll_changelog(new, today):
        print(f"Rolled CHANGELOG [Unreleased] into [{new}] - {today}")
    else:
        print("CHANGELOG unchanged (no [Unreleased] section, or version exists).")

    # Clean stale artifacts so `dist/` only holds the version we just built.
    dist = REPO_ROOT / "dist"
    for old in dist.glob("*") if dist.exists() else []:
        old.unlink()

    print("Building (uv build)...")
    subprocess.run(["uv", "build"], cwd=REPO_ROOT, check=True)

    print()
    print("Built. Review the CHANGELOG diff before tagging.")
    print()
    print("Validate, then publish with:")
    print("  uvx twine check dist/*")
    print(f"  uv publish --token <pypi-token>   # publishes {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
