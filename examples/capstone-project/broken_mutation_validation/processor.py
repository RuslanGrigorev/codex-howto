"""examples/capstone-project/broken_mutation_validation/processor.py - Ошибочная мутация."""

from __future__ import annotations
from typing import Any, Dict, List


class CourseReportProcessor:
    """Ошибочная мутация: не проверяет диапазон оценок и обязательные поля."""

    def process_reports(self, raw_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not raw_reports:
            return {"total_reports": 0, "passed_count": 0, "pass_rate": 0.0, "average_score": 0.0, "top_lessons": []}

        # Ошибка: полностью пропускает валидацию диапазонов и полей!
        total = len(raw_reports)
        passed = sum(1 for r in raw_reports if r.get("status") == "passed")
        scores = [float(r.get("score", 0)) for r in raw_reports]

        return {
            "total_reports": total,
            "passed_count": passed,
            "pass_rate": round(passed / total, 2),
            "average_score": round(sum(scores) / total, 2),
            "top_lessons": [],
        }
