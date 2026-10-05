#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["markdown-it-py==4.2.0", "beautifulsoup4==4.14.3", "jinja2==3.1.6"]
# ///

"""Автономная сборка курса Codex CLI. Python, Jinja2, Markdown; сеть не используется.
Команда: python scripts/build_website.py --output .learning/site
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

import markdown_adapter as markdown
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Make sibling script modules importable regardless of cwd.
sys.path.insert(0, str(Path(__file__).parent))

import os
import tempfile
from dataclasses import replace
from course_core import tree_hash, sha256, contained, source_files, load_json, check_course


# =============================================================================
# Configuration
# =============================================================================

REPO_URL = "https://github.com/RuslanGrigorev/codex-howto"
DEFAULT_BRANCH = "main"

# Files/dirs that exist in the repo but should not appear on the site.
EXCLUDE_DIRS = {
    ".git",
    ".learning",
    "third_party",
    ".github",
    ".gemini",
    ".agent",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "blog-posts",
    "openspec",
    "prompts",
    ".agents",
    "archive",
    "local-progress",
    "promo-video",
    "slides",
    ".gitissue",
    ".asm-improver",
    ".codex",
    ".opencode",
    "site",
    "scripts",
    "vi",
    "zh",
    "ja",
    "uk",
    "docs",
}

# Top-level markdown files that should not be rendered as standalone pages.
EXCLUDE_TOP_LEVEL = {
    "README.backup.md",
    "AGENTS.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "clean-code-rules.md",
    "CATALOG.md",
    "INDEX.md",
    "QUICK_REFERENCE.md",
    "LEARNING-ROADMAP.md",
    "STYLE_GUIDE.md",
    "resources.md",
}

EXCLUDE_TOP_LEVEL_PREFIXES = ("update-plan",)

# Match the course curriculum chapter ordering.
CHAPTER_ORDER: list[tuple[str, str]] = [
    ("README.md", "Введение"),
    ("01-start", "01. Начало работы"),
    ("02-workflow", "02. Рабочий цикл"),
    ("03-safety", "03. Безопасность"),
    ("04-instructions", "04. Инструкции"),
    ("05-sessions", "05. Сессии"),
    ("06-skills", "06. Навыки"),
    ("07-mcp", "07. MCP"),
    ("08-automation", "08. Автоматизация"),
    ("09-extensions", "09. Расширения"),
    ("10-capstone", "10. Итоговый проект"),
    ("reference", "Справочник"),
]


@dataclass
class WebsiteConfig:
    """Configuration for the website builder."""

    root_path: Path
    output_path: Path
    repo_url: str = REPO_URL
    branch: str = DEFAULT_BRANCH
    site_title: str = "Codex CLI: интерактивный курс и справочник"
    site_subtitle: str = "Практическое руководство и автономный справочник по Codex CLI"
    language: str = "ru"
    landing: bool = False  # render the marketing landing page as index.html
    roadmap_path: Path | None = None  # defaults to website_templates/roadmap.json
    ui_strings: dict[str, str] = field(default_factory=dict)


@dataclass
class PageInfo:
    """A single page generated for the site."""

    source: Path  # absolute path to the markdown source
    rel_source: str  # path relative to repo root (POSIX style)
    output_url: str  # site-relative URL, e.g. `01-slash-commands/index.html`
    title: str
    section: str  # the chapter group name (e.g. "Slash Commands")
    is_section_index: bool = False
    content: str | None = None  # cached source text (read once during collection)


@dataclass
class BuildState:
    """Build-time state shared across page rendering."""

    pages: list[PageInfo] = field(default_factory=list)
    source_to_url: dict[str, str] = field(default_factory=dict)
    page_anchors: dict[str, set[str]] = field(default_factory=dict)


# =============================================================================
# Logging
# =============================================================================


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging for the website builder."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("website_builder")


# =============================================================================
# Anchor algorithm (mirrors check_cross_references.heading_to_anchor)
# =============================================================================


def heading_to_anchor(heading: str) -> str:
    """Convert a heading to a GitHub-style anchor.

    Mirrors `scripts/check_cross_references.heading_to_anchor` so the website
    resolves the same `#anchor` references the validator accepts.
    """
    heading = re.sub(
        r"[\U0001F000-\U0001FFFF"
        r"\U00002702-\U000027B0"
        r"\U0000FE00-\U0000FE0F"
        r"\U0000200D"
        r"\U000000A9\U000000AE"
        r"\U00002000-\U0000206F"
        r"]",
        "",
        heading,
    )
    anchor = re.sub(r"[^\w\s-]", "", heading.lower(), flags=re.UNICODE)
    anchor = anchor.replace(" ", "-")
    return anchor.rstrip("-")


# =============================================================================
# Source discovery
# =============================================================================


def is_excluded_dir(name: str) -> bool:
    return name.startswith(".") or name in EXCLUDE_DIRS


def collect_folder_markdown(folder: Path) -> list[Path]:
    """Return markdown files inside a chapter folder.

    Order: README.md first (if present), then other top-level markdown files
    sorted alphabetically, then markdown files from non-hidden subfolders.
    """
    files: list[Path] = []
    readme = folder / "README.md"
    if readme.exists():
        files.append(readme)

    files.extend(md for md in sorted(folder.glob("*.md")) if md.name != "README.md")

    for sub in sorted(folder.iterdir()):
        if sub.is_dir() and not is_excluded_dir(sub.name):
            files.extend(collect_folder_markdown(sub))

    return files


def is_excluded_top_level_markdown(name: str) -> bool:
    return name in EXCLUDE_TOP_LEVEL or any(
        name.startswith(prefix) for prefix in EXCLUDE_TOP_LEVEL_PREFIXES
    )


def read_source(md_path: Path) -> str | None:
    """Read a markdown source file once, returning None on read failure."""
    try:
        return md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def title_from_content(content: str | None, default: str) -> str:
    """Pick a page title from the first H1, falling back to the default."""
    if content is None:
        return default
    match = re.search(r"^#\s+(.+?)\s*$", content, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()
    return default


def derive_page_title(md_path: Path, default: str) -> str:
    """Pick a page title from a file's first H1, falling back to the default."""
    return title_from_content(read_source(md_path), default)


