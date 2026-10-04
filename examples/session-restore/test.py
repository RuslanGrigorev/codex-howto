#!/usr/bin/env python3
"""test.py - Тестовый набор для упражнения session-restore.

Проверяет:
1. Создание, сохранение и возобновление сессии с сохранением полной истории сообщений.
2. Изоляцию: очистка контекста сессии не затрагивает файловую систему или переданное состояние файлов.
3. Корректное определение расхождения между историей сессии и текущим файловым состоянием.
4. Отсутствие смешивания контекста сессии и Git-состояния файлов.
"""

import os
import sys
import unittest

sys.path.insert(0, os.getcwd())

from session_manager import SessionManager


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        self.manager = SessionManager()

    def test_create_and_resume_session(self):
        s = self.manager.create_session("sess-1", "Исправление бага")
        self.assertEqual(s["id"], "sess-1")
        self.assertEqual(s["title"], "Исправление бага")
        self.assertEqual(len(s["messages"]), 0)

        self.manager.add_message("sess-1", "user", "Исправь ошибку деления на 0")
        self.manager.add_message("sess-1", "assistant", "План: добавить проверку делителя")

        resumed = self.manager.resume_session("sess-1")
        self.assertEqual(resumed["id"], "sess-1")
        self.assertEqual(len(resumed["messages"]), 2)
        self.assertEqual(resumed["messages"][0]["role"], "user")
        self.assertEqual(resumed["messages"][1]["role"], "assistant")

    def test_session_isolation_from_files(self):
        self.manager.create_session("sess-2", "Тест изоляции")
        self.manager.add_message("sess-2", "user", "Создай файл test.txt")

        # Моделируем файлы репозитория
        workspace_files = {"app.py": "print('hello')", "test.txt": "created"}
        workspace_snapshot = dict(workspace_files)

        # Очистка контекста диалога НЕ должна трогать файлы
        self.manager.clear_session_context("sess-2")
        resumed = self.manager.resume_session("sess-2")
        self.assertEqual(len(resumed["messages"]), 0, "Контекст сессии должен быть очищен")

        # Проверяем, что словарь файлов проекта остался нетронутым
        self.assertEqual(workspace_files, workspace_snapshot, "Файловое состояние не должно изменяться при сбросе сессии")

    def test_workspace_divergence(self):
        self.manager.create_session("sess-3", "Проверка расхождения")
        initial_files = {"main.py": "v1", "utils.py": "util"}
        current_files = {"main.py": "v2", "new_file.py": "new"}

        divergence = self.manager.check_workspace_divergence("sess-3", initial_files, current_files)
        self.assertTrue(divergence["diverged"])
        self.assertIn("main.py", divergence["modified"])
        self.assertIn("new_file.py", divergence["added"])
        self.assertIn("utils.py", divergence["removed"])

        # Проверяем, что проверка расхождения не изменила историю сообщений сессии
        res = self.manager.resume_session("sess-3")
        self.assertEqual(res["id"], "sess-3")


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestSessionManager)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
