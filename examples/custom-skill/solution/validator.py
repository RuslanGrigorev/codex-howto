"""examples/custom-skill/solution/validator.py - Эталонное решение."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class SkillValidator:
    """Валидатор структуры и метаданных пользовательских навыков Codex CLI."""

    NAME_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
    PROHIBITED_PATH_PATTERNS = [
        re.compile(r"[A-Za-z]:\\"),       # Windows абсолютный путь c:\
        re.compile(r"/Users/"),           # macOS домашний каталог
        re.compile(r"/home/"),            # Linux домашний каталог
    ]

    def validate_skill_directory(self, dir_path: str | Path) -> Dict[str, Any]:
        p = Path(dir_path)
        errors: List[str] = []

        if not p.is_dir():
            return {
                "valid": False,
                "name": None,
                "description": None,
                "errors": [f"Каталог {dir_path} не существует"],
            }

        skill_file = p / "SKILL.md"
        if not skill_file.exists():
            return {
                "valid": False,
                "name": None,
                "description": None,
                "errors": ["Файл SKILL.md отсутствует в корне навыка"],
            }

        try:
            content = skill_file.read_text(encoding="utf-8")
        except Exception as e:
            return {
                "valid": False,
                "name": None,
                "description": None,
                "errors": [f"Ошибка чтения SKILL.md: {e}"],
            }

        # 1. Проверка YAML frontmatter
        if not content.startswith("---"):
            errors.append("Файл SKILL.md должен начинаться с YAML frontmatter (---)")
            return {"valid": False, "name": None, "description": None, "errors": errors}

        parts = content.split("---", 2)
        if len(parts) < 3:
            errors.append("Не закрыт блок YAML frontmatter (---)")
            return {"valid": False, "name": None, "description": None, "errors": errors}

        frontmatter_text = parts[1]
        name: Optional[str] = None
        description: Optional[str] = None

        for line in frontmatter_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip().strip("\"'")
                if k == "name":
                    name = v
                elif k == "description":
                    description = v

        if not name:
            errors.append("Отсутствует обязательное поле frontmatter: name")
        elif not self.NAME_REGEX.match(name):
            errors.append(f"Недопустимое имя навыка '{name}': используйте kebab-case (только строчные латинские буквы, цифры и дефисы)")

        if not description:
            errors.append("Отсутствует обязательное поле frontmatter: description")

        # 2. Проверка на абсолютные пути и утечки
        for pattern in self.PROHIBITED_PATH_PATTERNS:
            if pattern.search(content):
                errors.append("Обнаружен запрещенный абсолютный путь в тексте навыка")
                break

        return {
            "valid": len(errors) == 0,
            "name": name if len(errors) == 0 else None,
            "description": description if len(errors) == 0 else None,
            "errors": errors,
        }