def source_to_site_url(rel_source: str) -> str:
    """Map `01-slash-commands/README.md` → `01-slash-commands/index.html`."""
    if rel_source == "README.md":
        return "index.html"
    if rel_source.endswith("/README.md"):
        return rel_source[: -len("README.md")] + "index.html"
    if rel_source.endswith(".md"):
        return rel_source[:-3] + ".html"
    return rel_source


def _disambiguate_url(url: str, used_lower: set[str], rel_source: str) -> str:
    """Avoid case-insensitive filesystem collisions (e.g. INDEX.html ↔ index.html).

    macOS/Windows treat `INDEX.html` and `index.html` as the same file. When
    two source files would resolve to URLs that differ only in case, suffix
    the second one with the source stem so both pages survive the build.
    """
    if url.lower() not in used_lower:
        return url
    parent, sep, leaf = url.rpartition("/")
    stem, dot, ext = leaf.rpartition(".")
    src_stem = Path(rel_source).stem.lower()
    candidate = f"{parent}{sep}{stem}-{src_stem}{dot}{ext}"
    suffix = 2
    while candidate.lower() in used_lower:
        candidate = f"{parent}{sep}{stem}-{src_stem}-{suffix}{dot}{ext}"
        suffix += 1
    return candidate


def get_effective_chapter_order(config: WebsiteConfig) -> list[tuple[str, str]]:
    """Determine chapter order from course.json if present, falling back to CHAPTER_ORDER."""
    course_path = config.root_path / "course.json"

    if course_path.exists():
        is_ru = (config.language == "ru")
        order: list[tuple[str, str]] = [("README.md", "Введение" if is_ru else "Introduction")]
        try:
            data = json.loads(course_path.read_text(encoding="utf-8"))
            for mod in data.get("modules", []):
                mid = str(mod.get("id", ""))
                m_order = mod.get("order", 1)
                candidates = [f"{m_order:02d}-{mid}", mid]
                found = None
                for cand in candidates:
                    if (config.root_path / cand).exists():
                        found = cand
                        break
                if found:
                    order.append((found, str(mod.get("title", mid))))
        except Exception:
            pass

        if (config.root_path / "reference").exists():
            order.append(("reference", "Справочник" if is_ru else "Reference"))
        return order

    return CHAPTER_ORDER


def collect_pages(config: WebsiteConfig, logger: logging.Logger) -> BuildState:
    """Walk the configured chapter order and produce a flat list of pages."""
    state = BuildState()
    seen: set[str] = set()
    used_urls: set[str] = set()

    chapter_order = get_effective_chapter_order(config)
    for item, display_name in chapter_order:
        item_path = config.root_path / item
        if not item_path.exists():
            logger.debug(f"Skipping missing chapter target: {item}")
            continue

        if item_path.is_file() and item_path.suffix == ".md":
            if is_excluded_top_level_markdown(item) or item in seen:
                continue
            seen.add(item)
            content = read_source(item_path)
            page_title = title_from_content(content, display_name)
            url = source_to_site_url(item)
            if config.landing and item == "README.md":
                # The landing page takes index.html; the README becomes guide.html.
                url = "guide.html"
            url = _disambiguate_url(url, used_urls, item)
            used_urls.add(url.lower())
            state.pages.append(
                PageInfo(
                    source=item_path,
                    rel_source=item,
                    output_url=url,
                    title=page_title,
                    section=display_name,
                    is_section_index=True,
                    content=content,
                )
            )
        elif item_path.is_dir():
            folder_files = collect_folder_markdown(item_path)
            if (config.root_path / 'course.json').exists():
                ordered = {l['path']: n for m in load_json(config.root_path / 'course.json')['modules'] for n, l in enumerate(m['lessons'])}
                folder_files.sort(key=lambda p: ((-1 if p.name == "README.md" else ordered.get(p.relative_to(config.root_path).as_posix(), 100000)), p.name))
            for md in folder_files:
                rel = md.relative_to(config.root_path).as_posix()
                if rel in seen:
                    continue
                seen.add(rel)
                is_index = md.name == "README.md" and md.parent == item_path
                content = read_source(md)
                title = title_from_content(
                    content, display_name if is_index else md.stem
                )
                url = _disambiguate_url(source_to_site_url(rel), used_urls, rel)
                used_urls.add(url.lower())
                state.pages.append(
                    PageInfo(
                        source=md,
                        rel_source=rel,
                        output_url=url,
                        title=title,
                        section=display_name,
                        is_section_index=is_index,
                        content=content,
                    )
                )
        else:
            logger.warning(f"Chapter target is not a file or directory: {item}")

    for md in sorted(config.root_path.glob("*.md")):
        rel = md.relative_to(config.root_path).as_posix()
        if is_excluded_top_level_markdown(md.name) or rel in seen:
            continue
        seen.add(rel)
        title_default = md.stem.replace("-", " ").replace("_", " ").title()
        content = read_source(md)
        title = title_from_content(content, title_default)
        url = _disambiguate_url(source_to_site_url(rel), used_urls, rel)
        used_urls.add(url.lower())
        state.pages.append(
            PageInfo(
                source=md,
                rel_source=rel,
                output_url=url,
                title=title,
                section="О проекте",
                is_section_index=False,
                content=content,
            )
        )

    for page in state.pages:
        state.source_to_url[page.rel_source] = page.output_url

    logger.info(f"Collected {len(state.pages)} pages across the curriculum")
    return state


