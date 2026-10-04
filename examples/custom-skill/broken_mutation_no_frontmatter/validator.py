"""examples/custom-skill/broken_mutation_no_frontmatter/validator.py - Ошибочная мутация."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional


class SkillValidator:
    """Ошибочная мутация: не проверяет YAML frontmatter."""

    def validate_skill_directory(self, dir_path: str | Path) -> Dict[str, Any]:
        p = Path(dir_path)
        if not p.is_dir() or not (p / "SKILL.md").exists():
            return {"valid": False, "name": None, "description": None, "errors": ["SKILL.md отсутствует"]}

        # Ошибка: считает любой файл валидным без frontmatter
        return {
            "valid": True,
            "name": "auto-name",
            "description": "auto-desc",
            "errors": [],
        }
