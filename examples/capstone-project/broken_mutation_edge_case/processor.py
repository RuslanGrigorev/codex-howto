"""examples/capstone-project/broken_mutation_edge_case/processor.py - Ошибочная мутация."""

from __future__ import annotations
from typing import Any, Dict, List


class CourseReportProcessor:
    """Ошибочная мутация: не обрабатывает пустой список (вызывает ZeroDivisionError)."""

    REQUIRED_FIELDS = {"student_id", "lesson_id", "score", "status"}

    def process_reports(self, raw_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Ошибка: нет проверки if not raw_reports!
        total = len(raw_reports)
        passed = 0
        total_score = 0.0

        for r in raw_reports:
            if self.REQUIRED_FIELDS - set(r.keys()):
                raise ValueError("missing field")
            s = float(r["score"])
            if s < 0 or s > 100:
                raise ValueError("out of bounds")
            total_score += s
            if r["status"] == "passed":
                passed += 1

        # Вызовет ZeroDivisionError при total == 0!
        return {
            "total_reports": total,
            "passed_count": passed,
            "pass_rate": round(passed / total, 2),
            "average_score": round(total_score / total, 2),
            "top_lessons": [],
        }