# =============================================================================
# Link rewriting
# =============================================================================


def is_external(href: str) -> bool:
    return href.startswith(("http://", "https://", "mailto:", "tel:"))


def relative_link(from_url: str, to_url: str, anchor: str = "") -> str:
    """Build a relative URL from `from_url` to `to_url` (both site-relative)."""
    if from_url == to_url:
        return anchor or from_url.rsplit("/", 1)[-1]
    from_parts = from_url.split("/")[:-1]
    to_parts = to_url.split("/")

    common = 0
    for a, b in zip(from_parts, to_parts, strict=False):
        if a != b:
            break
        common += 1

    ups = [".."] * (len(from_parts) - common)
    downs = to_parts[common:]
    parts = ups + downs
    rel = "/".join(parts) if parts else to_parts[-1]
    return rel + anchor


def _resolve_repo_relative(href: str, page_dir: Path, root_path: Path) -> str | None:
    """Resolve `href` relative to `page_dir` and return its repo-relative path."""
    resolved = (page_dir / href).resolve()
    try:
        rel_to_root = resolved.relative_to(root_path)
    except ValueError:
        return None
    return rel_to_root.as_posix()


def _github_source_url(
    config: WebsiteConfig, rel_str: str, *, is_dir: bool, anchor: str = ""
) -> str:
    kind = "tree" if is_dir else "blob"
    if rel_str == ".":
        return f"{config.repo_url}/{kind}/{config.branch}{anchor}"
    return f"{config.repo_url}/{kind}/{config.branch}/{rel_str}{anchor}"


def _rewrite_anchor(
    a: object,
    page: PageInfo,
    state: BuildState,
    config: WebsiteConfig,
    logger: logging.Logger,
) -> None:
    """Rewrite a single `<a href>` to its site URL or local source URL."""
    href = a.get("href", "")  # type: ignore[attr-defined]
    from urllib.parse import urlsplit, unquote
    if not href or href == "#":
        raise RuntimeError(f"Пустая ссылка в {page.rel_source}")
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme not in {"https", "http", "mailto", "tel"} or parsed.netloc and not parsed.scheme:
            raise RuntimeError(f"Недопустимая URL-схема в {page.rel_source}: {href}")
        return
    if href.startswith("#"):
        return
    if parsed.query:
        raise RuntimeError(f"Параметры локальной ссылки не поддерживаются: {href}")
    href = unquote(href)

    anchor = ""
    if "#" in href:
        href, anchor_part = href.split("#", 1)
        anchor = "#" + anchor_part
    if not href:
        return

    rel_str = _resolve_repo_relative(href, page.source.parent, config.root_path)
    if rel_str is None:
        raise RuntimeError(f"Ссылка выходит за пределы проекта: {href} ({page.rel_source})")

    candidates = [rel_str]
    resolved = (page.source.parent / href).resolve()
    if not rel_str.endswith(".md") and resolved.is_dir():
        candidates.append(rel_str + "/README.md")

    for candidate in candidates:
        if candidate in state.source_to_url:
            a["href"] = relative_link(  # type: ignore[index]
                page.output_url, state.source_to_url[candidate], anchor
            )
            return

    if not resolved.exists():
        raise RuntimeError(f"Не найдена локальная ссылка {href} в {page.rel_source}")
    target = material_url(rel_str, resolved.is_dir())
    a["href"] = relative_link(page.output_url, target, anchor)


def _rewrite_asset_ref(
    element: object,
    attr: str,
    raw_value: str,
    page: PageInfo,
    config: WebsiteConfig,
) -> None:
    """Rewrite a single asset reference (img.src / source.srcset) to assets/."""
    if not raw_value or is_external(raw_value):
        return
    first = raw_value.split(",", 1)[0].strip().split(" ", 1)[0]
    if not first or is_external(first):
        return
    rel_str = _resolve_repo_relative(first, page.source.parent, config.root_path)
    if rel_str is None:
        return
    target = "assets/" + rel_str
    element[attr] = relative_link(page.output_url, target)  # type: ignore[index]


