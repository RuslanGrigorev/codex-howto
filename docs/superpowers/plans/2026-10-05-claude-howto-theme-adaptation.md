# Claude How-To Theme & Interactive Stations Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore and adapt the complete "Terminal Luxe" visual design and interactive metro-map architecture from `luongnv89/claude-howto` for the Codex CLI course (10 modules, 62 lessons), ensuring 100% offline self-contained operation and full test compliance.

**Architecture:** The landing page is powered by Jinja2 templates (`landing.html.j2`, `base.html.j2`), custom vanilla CSS (`landing.css`, `site.css`), and lightweight offline JS (`landing.js`, `progress.js`). Modules are organized into 4 logical levels with interactive station cards, progress rings, collapsible lesson accordions, and interactive checkmarks, while lesson pages adopt matching dark/emerald aesthetics.

**Tech Stack:** Jinja2 (Python 3.13), HTML5, Vanilla CSS3 (Custom properties, grid, flexbox, glassmorphism), Vanilla JavaScript (ES6, localStorage, Web APIs), Playwright / Chromium for browser testing.

## Global Constraints

- Explanations and UI in Russian; CLI commands, API names, flags, and keys in original English.
- No external CDN or web requests at runtime; 100% self-contained offline delivery.
- Do not overwrite or modify user's global configurations (`~/.codex`, Minimax, or Codex Desktop).
- All 86 pages and 62 lessons must remain fully intact and validated.
- All verification commands (`scripts/browser_check.py`, `scripts/check_site.py`, `scripts/check_project.py catalog`, `scripts/check_coverage.py`) must PASS with 0 errors.

---

### Task 1: Level Resolution and Roadmap Data in Website Builder

**Files:**
- Modify: `scripts/build_website.py:970-985`
- Test: `scripts/check_coverage.py` and `scripts/check_project.py catalog`

**Interfaces:**
- Consumes: `course.json` modules (10 modules, 62 lessons).
- Produces: `levels` list with 4 logical levels:
  1. `start-workflow`: "Уровень 1: Начало работы" (Модули 1–2).
  2. `safety-instructions`: "Уровень 2: Безопасность и управление" (Модули 3–5).
  3. `skills-mcp`: "Уровень 3: Расширяемость и MCP" (Модули 6–7).
  4. `automation-capstone`: "Уровень 4: Автоматизация и приёмка" (Модули 8–10).

- [ ] **Step 1: Write test or verification check for 4-level roadmap grouping**

Verify that `_resolve_course_roadmap` groups the 10 modules into 4 levels with correct lesson counts.
Test script:
```python
# test_roadmap_levels.py
from build_website import _resolve_course_roadmap, BuildState, collect_pages, WebsiteConfig
from pathlib import Path
import json

root = Path('.')
state = BuildState()
state.source_to_url = {l['path']: l['path'].replace('.md', '.html') for m in json.loads(Path('course.json').read_text(encoding='utf-8'))['modules'] for l in m['lessons']}
levels, mod_count, lesson_count = _resolve_course_roadmap(Path('course.json'), state)
assert len(levels) == 4, f"Expected 4 levels, got {len(levels)}"
assert mod_count == 10
assert lesson_count == 62
print("PASS: 4 levels resolved successfully")
```

- [ ] **Step 2: Update `_resolve_course_roadmap` in `scripts/build_website.py`**

Group the 10 modules into 4 logical levels with Russian titles and summaries matching the curriculum:
```python
def _resolve_course_roadmap(course_json_path, state, language="ru"):
    data = load_json(course_json_path)
    level_defs = [
        {"id": "level-1", "name": "Уровень 1", "title": "Основы и первый запуск", "summary": "Среда, установка, базовые команды и ограниченные исправления.", "orders": {1, 2}},
        {"id": "level-2", "name": "Уровень 2", "title": "Безопасность и управление", "summary": "Песочница, правила AGENTS.md, контекст и сессии.", "orders": {3, 4, 5}},
        {"id": "level-3", "name": "Уровень 3", "title": "Навыки и интеграция MCP", "summary": "Создание локальных навыков, подключение и диагностика серверов инструментов.", "orders": {6, 7}},
        {"id": "level-4", "name": "Уровень 4", "title": "Автоматизация и приёмка", "summary": "Пакетное выполнение exec, события JSONL, hooks, субагенты и итоговый проект.", "orders": {8, 9, 10}},
    ]
    all_modules = []
    total_lessons = 0
    for mod in data["modules"]:
        items = []
        for lesson in mod["lessons"]:
            if lesson["path"] not in state.source_to_url:
                raise RuntimeError("Урок отсутствует в сборке: " + lesson["path"])
            items.append({**lesson, "full_id": lesson["id"], "href": state.source_to_url[lesson["path"]]})
        total_lessons += len(items)
        time_est = f"{len(items) * 15} мин"
        all_modules.append({
            **mod, "lessons": items, "lesson_count": len(items), "time": time_est,
            "number": str(mod["order"]).zfill(2), "tagline": mod.get("summary", ""),
            "url": state.source_to_url.get(mod.get("path", ""), items[0]["href"])
        })
    levels = []
    for ldef in level_defs:
        mods = [m for m in all_modules if m["order"] in ldef["orders"]]
        if mods:
            levels.append({**ldef, "modules": mods})
    return levels, len(all_modules), total_lessons
```

