"""Wrapper around the `scip-python` CLI."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class ScipNotInstalledError(RuntimeError):
    """Raised when the scip-python binary is not on PATH."""

    INSTALL_HINT = (
        "scip-python not found on PATH. Install with:\n"
        "    npm install -g @sourcegraph/scip-python"
    )

    def __init__(self) -> None:
        super().__init__(self.INSTALL_HINT)


def run_scip(repo_path: Path, output: Path) -> None:
    """Run `scip-python index` against repo_path, writing to output.

    Uses ``--cwd`` so that scip-python discovers the pyproject.toml inside
    ``repo_path`` rather than walking up to a parent project root.  This
    ensures monikers are rooted at the repo's own package names instead of
    the parent project's namespace.
    """
    if not shutil.which("scip-python"):
        raise ScipNotInstalledError()
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "scip-python",
            "index",
            "--cwd",
            str(repo_path),
            "--output",
            str(output),
        ],
        check=True,
    )