def rewrite_links_in_soup(
    soup: BeautifulSoup,
    page: PageInfo,
    state: BuildState,
    config: WebsiteConfig,
    logger: logging.Logger,
) -> None:
    """Rewrite anchor/image hrefs of `soup` in place to resolve on the site."""
    for a in soup.find_all("a"):
        _rewrite_anchor(a, page, state, config, logger)

    for img in soup.find_all("img"):
        _rewrite_asset_ref(img, "src", img.get("src", ""), page, config)
        if img.get("src"):
            img["loading"] = "lazy"

    for source in soup.find_all("source"):
        _rewrite_asset_ref(source, "srcset", source.get("srcset", ""), page, config)


def rewrite_links(
    html_content: str,
    page: PageInfo,
    state: BuildState,
    config: WebsiteConfig,
    logger: logging.Logger,
) -> str:
    """String wrapper around :func:`rewrite_links_in_soup`."""
    soup = BeautifulSoup(html_content, "html.parser")
    rewrite_links_in_soup(soup, page, state, config, logger)
    return str(soup)


# =============================================================================
# Mermaid handling
# =============================================================================


MERMAID_BLOCK_RE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)


def replace_mermaid_blocks(md_content: str) -> str:
    """Replace ```mermaid``` fences with `<pre class="mermaid">` for client-side render."""

    def _replace(match: re.Match[str]) -> str:
        code = match.group(1)
        return f'<pre class="mermaid">{html.escape(code)}</pre>'

    return MERMAID_BLOCK_RE.sub(_replace, md_content)


# =============================================================================
# Markdown rendering
# =============================================================================


def normalise_heading_ids_in_soup(soup: BeautifulSoup) -> None:
    """Force GitHub-style anchor ids on every heading of `soup`, in place.

    `python-markdown`'s `toc` extension generates its own slug; we re-write them
    so they match `check_cross_references.heading_to_anchor`.
    """
    used: dict[str, int] = {}
    for level in ("h1", "h2", "h3", "h4", "h5", "h6"):
        for h in soup.find_all(level):
            text = h.get_text(strip=True)
            anchor = heading_to_anchor(text)
            if not anchor:
                continue
            count = used.get(anchor, 0)
            final = anchor if count == 0 else f"{anchor}-{count}"
            used[anchor] = count + 1
            h["id"] = final


def normalise_heading_ids(html_content: str) -> str:
    """String wrapper around :func:`normalise_heading_ids_in_soup`."""
    soup = BeautifulSoup(html_content, "html.parser")
    normalise_heading_ids_in_soup(soup)
    return str(soup)


def extract_toc_from_soup(soup: BeautifulSoup) -> list[dict[str, str]]:
    """Pull H2/H3 headings of `soup` into a flat list for in-page navigation."""
    toc: list[dict[str, str]] = []
    for h in soup.find_all(["h2", "h3"]):
        anchor = h.get("id")
        if not anchor:
            continue
        toc.append(
            {
                "level": h.name,
                "text": h.get_text(strip=True),
                "anchor": anchor,
            }
        )
    return toc


def extract_toc(html_content: str) -> list[dict[str, str]]:
    """String wrapper around :func:`extract_toc_from_soup`."""
    return extract_toc_from_soup(BeautifulSoup(html_content, "html.parser"))


def render_markdown_to_soup(md_content: str) -> BeautifulSoup:
    """Render markdown to a parsed soup with GitHub-style heading ids applied.

    Parsing the rendered HTML once here lets the caller run TOC extraction and
    link rewriting against the same tree instead of reparsing per stage.
    """
    md_content = replace_mermaid_blocks(md_content)
    html_content = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "codehilite", "toc"],
        extension_configs={"codehilite": {"guess_lang": False}},
    )
    soup = BeautifulSoup(html_content, "html.parser")
    normalise_heading_ids_in_soup(soup)
    return soup


def render_markdown(md_content: str) -> str:
    """Преобразовать Markdown в локальный HTML курса."""
    return str(render_markdown_to_soup(md_content))


# =============================================================================
# Asset copying
# =============================================================================


ASSET_EXTENSIONS = {
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
}


def copy_assets(
    config: WebsiteConfig, state: BuildState, logger: logging.Logger
) -> None:
    """Copy images referenced by any rendered page into `<output>/assets/`."""
    assets_dir = config.output_path / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    copied: set[Path] = set()

    for page in state.pages:
        content = page.content if page.content is not None else read_source(page.source)
        if content is None:
            continue
        for match in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", content):
            src = match.group(1).split(" ", 1)[0]
            if is_external(src):
                continue
            resolved = (page.source.parent / src).resolve()
            if not resolved.exists() or not resolved.is_file():
                continue
            if resolved.suffix.lower() not in ASSET_EXTENSIONS:
                continue
            try:
                rel = resolved.relative_to(config.root_path)
            except ValueError:
                continue
            target = assets_dir / rel
            if target in copied:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(resolved, target)
            copied.add(target)

    # Always copy the logo set so the site header can reuse it.
    logo_dir = config.root_path / "resources" / "logos"
    if logo_dir.exists():
        for logo in logo_dir.glob("*.svg"):
            try:
                rel = logo.relative_to(config.root_path)
            except ValueError:
                continue
            target = assets_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(logo, target)
            copied.add(target)

    logger.info(f"Copied {len(copied)} asset file(s) into {assets_dir}")


