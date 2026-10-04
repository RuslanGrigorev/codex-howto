"""examples/capstone-project/solution/processor.py - Эталонное решение итоговой практики."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


class CourseReportProcessor:
    """Обработчик и аналитический агрегатор учебных отчетов курса."""

    REQUIRED_FIELDS = {"student_id", "lesson_id", "score", "status"}
    VALID_STATUSES = {"passed", "failed"}

    def process_reports(self, raw_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(raw_reports, list):
            raise ValueError("raw_reports должен быть списком")

        if not raw_reports:
            return {
                "total_reports": 0,
                "passed_count": 0,
                "pass_rate": 0.0,
                "average_score": 0.0,
                "top_lessons": [],
            }

        total_reports = len(raw_reports)
        passed_count = 0
        total_score = 0.0
        lesson_pass_counter: Counter[str] = Counter()

        for report in raw_reports:
            if not isinstance(report, dict):
                raise ValueError("Каждый отчет должен быть словарем")

            # Проверка обязательных полей
            missing = self.REQUIRED_FIELDS - set(report.keys())
            if missing:
                raise ValueError(f"В отчете отсутствуют обязательные поля: {missing}")

            score = float(report["score"])
            if score < 0.0 or score > 100.0:
                raise ValueError(f"Балл {score} выходит за пределы допустимого диапазона 0..100")

            status = report["status"]
            if status not in self.VALID_STATUSES:
                raise ValueError(f"Недопустимый статус '{status}'")

            total_score += score
            if status == "passed":
                passed_count += 1
                lesson_pass_counter[report["lesson_id"]] += 1

        pass_rate = round(passed_count / total_reports, 2)
        average_score = round(total_score / total_reports, 2)

        # Сортировка уроков: сначала по убыванию успешных сдач, затем по алфавиту ID
        sorted_lessons = sorted(
            lesson_pass_counter.keys(),
            key=lambda lid: (-lesson_pass_counter[lid], lid),
        )

        return {
            "total_reports": total_reports,
            "passed_count": passed_count,
            "pass_rate": pass_rate,
            "average_score": average_score,
            "top_lessons": sorted_lessons,
        }
