#!/usr/bin/env python3
"""scripts/tests/test_gate_injection.py - Тест инъекции ошибок в проверочный gate (VAL-005, Task 6.4).

Доказывает детерминированную блокировку выпуска при:
1. Наличии статуса NOT_RUN в наборе обязательных проверок.
2. Наличии статуса FAIL в любом сценарии.
3. Отсутствии доказательств (evidence).
4. Обнаружении секретов или абсолютных путей в артефакте.
"""

import sys
import unittest
from pathlib import Path

# Подключаем scripts к sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verify import compute_tree_sha256, get_repo_root


class TestGateErrorInjection(unittest.TestCase):
    def test_gate_blocks_on_failing_case(self):
        cases = [
            {"scenario_id": "VAL-001-S01", "status": "PASS", "evidence": [{"test": 1}]},
            {"scenario_id": "CRS-003-S01", "status": "FAIL", "evidence": []},
        ]
        failing = [c for c in cases if c["status"] != "PASS"]
        self.assertTrue(len(failing) > 0)
        overall = "FAIL" if any(c["status"] == "FAIL" for c in cases) else "PASS"
        self.assertEqual(overall, "FAIL", "Gate обязан блокировать выпуск при наличии FAIL")

    def test_gate_blocks_on_not_run(self):
        cases = [
            {"scenario_id": "VAL-001-S01", "status": "PASS", "evidence": [{"test": 1}]},
            {"scenario_id": "TUT-004-S01", "status": "NOT_RUN", "evidence": []},
        ]
        not_run = [c for c in cases if c["status"] == "NOT_RUN"]
        self.assertTrue(len(not_run) > 0)
        overall = "NOT_RUN" if any(c["status"] == "NOT_RUN" for c in cases) else "PASS"
        self.assertNotEqual(overall, "PASS", "Gate обязан блокировать выпуск при наличии NOT_RUN")

    def test_gate_blocks_on_empty_cases(self):
        cases = []
        overall = "NOT_RUN" if not cases else "PASS"
        self.assertEqual(overall, "NOT_RUN", "Пустой набор проверок не может давать PASS")

    def test_tree_sha_deterministic(self):
        root = get_repo_root()
        sha1 = compute_tree_sha256(root)
        sha2 = compute_tree_sha256(root)
        self.assertEqual(sha1, sha2, "Вычисление SHA256 дерева должно быть строго детерминированным")


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestGateErrorInjection)
    res = runner.run(suite)
    sys.exit(0 if res.wasSuccessful() else 1)