# =============================================================================
# Page rendering
# =============================================================================


def build_nav_skeleton(state: BuildState) -> list[dict[str, object]]:
    """Group pages into sidebar sections once, keyed by section name.

    The grouping (sections + ordered page list) is identical for every page,
    so it is computed a single time and reused. `localize_nav` then turns the
    absolute page URLs into per-page relative URLs — an O(n) pass instead of
    re-grouping all pages for every page (which was O(n²)).
    """
    sections: list[dict[str, object]] = []
    section_map: dict[str, dict[str, object]] = {}

    for page in state.pages:
        section = section_map.get(page.section)
        if section is None:
            section = {"name": page.section, "items": []}
            section_map[page.section] = section
            sections.append(section)

        items = section["items"]
        assert isinstance(items, list)
        items.append(page)

    return sections


def localize_nav(
    skeleton: list[dict[str, object]], current_url: str
) -> list[dict[str, object]]:
    """Resolve the shared nav skeleton into relative URLs for `current_url`."""
    localized: list[dict[str, object]] = []
    for section in skeleton:
        pages = section["items"]
        assert isinstance(pages, list)
        localized.append(
            {
                "name": section["name"],
                "items": [
                    {
                        "title": page.title,
                        "url": relative_link(current_url, page.output_url),
                        "is_current": page.output_url == current_url,
                        "is_index": page.is_section_index,
                    }
                    for page in pages
                ],
            }
        )
    return localized


def render_pages(
    config: WebsiteConfig,
    state: BuildState,
    env: Environment,
    logger: logging.Logger,
) -> None:
    """Render each markdown page into `<output>/<output_url>`."""
    template = env.get_template("page.html.j2")
    total = len(state.pages)

    nav_skeleton = build_nav_skeleton(state)

    for idx, page in enumerate(state.pages):
        nav = localize_nav(nav_skeleton, page.output_url)
        if page.content is not None:
            md_content = page.content
        else:
            try:
                md_content = page.source.read_text(encoding="utf-8")
            except UnicodeDecodeError as e:
                raise RuntimeError(f"Failed to read {page.source}: {e}") from e

        # Parse the rendered markdown once, then run heading-id normalisation,
        # TOC extraction, and link rewriting against the same tree before a
        # single serialization — avoids reparsing the HTML three times per page.
        soup = render_markdown_to_soup(md_content)
        toc = extract_toc_from_soup(soup)
        rewrite_links_in_soup(soup, page, state, config, logger)
        state.page_anchors[page.output_url] = {
            str(el["id"]) for el in soup.find_all(id=True)
        }
        html_content = str(soup)

        prev_page = state.pages[idx - 1] if idx > 0 else None
        next_page = state.pages[idx + 1] if idx < total - 1 else None

        course = load_json(config.root_path / "course.json") if (config.root_path / "course.json").exists() else {"modules": []}
        lesson = next((l for m in course["modules"] for l in m["lessons"] if l["path"] == page.rel_source), None)
        quiz = load_json(config.root_path / lesson["quiz_path"]) if lesson and lesson.get("quiz_path") else None
        module = next((m for m in course["modules"] if lesson and lesson in m["lessons"]), None)
        if lesson:
            ordered_lessons = [l for m in course["modules"] for l in m["lessons"]]
            lesson_index = next(i for i, l in enumerate(ordered_lessons) if l["id"] == lesson["id"])
            by_source = {p.rel_source: p for p in state.pages}
            prev_page = by_source[ordered_lessons[lesson_index - 1]["path"]] if lesson_index else None
            next_page = by_source[ordered_lessons[lesson_index + 1]["path"]] if lesson_index + 1 < len(ordered_lessons) else None
        material_links = []
        if lesson and lesson.get("exercise_id"):
            folder = 'examples/' + lesson['exercise_id']
            for label, suffix, directory in [('Исходные файлы', 'starter', True), ('Подсказки', 'HINTS.md', False), ('Эталонное решение', 'solution', True), ('Скрипт проверки', 'test.py', False)]:
                target = config.root_path / folder / suffix
                if not target.exists():
                    raise RuntimeError('Нет материала упражнения: ' + str(target))
                material_links.append({'label': label, 'url': relative_link(page.output_url, material_url(folder + '/' + suffix, directory))})
        rendered = template.render(
            course=course, lesson=lesson, quiz=quiz, module=module, material_links=material_links,
            site_title=config.site_title,
            site_subtitle=config.site_subtitle,
            page_title=page.title,
            section=page.section,
            content=html_content,
            toc=toc,
            nav=nav,
            current_url=page.output_url,
            base_path=relative_link(page.output_url, "index.html").rsplit(
                "index.html", 1
            )[0],
            assets_prefix=relative_link(page.output_url, "assets/").rsplit(
                "assets/", 1
            )[0]
            + "assets/",
            prev_page=(
                {
                    "title": prev_page.title,
                    "url": relative_link(page.output_url, prev_page.output_url),
                }
                if prev_page
                else None
            ),
            next_page=(
                {
                    "title": next_page.title,
                    "url": relative_link(page.output_url, next_page.output_url),
                }
                if next_page
                else None
            ),
            github_source_url=f"{config.repo_url}/blob/{config.branch}/{page.rel_source}",
            repo_url=config.repo_url,
            language=config.language,
            ui=config.ui_strings,
        )

        out_file = config.output_path / page.output_url
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(rendered, encoding="utf-8")
        logger.debug(f"Wrote {out_file}")

    logger.info(f"Rendered {total} HTML page(s) into {config.output_path}")