- [ ] **Step 3: Run verification test to confirm 4 levels**

Run: `python -c "from scripts.build_website import _resolve_course_roadmap, BuildState; ..."`
Expected: PASS

- [ ] **Step 4: Commit changes**

```bash
git add scripts/build_website.py
git commit -m "feat(builder): structure course roadmap into 4 logical levels for stations view"
```

---

### Task 2: Restore and Adapt Terminal Luxe Stylesheet (`landing.css`)

**Files:**
- Create/Overwrite: `scripts/website_templates/landing.css`
- Copy to: `site/assets/landing.css`

**Interfaces:**
- Consumes: CSS tokens for Terminal Luxe (`--bg`, `--panel`, `--green`, `--green-glow`, `--border`, `--text`).
- Produces: Visual styles for:
  - Hero with circular progress ring SVG and Terminal Luxe preview terminal.
  - Stations roadmaps (`.station-track`, `.station-card`, `.node`, `.pill`, `.station-bar`, `.lessons`).
  - Interactive checkboxes with SVG checkmarks and dashes.
  - 3-step Get Started cards (`.steps`, `.step`, `.step-num`, `.code`, `.copy`).
  - Floating sticky nav with glassmorphism and theme toggle.

- [ ] **Step 1: Extract and adapt Terminal Luxe `landing.css` from commit `b9bc14e`**

Extract `b9bc14e:scripts/website_templates/landing.css` and ensure all custom variables support:
- Primary dark theme `#000000` with emerald green `#22c55e`.
- Light theme `#fbfaf7` with emerald `#15803d`.
- Station track connecting line, glowing node indicators, station bars.
- Custom scrollbars.

- [ ] **Step 2: Save to `scripts/website_templates/landing.css` and `site/assets/landing.css`**

Write the complete stylesheet with all styles for stations, terminal, hero, and steps.

- [ ] **Step 3: Verify CSS syntax and absence of external resource URLs**

Verify that `landing.css` contains zero `http://` or `https://` references or `@import` to external URLs.

- [ ] **Step 4: Commit changes**

```bash
git add scripts/website_templates/landing.css site/assets/landing.css
git commit -m "feat(style): restore and adapt Terminal Luxe landing.css with emerald accents"
```

---

### Task 3: Restore and Adapt Landing Page Template (`landing.html.j2` and `base.html.j2`)

**Files:**
- Modify: `scripts/website_templates/landing.html.j2`
- Modify: `scripts/website_templates/base.html.j2`

**Interfaces:**
- Consumes: `levels`, `module_count`, `lesson_count`, `site_title`, `guide_url`, `repo_url`, `version`.
- Produces:
  - Interactive Sticky Header with brand `Codex CLI`, navigation anchors, and `#theme-toggle`.
  - Hero with `<em>Codex CLI</em>`, circular progress ring, and interactive 3-tab terminal.
  - RoadMap section with levels and collapsible stations.
  - Quick Start section with 3 steps (`git clone`, `python scripts/verify.py`, `$learn`).
  - Footer with project metadata and "Наверх ↑" link.

- [ ] **Step 1: Update `scripts/website_templates/landing.html.j2`**

Write the complete template structure containing:
1. Hero grid with circular progress ring and terminal simulation (tab 1: Quick start `$learn`, tab 2: `/plan` & `/goal`, tab 3: `codex exec --json`).
2. Stations roadmap with 4 levels, station cards, progress bars, toggle buttons, and lesson checkboxes.
3. Steps section for Quick Start.
4. Navigation and footer matching `claude-howto`.

- [ ] **Step 2: Ensure all required test IDs and elements are present**

Ensure:
- `#theme-toggle` exists.
- `#course-search` and `#search-results` exist (or search input in toolbar/nav).
- `#roadmap` exists.
- `lang="ru"` on `html`.

- [ ] **Step 3: Commit changes**

```bash
git add scripts/website_templates/landing.html.j2 scripts/website_templates/base.html.j2
git commit -m "feat(templates): adapt landing.html.j2 with interactive stations, terminal hero and get started section"
```

