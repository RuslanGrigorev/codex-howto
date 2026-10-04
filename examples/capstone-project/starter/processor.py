"""examples/capstone-project/starter/processor.py - Заготовка для упражнения."""

from __future__ import annotations
from typing import Any, Dict, List


class CourseReportProcessor:
    """Обработчик и аналитический агрегатор учебных отчетов курса."""

    def process_reports(self, raw_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        # TODO: Реализовать валидацию отчетов, агрегацию метрик (pass_rate, average_score)
        # и безопасную обработку граничных случаев
        raise NotImplementedError("process_reports не реализован")