# =============================================================================
# Landing page
# =============================================================================


def _resolve_landing_roadmap(
    data: dict[str, object], state: BuildState
) -> tuple[list[dict[str, object]], int, int, list[str]]:
    """Resolve roadmap module sources and lesson headings to site URLs.

    Returns (levels, module_count, lesson_count, problems). Every module
    `source` must map to a rendered page and every lesson `heading` must
    match an element id on that page — problems are collected, not raised,
    so a single error lists all drift at once.
    """
    problems: list[str] = []
    seen_module_ids: set[str] = set()
    seen_lesson_ids: set[str] = set()
    resolved_levels: list[dict[str, object]] = []
    module_count = 0
    lesson_count = 0

    levels = data.get("levels", [])
    if not isinstance(levels, list):
        raise RuntimeError("roadmap.json: 'levels' must be a list")

    for level in levels:
        resolved_modules: list[dict[str, object]] = []
        for module in level.get("modules", []):
            mod_id = str(module.get("id", ""))
            source = str(module.get("source", ""))
            module_count += 1
            if mod_id in seen_module_ids:
                problems.append(f"duplicate module id: '{mod_id}'")
            seen_module_ids.add(mod_id)

            url = state.source_to_url.get(source)
            if url is None:
                problems.append(
                    f"module '{mod_id}': source '{source}' was not rendered"
                )
            anchors = state.page_anchors.get(url, set()) if url else set()

            resolved_lessons: list[dict[str, object]] = []
            for lesson in module.get("lessons", []):
                lesson_id = str(lesson.get("id", ""))
                full_id = f"{mod_id}/{lesson_id}"
                lesson_count += 1
                if full_id in seen_lesson_ids:
                    problems.append(f"duplicate lesson id: '{full_id}'")
                seen_lesson_ids.add(full_id)

                heading = str(lesson.get("heading", ""))
                anchor = heading_to_anchor(heading)
                if url is not None and anchor not in anchors:
                    problems.append(
                        f"lesson '{full_id}': heading '{heading}' resolves to "
                        f"#{anchor}, which is missing from {source}"
                    )
                resolved_lessons.append(
                    {
                        "id": lesson_id,
                        "full_id": full_id,
                        "title": lesson.get("title", heading),
                        "href": (
                            relative_link("index.html", url, f"#{anchor}")
                            if url
                            else "#"
                        ),
                    }
                )
            resolved_modules.append(
                {
                    "id": mod_id,
                    "number": module.get("number", ""),
                    "title": module.get("title", mod_id),
                    "time": module.get("time", ""),
                    "tagline": module.get("tagline", ""),
                    "url": relative_link("index.html", url) if url else "#",
                    "lessons": resolved_lessons,
                    "lesson_count": len(resolved_lessons),
                }
            )
        resolved_levels.append(
            {
                "id": level.get("id", ""),
                "name": level.get("name", ""),
                "title": level.get("title", ""),
                "summary": level.get("summary", ""),
                "modules": resolved_modules,
            }
        )
    return resolved_levels, module_count, lesson_count, problems


def _resolve_course_roadmap(course_json_path, state, language="ru"):
    data = load_json(course_json_path)
    modules = []
    count = 0
    for mod in data["modules"]:
        items = []
        for lesson in mod["lessons"]:
            if lesson["path"] not in state.source_to_url:
                raise RuntimeError("Урок отсутствует в сборке: " + lesson["path"])
            items.append({**lesson, "full_id": lesson["id"], "href": state.source_to_url[lesson["path"]]})
        count += len(items)
        modules.append({**mod, "lessons": items, "number": str(mod["order"]),
                        "tagline": mod.get("summary", ""), "url": state.source_to_url.get(mod.get("path", ""), items[0]["href"])})
    return [{"id": "course", "title": "Карта курса", "modules": modules}], len(modules), count


def render_landing(
    config: WebsiteConfig,
    state: BuildState,
    env: Environment,
    logger: logging.Logger,
) -> None:
    """Render the landing page as `index.html`."""
    template_dir = Path(__file__).parent / "website_templates"
    course_json_path = config.root_path / "course.json"

    if course_json_path.exists():
        levels, module_count, lesson_count = _resolve_course_roadmap(course_json_path, state, config.language)
    else:
        raise ValueError('Для карты курса нужен course.json')

    version = None
    readme_text = read_source(config.root_path / "README.md")
    if readme_text:
        match = re.search(r"badge/version-([\d.]+)", readme_text)
        if match:
            version = match.group(1)

    template = env.get_template("landing.html.j2")
    rendered = template.render(
        course=load_json(course_json_path) if course_json_path.exists() else {"modules": []},
        site_title=config.site_title,
        site_subtitle=config.site_subtitle,
        levels=levels,
        module_count=module_count,
        lesson_count=lesson_count,
        version=version,
        guide_url=state.source_to_url.get("README.md", "guide.html"),
        repo_url=config.repo_url,
        branch=config.branch,
        language=config.language,
        ui=config.ui_strings,
    )

    out_file = config.output_path / "index.html"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(rendered, encoding="utf-8")

    assets_dir = config.output_path / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for name in ("landing.css", "landing.js"):
        src = template_dir / name
        if src.exists():
            shutil.copy2(src, assets_dir / name)
        else:
            logger.warning(f"Landing asset missing, skipped: {src}")

    logger.info(f"Rendered landing page → {out_file}")


