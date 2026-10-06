"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project structure for testing."""
    readme = tmp_path / "README.md"
    readme.write_text("# Test Project\n\nThis is a test.")

    chapter_dir = tmp_path / "01-start"
    chapter_dir.mkdir()
    (chapter_dir / "overview.md").write_text("# Chapter Overview\n\nOverview content.")

    return tmp_path


def _symlinks_supported() -> bool:
    import tempfile
    try:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.txt"
            src.write_text("x")
            dst = Path(td) / "dst.txt"
            dst.symlink_to(src)
            return True
    except OSError:
        return False


_HAS_SYMLINKS = _symlinks_supported()


def pytest_collection_modifyitems(config, items):
    if not _HAS_SYMLINKS:
        skip_symlink = pytest.mark.skip(reason="Platform lacks unprivileged symlink support (WinError 1314)")
        for item in items:
            if "symlink" in item.name.lower():
                item.add_marker(skip_symlink)

