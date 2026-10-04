"""examples/custom-skill/broken_mutation_leak_paths/validator.py - Ошибочная мутация."""

from __future__ import annotations
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class SkillValidator:
    """Ошибочная мутация: не проверяет абсолютные пути и утечки."""

    NAME_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

    def validate_skill_directory(self, dir_path: str | Path) -> Dict[str, Any]:
        p = Path(dir_path)
        if not p.is_dir() or not (p / "SKILL.md").exists():
            return {"valid": False, "name": None, "description": None, "errors": ["SKILL.md отсутствует"]}

        content = (p / "SKILL.md").read_text(encoding="utf-8")
        if not content.startswith("---"):
            return {"valid": False, "name": None, "description": None, "errors": ["Отсутствует frontmatter"]}

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {"valid": False, "name": None, "description": None, "errors": ["Не закрыт frontmatter"]}

        name = None
        description = None
        for line in parts[1].splitlines():
            line = line.strip()
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("description:"):
                description = line.split(":", 1)[1].strip()

        if not name or not self.NAME_REGEX.match(name) or not description:
            return {"valid": False, "name": None, "description": None, "errors": ["Некорректный frontmatter"]}

        # Ошибка: полностью пропускает проверку на абсолютные локальные пути!
        return {
            "valid": True,
            "name": name,
            "description": description,
            "errors": [],
        }
