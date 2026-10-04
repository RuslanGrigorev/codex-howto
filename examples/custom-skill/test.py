#!/usr/bin/env python3
"""test.py - Автономный тестовый набор для упражнения custom-skill.

Проверяет:
1. Наличие SKILL.md и корректность структуры.
2. Валидацию обязательных полей frontmatter (name, description).
3. Валидацию формата имени (kebab-case).
4. Блокировку абсолютных путей и потенциальных утечек.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.getcwd())

from validator import SkillValidator


class TestSkillValidator(unittest.TestCase):
    def setUp(self):
        self.validator = SkillValidator()
        self.test_dir = tempfile.mkdtemp(prefix="test_skill_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_skill(self, content: str) -> Path:
        skill_dir = Path(self.test_dir) / "test-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        return skill_dir

    def test_valid_skill(self):
        content = """---
name: code-review-helper
description: Помощник для автоматизированного ревью кода
---

# Code Review Helper

Инструкции для выполнения проверки кода.
"""
        skill_dir = self._create_skill(content)
        res = self.validator.validate_skill_directory(skill_dir)
        self.assertTrue(res["valid"], f"Ожидалась успешная валидация, получены ошибки: {res.get('errors')}")
        self.assertEqual(res["name"], "code-review-helper")
        self.assertEqual(res["description"], "Помощник для автоматизированного ревью кода")
        self.assertEqual(len(res["errors"]), 0)

    def test_missing_skill_md(self):
        empty_dir = Path(self.test_dir) / "empty-skill"
        empty_dir.mkdir(parents=True, exist_ok=True)
        res = self.validator.validate_skill_directory(empty_dir)
        self.assertFalse(res["valid"])
        self.assertTrue(any("SKILL.md" in e for e in res["errors"]))

    def test_missing_frontmatter(self):
        content = """# Просто заголовок без frontmatter

Какой-то текст без метаданных.
"""
        skill_dir = self._create_skill(content)
        res = self.validator.validate_skill_directory(skill_dir)
        self.assertFalse(res["valid"])
        self.assertTrue(any("frontmatter" in e.lower() for e in res["errors"]))

    def test_invalid_name_format(self):
        content = """---
name: Invalid Name With Spaces!
description: Некорректное имя навыка
---

# Test
"""
        skill_dir = self._create_skill(content)
        res = self.validator.validate_skill_directory(skill_dir)
        self.assertFalse(res["valid"])
        self.assertTrue(any("name" in e.lower() for e in res["errors"]))

    def test_prohibited_absolute_paths(self):
        # Строим путь динамически, чтобы сам тест не содержал жестких путей
        drive_path = "C:" + chr(92) + "Users" + chr(92) + "developer" + chr(92) + "project"
        content = f"""---
name: dangerous-skill
description: Навык с жестким путем
---

Используй путь {drive_path} для сохранения файлов.
"""
        skill_dir = self._create_skill(content)
        res = self.validator.validate_skill_directory(skill_dir)
        self.assertFalse(res["valid"], "Навык с абсолютным локальным путем должен быть отклонен")
        self.assertTrue(any("путь" in e.lower() or "path" in e.lower() for e in res["errors"]))


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestSkillValidator)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
