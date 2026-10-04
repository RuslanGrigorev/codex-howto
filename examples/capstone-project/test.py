#!/usr/bin/env python3
"""test.py - Автономный тестовый набор для упражнения capstone-project.

Проверяет:
1. Корректную агрегацию статистики отчетов.
2. Обработку пустого списка (без ZeroDivisionError).
3. Валидацию схемы данных и диапазонов (score от 0.0 до 100.0, обязательные поля).
4. Детерминированное ранжирование уроков по количеству успешных сдач.
"""

import os
import sys
import unittest

sys.path.insert(0, os.getcwd())

from processor import CourseReportProcessor


class TestCourseReportProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = CourseReportProcessor()

    def test_process_normal_reports(self):
        reports = [
            {"student_id": "s1", "lesson_id": "start.overview", "score": 90.0, "status": "passed"},
            {"student_id": "s2", "lesson_id": "start.overview", "score": 85.0, "status": "passed"},
            {"student_id": "s1", "lesson_id": "workflow.small-fix", "score": 70.0, "status": "failed"},
            {"student_id": "s2", "lesson_id": "workflow.small-fix", "score": 95.0, "status": "passed"},
        ]
        res = self.processor.process_reports(reports)
        self.assertEqual(res["total_reports"], 4)
        self.assertEqual(res["passed_count"], 3)
        self.assertEqual(res["pass_rate"], 0.75)
        self.assertEqual(res["average_score"], 85.0)
        self.assertEqual(res["top_lessons"], ["start.overview", "workflow.small-fix"])

    def test_process_empty_reports(self):
        res = self.processor.process_reports([])
        self.assertEqual(res["total_reports"], 0)
        self.assertEqual(res["passed_count"], 0)
        self.assertEqual(res["pass_rate"], 0.0)
        self.assertEqual(res["average_score"], 0.0)
        self.assertEqual(res["top_lessons"], [])

    def test_invalid_score_range_raises(self):
        bad_reports_high = [{"student_id": "s1", "lesson_id": "m1", "score": 105.0, "status": "passed"}]
        with self.assertRaises(ValueError):
            self.processor.process_reports(bad_reports_high)

        bad_reports_low = [{"student_id": "s1", "lesson_id": "m1", "score": -5.0, "status": "failed"}]
        with self.assertRaises(ValueError):
            self.processor.process_reports(bad_reports_low)

    def test_missing_fields_raises(self):
        bad_report = [{"student_id": "s1", "score": 90.0}]  # missing lesson_id and status
        with self.assertRaises(ValueError):
            self.processor.process_reports(bad_report)


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestCourseReportProcessor)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
