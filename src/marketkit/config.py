"""marketkit configuration helpers: package discovery, project root, template installation."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from .constants import RESEARCH_DIR_NAME


def _find_project_root() -> Path | None:
    """Walk up from cwd looking for a .market-research/ directory.

    Returns:
        Path to the project root (parent of .market-research/), or None if not found.
    """
    current = Path.cwd()
    while True:
        if (current / RESEARCH_DIR_NAME).is_dir():
            return current
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            return None
        current = parent


def _find_package_dir(subdir: str) -> Path:
    """Find a package subdirectory (e.g. templates/).

    Search order:
    1. Project root (dev mode / source checkout)
    2. importlib.resources (pip install) — bundled inside the wheel
    """
    root = Path(__file__).parent.parent.parent
    candidate = root / subdir
    if candidate.is_dir():
        return candidate

    # Installed mode: check inside the package
    try:
        pkg = files("marketkit")
        candidate = Path(str(pkg)) / subdir
        if candidate.is_dir():
            return candidate
    except Exception:
        pass

    raise FileNotFoundError(f"Could not find {subdir} directory")


def _install_command_template(src: Path, dest: Path):
    """Copy a command template to the project commands directory."""
    import shutil
    shutil.copy2(src, dest)