# =============================================================================
# Build orchestration
# =============================================================================



BUILD_MARKER = '.codex-course-build'

def validate_output(root: Path, output: Path) -> Path:
    """Разрешает новый/пустой каталог или предыдущую собственную сборку."""
    root = root.resolve()
    raw = output.absolute()
    if raw.is_symlink() or any(p.is_symlink() for p in raw.parents):
        raise ValueError('Каталог вывода не должен проходить через символическую ссылку')
    output = raw.resolve()
    if root.is_relative_to(output):
        raise ValueError('Нельзя собирать в корень проекта или его предка')
    if output.is_relative_to(root):
        first = output.relative_to(root).parts[0]
        if first not in {'site', 'site_test', '.learning', 'dist'}:
            raise ValueError('Внутри проекта используйте site, dist или .learning')
    if output.exists():
        if not output.is_dir(): raise ValueError('Вывод не является каталогом')
        if any(output.iterdir()) and not (output / BUILD_MARKER).is_file():
            raise ValueError('Непустой чужой каталог: сборщик не будет его очищать')
        if (output / '.git').exists(): raise ValueError('Нельзя заменять Git-репозиторий')
    return output

def material_url(relative, is_dir=False):
    """Separate previews from raw files; no dependency on a GitHub branch."""
    from urllib.parse import quote
    rel = "" if relative == "." else str(relative).strip("/")
    return "materials/" + quote(rel, safe="/") + ("/index.html" if is_dir and rel else "index.html" if is_dir else ".html")


