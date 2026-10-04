"""examples/custom-skill/starter/validator.py - Заготовка для упражнения."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional


class SkillValidator:
    """Валидатор структуры и метаданных пользовательских навыков Codex CLI."""

    def validate_skill_directory(self, dir_path: str | Path) -> Dict[str, Any]:
        # TODO: Реализовать проверку наличия SKILL.md, парсинг frontmatter (name, description)
        # и защиту от утечки локальных абсолютных путей
        raise NotImplementedError("validate_skill_directory не реализован")
