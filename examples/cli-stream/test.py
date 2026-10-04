#!/usr/bin/env python3
"""test.py - Автономный тестовый набор для упражнения cli-stream.

Проверяет:
1. Построчный парсинг потока JSONL.
2. Сборку итогового текста из delta-событий.
3. Распознавание событий ошибок (type=error) и установку флага success=False.
4. Определение кода завершения (type=done).
5. Обработку невалидных строк (malformed JSON).
"""

import os
import sys
import unittest

sys.path.insert(0, os.getcwd())

from stream_parser import CodexStreamParser


class TestCodexStreamParser(unittest.TestCase):
    def setUp(self):
        self.parser = CodexStreamParser()

    def test_successful_stream(self):
        stream = [
            '{"type": "item_started", "id": "1"}',
            '{"type": "item_delta", "id": "1", "delta": "Выполняю проверку..."}',
            '{"type": "item_delta", "id": "1", "delta": " Все тесты пройдены!"}',
            '{"type": "item_completed", "id": "1", "status": "ok"}',
            '{"type": "done", "exit_code": 0}',
        ]
        result = self.parser.parse_stream(stream)
        self.assertTrue(result["success"])
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["output_text"], "Выполняю проверку... Все тесты пройдены!")
        self.assertEqual(result["events_count"], 5)
        self.assertEqual(len(result["errors"]), 0)

    def test_error_event_sets_failure(self):
        stream = [
            '{"type": "item_started", "id": "1"}',
            '{"type": "error", "message": "Отказ в доступе к системному файлу", "code": 13}',
            '{"type": "done", "exit_code": 1}',
        ]
        result = self.parser.parse_stream(stream)
        self.assertFalse(result["success"], "Событие ошибки обязано делать success=False")
        self.assertEqual(result["exit_code"], 1)
        self.assertTrue(any("Отказ в доступе" in err for err in result["errors"]))

    def test_malformed_json_handling(self):
        stream = [
            '{"type": "item_started", "id": "1"}',
            'ЭТО НЕ JSON СТРОКА',
            '{"type": "done", "exit_code": 0}',
        ]
        result = self.parser.parse_stream(stream)
        self.assertFalse(result["success"], "Поврежденные строки в потоке должны приводить к ошибке")
        self.assertTrue(len(result["errors"]) > 0)
        self.assertTrue(any("невалидный" in err.lower() or "json" in err.lower() for err in result["errors"]))

    def test_reject_single_json_blob_not_jsonl(self):
        # Если передать поток как единый склеенный блок JSON без разделения на строки
        stream = [
            '{"type": "item_started"} {"type": "done"}'
        ]
        result = self.parser.parse_stream(stream)
        self.assertFalse(result["success"])


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestCodexStreamParser)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
