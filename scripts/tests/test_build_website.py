"""Tests for the static website builder."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

from build_website import (
    BuildState,
    PageInfo,
    WebsiteConfig,
    _disambiguate_url,
    build_website,
    collect_folder_markdown,
    collect_pages,
    derive_page_title,
    heading_to_anchor,
    is_excluded_dir,
    is_excluded_top_level_markdown,
    relative_link,
    render_markdown,
    replace_mermaid_blocks,
    rewrite_links,
    source_to_site_url,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def site_root(tmp_path: Path) -> Path:
    """Create a minimal repo-like tree the builder can render."""
    (tmp_path / "README.md").write_text(
        "<picture>\n"
        '  <source media="(prefers-color-scheme: dark)" '
        'srcset="resources/logos/course-logo-dark.svg">\n'
        '  <img alt="Course" src="resources/logos/course-logo.svg">\n'
        "</picture>\n\n"
        "# Home Page\n\nWelcome. See [Slash Commands](01-start/README.md).\n"
        "Also check [script](scripts/build.sh) and the [logo](resources/logos/logo.svg).\n"
    )
    (tmp_path / "LEARNING-ROADMAP.md").write_text(
        "# Learning Roadmap\n\nLink back to [Home](README.md#home-page).\n"
    )
    (tmp_path / "CONTRIBUTING.md").write_text("# Contributing\n\nHelp improve docs.")
    (tmp_path / "AGENTS.md").write_text("# Internal Agent Notes\n")
    (tmp_path / "update-plan-2026-05-02.md").write_text("# Temporary Plan\n")

    sc = tmp_path / "01-start"
    sc.mkdir()
    (sc / "README.md").write_text(
        "# Slash Commands\n\n## Advanced Usage\n\nMermaid time:\n\n```mermaid\nflowchart LR\nA-->B\n```\n\n"
        "See [example](example.md).\n"
    )
    (sc / "example.md").write_text("# Example\n\nGo back to [overview](README.md).\n")

    # Non-markdown repo files
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "build.sh").write_text("#!/bin/bash\necho hi\n")

    logos = tmp_path / "resources" / "logos"
    logos.mkdir(parents=True)
    (logos / "logo.svg").write_text("<svg></svg>")
    (logos / "course-logo.svg").write_text("<svg></svg>")
    (logos / "course-logo-dark.svg").write_text("<svg></svg>")

    return tmp_path


@pytest.fixture
def logger() -> logging.Logger:
    return logging.getLogger("test_build_website")


# =============================================================================
# heading_to_anchor parity with check_cross_references
# =============================================================================


class TestHeadingToAnchor:
    def test_simple_title(self) -> None:
        assert heading_to_anchor("Hello World") == "hello-world"

    def test_punctuation_removed(self) -> None:
        assert heading_to_anchor("What's Next?") == "whats-next"

    def test_unicode_preserved(self) -> None:
        assert heading_to_anchor("Hướng dẫn") == "hướng-dẫn"

    def test_emoji_stripped(self) -> None:
        # The validator strips emoji; we mirror that exactly.
        assert heading_to_anchor("🔥 Trending") == "-trending"


# =============================================================================
# source_to_site_url
# =============================================================================


class TestSourceToSiteUrl:
    def test_root_readme_maps_to_index(self) -> None:
        assert source_to_site_url("README.md") == "index.html"

    def test_folder_readme_maps_to_folder_index(self) -> None:
        assert (
            source_to_site_url("01-start/README.md")
            == "01-start/index.html"
        )

    def test_other_markdown_uses_html_extension(self) -> None:
        assert (
            source_to_site_url("01-start/example.md")
            == "01-start/example.html"
        )


class TestDisambiguateUrl:
    def test_no_collision_passes_through(self) -> None:
        used: set[str] = {"foo.html"}
        assert _disambiguate_url("bar.html", used, "bar.md") == "bar.html"

    def test_case_insensitive_collision_disambiguated(self) -> None:
        # README → index.html lands first; INDEX.md (case-insensitive collision)
        # must get a suffix on macOS / Windows filesystems.
        used: set[str] = {"index.html"}
        result = _disambiguate_url("INDEX.html", used, "INDEX.md")
        assert result.lower() != "index.html"
        assert result.endswith(".html")


# =============================================================================
# relative_link
# =============================================================================


class TestRelativeLink:
    def test_same_directory(self) -> None:
        assert relative_link("01/index.html", "01/example.html") == "example.html"

    def test_anchor_appended(self) -> None:
        assert (
            relative_link("01/index.html", "02/index.html", "#intro")
            == "../02/index.html#intro"
        )

    def test_self_link_returns_anchor_only(self) -> None:
        assert relative_link("01/index.html", "01/index.html", "#section") == "#section"

    def test_parent_directory(self) -> None:
        assert relative_link("01/index.html", "index.html") == "../index.html"


# =============================================================================
# is_excluded_dir
# =============================================================================


class TestIsExcludedDir:
    def test_hidden_dirs_excluded(self) -> None:
        assert is_excluded_dir(".git") is True

    def test_known_dir_excluded(self) -> None:
        assert is_excluded_dir("node_modules") is True

    def test_chapter_dir_kept(self) -> None:
        assert is_excluded_dir("01-start") is False


class TestIsExcludedTopLevelMarkdown:
    def test_internal_agent_file_excluded(self) -> None:
        assert is_excluded_top_level_markdown("AGENTS.md") is True

    def test_temporary_update_plan_excluded(self) -> None:
        assert is_excluded_top_level_markdown("update-plan-2026-05-02.md") is True

    def test_project_doc_included(self) -> None:
        assert is_excluded_top_level_markdown("CONTRIBUTING.md") is False


# =============================================================================
# collect_folder_markdown
# =============================================================================


class TestCollectFolderMarkdown:
    def test_readme_first(self, tmp_path: Path) -> None:
        (tmp_path / "b.md").write_text("# B")
        (tmp_path / "README.md").write_text("# Readme")
        (tmp_path / "a.md").write_text("# A")
        files = collect_folder_markdown(tmp_path)
        assert [f.name for f in files] == ["README.md", "a.md", "b.md"]

    def test_skips_hidden_subdirs(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# R")
        hidden = tmp_path / ".cache"
        hidden.mkdir()
        (hidden / "junk.md").write_text("# junk")
        files = collect_folder_markdown(tmp_path)
        assert [f.name for f in files] == ["README.md"]


class TestCollectPages:
    def test_additional_top_level_docs_are_collected(
        self, site_root: Path, logger: logging.Logger
    ) -> None:
        state = collect_pages(
            WebsiteConfig(root_path=site_root, output_path=site_root / "site"), logger
        )
        assert "CONTRIBUTING.md" in state.source_to_url
        assert state.source_to_url["CONTRIBUTING.md"] == "CONTRIBUTING.html"
        assert "AGENTS.md" not in state.source_to_url
        assert "update-plan-2026-05-02.md" not in state.source_to_url


# =============================================================================
# derive_page_title
# =============================================================================


class TestDerivePageTitle:
    def test_uses_h1(self, tmp_path: Path) -> None:
        f = tmp_path / "f.md"
        f.write_text("Some intro\n# The Title\nBody")
        assert derive_page_title(f, "Default") == "The Title"

    def test_falls_back_when_no_h1(self, tmp_path: Path) -> None:
        f = tmp_path / "f.md"
        f.write_text("No heading here")
        assert derive_page_title(f, "Default") == "Default"


# =============================================================================
# replace_mermaid_blocks
# =============================================================================


class TestReplaceMermaidBlocks:
    def test_replaces_fence(self) -> None:
        md = "Before\n\n```mermaid\nflowchart LR\nA-->B\n```\n\nAfter"
        out = replace_mermaid_blocks(md)
        assert '<pre class="mermaid">' in out
        assert "flowchart LR" in out
        assert "```mermaid" not in out

    def test_escapes_html(self) -> None:
        md = "```mermaid\nA --> B<C>\n```\n"
        out = replace_mermaid_blocks(md)
        assert "&lt;C&gt;" in out


# =============================================================================
# render_markdown
# =============================================================================


class TestRenderMarkdown:
    def test_heading_gets_github_anchor(self) -> None:
        html_content = render_markdown("# Hello World\n\nBody")
        assert 'id="hello-world"' in html_content

    def test_duplicate_headings_get_suffix(self) -> None:
        html_content = render_markdown("# Hi\n\n# Hi\n")
        assert 'id="hi"' in html_content
        assert 'id="hi-1"' in html_content


# =============================================================================
# rewrite_links
# =============================================================================


class TestRewriteLinks:
    def _state(self) -> BuildState:
        state = BuildState()
        state.source_to_url = {
            "README.md": "index.html",
            "01-start/README.md": "01-start/index.html",
        }
        return state

    def _config(self, root: Path) -> WebsiteConfig:
        return WebsiteConfig(
            root_path=root,
            output_path=root / "out",
            repo_url="https://github.com/example/repo",
            branch="main",
        )

    def test_internal_markdown_link_rewritten(
        self, tmp_path: Path, logger: logging.Logger
    ) -> None:
        (tmp_path / "README.md").write_text("# Home")
        (tmp_path / "01-start").mkdir()
        (tmp_path / "01-start" / "README.md").write_text("# Slash")
        page = PageInfo(
            source=tmp_path / "README.md",
            rel_source="README.md",
            output_url="index.html",
            title="Home",
            section="Introduction",
            is_section_index=True,
        )
        html_in = '<a href="01-start/README.md">go</a>'
        out = rewrite_links(
            html_in, page, self._state(), self._config(tmp_path), logger
        )
        assert "01-start/index.html" in out
        assert ".md" not in out

    def test_anchor_preserved(self, tmp_path: Path, logger: logging.Logger) -> None:
        (tmp_path / "README.md").write_text("# Home")
        (tmp_path / "01-start").mkdir()
        (tmp_path / "01-start" / "README.md").write_text("# Slash")
        page = PageInfo(
            source=tmp_path / "README.md",
            rel_source="README.md",
            output_url="index.html",
            title="Home",
            section="Introduction",
            is_section_index=True,
        )
        html_in = '<a href="01-start/README.md#run">go</a>'
        out = rewrite_links(
            html_in, page, self._state(), self._config(tmp_path), logger
        )
        assert "#run" in out

    def test_non_markdown_link_uses_local_source(
        self, tmp_path: Path, logger: logging.Logger
    ) -> None:
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "build.sh").write_text("#!/bin/bash")
        (tmp_path / "README.md").write_text("# Home")
        page = PageInfo(
            source=tmp_path / "README.md",
            rel_source="README.md",
            output_url="index.html",
            title="Home",
            section="Introduction",
            is_section_index=True,
        )
        html_in = '<a href="scripts/build.sh">script</a>'
        out = rewrite_links(
            html_in, page, self._state(), self._config(tmp_path), logger
        )
        assert "materials/scripts/build.sh.html" in out
        assert 'target="_blank"' not in out

    def test_repo_directory_link_uses_local_index(
        self, tmp_path: Path, logger: logging.Logger
    ) -> None:
        (tmp_path / "scripts").mkdir()
        (tmp_path / "README.md").write_text("# Home")
        page = PageInfo(
            source=tmp_path / "README.md",
            rel_source="README.md",
            output_url="index.html",
            title="Home",
            section="Introduction",
            is_section_index=True,
        )
        html_in = '<a href="scripts/">scripts</a>'
        out = rewrite_links(
            html_in, page, self._state(), self._config(tmp_path), logger
        )
        assert "materials/scripts/index.html" in out
        assert "github.com/example/repo/blob/main/scripts" not in out

    def test_repo_root_link_uses_local_index(
        self, tmp_path: Path, logger: logging.Logger
    ) -> None:
        (tmp_path / "README.md").write_text("# Home")
        page = PageInfo(
            source=tmp_path / "README.md",
            rel_source="README.md",
            output_url="index.html",
            title="Home",
            section="Introduction",
            is_section_index=True,
        )
        html_in = '<a href=".">repo root</a>'
        out = rewrite_links(
            html_in, page, self._state(), self._config(tmp_path), logger
        )
        assert "materials/index.html" in out
        assert "github.com/example/repo/blob/main/." not in out

    def test_external_link_left_alone(
        self, tmp_path: Path, logger: logging.Logger
    ) -> None:
        page = PageInfo(
            source=tmp_path / "README.md",
            rel_source="README.md",
            output_url="index.html",
            title="Home",
            section="Introduction",
            is_section_index=True,
        )
        (tmp_path / "README.md").write_text("# Home")
        html_in = '<a href="https://example.org">site</a>'
        out = rewrite_links(
            html_in, page, self._state(), self._config(tmp_path), logger
        )
        assert 'href="https://example.org"' in out


# =============================================================================
# Full build smoke test
# =============================================================================


class TestBuildWebsite:
    def test_smoke_build(self, site_root: Path, logger: logging.Logger) -> None:
        out_dir = site_root / "site"
        config = WebsiteConfig(
            root_path=site_root,
            output_path=out_dir,
            repo_url="https://github.com/example/repo",
            branch="main",
        )

        build_website(config, logger, skip_vendor=True)

        # Index page rendered
        index = out_dir / "index.html"
        assert index.exists()
        index_html = index.read_text(encoding="utf-8")
        assert "Home Page" in index_html
        assert "01-start/index.html" in index_html
        assert "CONTRIBUTING.html" in index_html
        # Non-markdown link rewritten to GitHub
        assert "materials/scripts/build.sh.html" in index_html
        # <source srcset> inside <picture> rewritten to point at assets/
        assert 'srcset="assets/resources/logos/' in index_html

        # Additional top-level docs rendered
        assert (out_dir / "CONTRIBUTING.html").exists()
        assert not (out_dir / "AGENTS.html").exists()
        assert not (out_dir / "update-plan-2026-05-02.html").exists()

        # Folder index rendered
        sc_index = out_dir / "01-start" / "index.html"
        assert sc_index.exists()
        sc_html = sc_index.read_text(encoding="utf-8")
        # Mermaid block became a <pre class="mermaid"> block
        assert '<pre class="mermaid">' in sc_html
        # Sibling markdown link rewritten
        assert "example.html" in sc_html

        # Example page rendered
        example_page = out_dir / "01-start" / "example.html"
        assert example_page.exists()
        example_html = example_page.read_text(encoding="utf-8")
        # Back-link to README rewrites to index.html
        assert "index.html" in example_html

        # Stylesheet copied into assets
        assert (out_dir / "assets" / "site.css").exists()
        # Logo copied into assets
        assert (out_dir / "assets" / "resources" / "logos" / "logo.svg").exists()
        # Template no longer references third-party CDNs.
        for hostile in (
            "cdn.tailwindcss.com",
            "cdn.jsdelivr.net",
            "fonts.googleapis.com",
        ):
            assert hostile not in index_html, (
                f"Built HTML still references {hostile} — CDN should be self-hosted"
            )


# =============================================================================
# vendor_assets module smoke test
# =============================================================================