---

### Task 4: Interactive Station Logic and Progress Ring (`landing.js` and `progress.js`)

**Files:**
- Create/Overwrite: `scripts/website_templates/landing.js`
- Copy to: `site/assets/landing.js`
- Test: `site/assets/site.js` and `scripts/website_templates/site.js`

**Interfaces:**
- Consumes: `CodexProgress` state from `progress.js`.
- Produces:
  - Terminal tab switcher logic (`data-tab`).
  - Module accordion toggle (`aria-expanded`, `.open`).
  - Lesson checkbox click listener: toggles read status, updates module progress bar (`0/8`), updates station pill (`Не начато` / `В процессе` / `Пройдено`), updates Hero circular progress ring (`N%` and `N/62`).
  - Command copy buttons with tooltip feedback ("Скопировано!").
  - Theme toggler supporting `data-theme="dark"` and `data-theme="light"`.

- [ ] **Step 1: Update `landing.js` with full interactive station logic**

Ensure:
- Clicks on `.check` toggle lesson read state via `CodexProgress.toggleRead()`.
- Circular progress ring SVG `strokeDashoffset` is smoothly updated based on completed / total lessons.
- Terminal tabs switch active tab and visible code snippet.
- Station accordion buttons toggle `.open` on `.lessons` list.
- Theme toggle synchronizes with `document.documentElement.dataset.theme` and `localStorage.setItem('course-theme')`.

- [ ] **Step 2: Sync to `site/assets/landing.js`**

Copy updated script to `site/assets/landing.js`.

- [ ] **Step 3: Commit changes**

```bash
git add scripts/website_templates/landing.js site/assets/landing.js
git commit -m "feat(interactive): implement landing.js with station checkboxes, progress ring and terminal tabs"
```

---

### Task 5: Adapt Lesson Page Styles (`site.css` and `page.html.j2`)

**Files:**
- Modify: `scripts/website_templates/site.css`
- Copy to: `site/assets/site.css`
- Modify: `scripts/website_templates/page.html.j2`

**Interfaces:**
- Consumes: Terminal Luxe variables (`--bg: #000`, `--panel: rgba(255,255,255,0.03)`, `--green: #22c55e`).
- Produces:
  - Matching dark theme for lesson reading pages.
  - Sticky sidebar with emerald active indicator.
  - Callout alert boxes, quiz fieldsets, and copy buttons in emerald styling.

- [ ] **Step 1: Align `site.css` color variables with Terminal Luxe**

Ensure:
- Primary dark theme `--bg: #000000`, `--panel: rgba(255, 255, 255, 0.03)`, `--accent: #22c55e`, `--border: rgba(255, 255, 255, 0.09)`.
- Active sidebar lesson item highlighted with emerald accent.
- Custom thin scrollbars in matching emerald tint.

- [ ] **Step 2: Sync `site/assets/site.css`**

- [ ] **Step 3: Commit changes**

```bash
git add scripts/website_templates/site.css site/assets/site.css scripts/website_templates/page.html.j2
git commit -m "feat(style): align lesson pages and sidebar with Terminal Luxe emerald palette"
```

---

### Task 6: Full Site Rebuild and Automated Verification

**Files:**
- Modify: `site/` (all 86 HTML pages and assets)

- [ ] **Step 1: Rebuild the static site using `build_website.py`**

Run: `python scripts/build_website.py --output site`
Expected: 86 HTML pages generated with all 62 lessons, 4 levels, 10 stations.

- [ ] **Step 2: Run link and offline resource validation**

Run: `python scripts/check_site.py --site site`
Expected: PASS (0 errors).

- [ ] **Step 3: Run comprehensive browser check**

Run: `python scripts/browser_check.py --site site`
Expected: PASS (461 pages opened, search works, quiz works, theme toggle works, responsive checks pass on 390px, 768px, 1440px).

- [ ] **Step 4: Run course catalog and coverage checks**

Run: `python scripts/check_project.py catalog`
Run: `python scripts/check_coverage.py`
Expected: All PASS.

- [ ] **Step 5: Visual verification in Playwright**

Navigate to `http://localhost:8080/index.html`:
- Verify Hero section with circular progress ring and Terminal tabs.
- Verify 4 levels and 10 stations with progress bars and collapsible lesson lists.
- Click an interactive lesson checkbox and verify progress updates.
- Capture screenshots for desktop and mobile view.

- [ ] **Step 6: Commit all generated site updates**

```bash
git add site/
git commit -m "feat(site): rebuild site with Terminal Luxe claude-howto visual design and interactive stations"
```