def copy_learning_sources(config):
    """Copy the allowlist verbatim and build escaped, local code viewers."""
    from urllib.parse import quote, unquote
    root, output = config.root_path.resolve(), config.output_path
    top_files = {'README.md', 'AGENTS.md', 'course.json', 'sources.json', 'LICENSE',
                 'NOTICE.md', 'SECURITY.md', 'CONTRIBUTING.md', 'validation.json', 'ACCEPTANCE_RU.md'}
    top_dirs = {'examples', 'reference', 'scripts', '.agents', 'openspec', 'third_party', 'resources'}
    files = []
    for path in source_files(root):
        rel = path.relative_to(root)
        if not (rel.as_posix() in top_files or rel.parts[0] in top_dirs
                or re.fullmatch(r'\d\d-[a-z0-9-]+', rel.parts[0])):
            continue
        if path.name in {'.env', 'auth.json', 'id_rsa', 'id_ed25519'} or path.suffix.lower() in {'.ttf', '.woff', '.woff2', '.otf'}:
            raise ValueError('Не допускается в учебной поставке: ' + str(rel))
        dest = output / 'source' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        files.append((rel, path))
    dirs = {Path('.')}
    for rel, _ in files:
        dirs.update(rel.parents)
    # A source name must never silently overwrite another preview/index.
    urls = [material_url(rel.as_posix()) for rel, _ in files] + [material_url(d.as_posix(), True) for d in dirs]
    if len({x.casefold() for x in urls}) != len(urls):
        raise ValueError('Конфликт имён локальных страниц материалов')

    def write(url, title, body, breadcrumbs):
        assets = relative_link(url, 'assets/site.css')
        back = relative_link(url, 'index.html')
        # No runtime JS is needed to read code, licenses or solutions.
        result = ('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
                  '<meta name="viewport" content="width=device-width, initial-scale=1">'
                  '<title>' + html.escape(title) + ' — Материалы курса</title>'
                  '<link rel="stylesheet" href="' + assets + '"></head><body>'
                  '<header><a class="brand" href="' + back + '">Курс по Codex CLI</a></header>'
                  '<main id="content" class="material-page"><nav aria-label="Путь к файлу">' + breadcrumbs + '</nav>'
                  '<h1>' + html.escape(title) + '</h1>' + body + '</main>'
                  '<footer>Локальные материалы курса. Чтение кода не запускает его.</footer></body></html>')
        dest = output / unquote(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(result, encoding='utf-8')

    for rel, path in files:
        url = material_url(rel.as_posix())
        raw = relative_link(url, 'source/' + quote(rel.as_posix(), safe='/'))
        parent = relative_link(url, material_url(rel.parent.as_posix(), True))
        body = '<p><a class="button" download href="' + raw + '">Скачать исходный файл</a></p>'
        try:
            text = path.read_text(encoding='utf-8')
            if path.name == 'HINTS.md' and rel.parts[0] == 'examples':
                soup = render_markdown_to_soup(text)
                # Hints are authored course documents; ordinary source files stay escaped.
                for heading in soup.find_all('h1'):
                    heading.name = 'h2'
                page = PageInfo(path, rel.as_posix(), url, rel.name, 'Подсказки')
                rewrite_links_in_soup(soup, page, BuildState(), config, logging.getLogger(__name__))
                body += '<article class="prose">' + str(soup) + '</article>'
            else:
                body += '<pre class="source-code"><code>' + html.escape(text) + '</code></pre>'
        except UnicodeError:
            body += '<p>Двоичный файл. Для просмотра сохраните его на устройство.</p>'
        write(url, rel.name, body, '<a href="' + parent + '">← ' + html.escape(rel.parent.as_posix()) + '</a>')
    for directory in sorted(dirs):
        url = material_url(directory.as_posix(), True)
        children = [(d.name, material_url(d.as_posix(), True), True) for d in dirs if d != directory and d.parent == directory]
        children += [(r.name, material_url(r.as_posix()), False) for r, _ in files if r.parent == directory]
        body = '<p>Это файлы из поставки, а не ссылки на GitHub. Для выполнения команд используйте каталог <code>source</code>.</p><ul class="material-list">'
        for name, target, is_dir in sorted(children, key=lambda x: (not x[2], x[0])):
            body += '<li><a href="' + relative_link(url, target) + '">' + html.escape(name) + (' /' if is_dir else '') + '</a></li>'
        body += '</ul>'
        crumbs = '<a href="' + relative_link(url, 'index.html') + '">Карта курса</a>' if directory == Path('.') else '<a href="' + relative_link(url, material_url(directory.parent.as_posix(), True)) + '">← Назад к каталогу</a>'
        write(url, 'Материалы курса' if directory == Path('.') else directory.as_posix(), body, crumbs)

def build_website(config, logger, *, skip_vendor=False):
    """Сначала полная сборка в staging. Старый результат меняется только после успеха.
    skip_vendor сохранён для совместимости вызовов; сети нет в обоих режимах.
    """
    root = config.root_path.resolve()
    if not root.is_dir(): raise ValueError('Корень проекта не найден')
    output = validate_output(root, config.output_path)
    if (root / 'course.json').exists():
        errors = check_course(root)
        if errors: raise ValueError('\n'.join(errors))
    before = tree_hash(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.codex-build-', dir=output.parent))
    try:
        staged = replace(config, root_path=root, output_path=stage)
        template_dir = Path(__file__).parent / 'website_templates'
        env = Environment(loader=FileSystemLoader(str(template_dir)),
                          autoescape=select_autoescape(['html', 'xml', 'j2']),
                          trim_blocks=True, lstrip_blocks=True)
        state = collect_pages(staged, logger)
        if not state.pages: raise RuntimeError('Нет Markdown-страниц')
        render_pages(staged, state, env, logger)
        if config.landing: render_landing(staged, state, env, logger)
        copy_assets(staged, state, logger)
        copy_learning_sources(staged)
        assets = stage / 'assets'; assets.mkdir(exist_ok=True)
        for name in ('site.css', 'site.js', 'progress.js', 'landing.css', 'landing.js'):
            shutil.copy2(template_dir / name, assets / name)
        index = [{"title": p.title, "url": p.output_url,
                  "text": (p.content or '')} for p in state.pages]
        payload = json.dumps(index, ensure_ascii=False).replace('<', '\\u003c')
        (assets / 'search-index.js').write_text('window.COURSE_SEARCH = ' + payload + ';', encoding='utf-8')
        from check_site import check as check_site
        link_errors, _ = check_site(stage)
        if link_errors: raise ValueError('Ошибки локальных ссылок:\n' + '\n'.join(link_errors[:30]))
        if tree_hash(root) != before: raise ValueError('Исходники изменились во время сборки')
        manifest = {'schema_version': 1, 'candidate_tree_sha256': before, 'files': {p.relative_to(stage).as_posix(): sha256(p) for p in sorted(stage.rglob('*')) if p.is_file()}}
        (stage / BUILD_MARKER).write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding='utf-8')
        backup = output.with_name(output.name + '.previous-build')
        if backup.exists(): raise ValueError('Сначала разберите предыдущую резервную сборку: ' + str(backup))
        had_output = output.exists()
        if had_output: output.rename(backup)
        try:
            stage.rename(output)
        except BaseException:
            if had_output: backup.rename(output)
            raise
        if had_output: shutil.rmtree(backup)
        logger.info('Автономный сайт собран: %s', output)
        return output
    finally:
        if stage.exists(): shutil.rmtree(stage)

def main():
    parser = argparse.ArgumentParser(description='Сборка автономного курса Codex CLI без сети')
    parser.add_argument('--root', '-r', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--output', '-o', type=Path)
    parser.add_argument('--lang', choices=['ru'], default='ru')
    parser.add_argument('--repo-url', default=REPO_URL)
    parser.add_argument('--branch', default=DEFAULT_BRANCH)
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    config = WebsiteConfig(root, args.output or root / 'site', repo_url=args.repo_url,
                           branch=args.branch, landing=True, language='ru')
    try:
        build_website(config, setup_logging(args.verbose))
        return 0
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print('Ошибка сборки: ' + str(exc), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
