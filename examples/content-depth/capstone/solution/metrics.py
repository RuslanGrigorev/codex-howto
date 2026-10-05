"""Эталонное решение модуля агрегации метрик производительности для C01."""
from __future__ import annotations
import math
from typing import Any

def calculate_percentiles(values: list[float]) -> dict[str, float]:
    if not values:
        raise ValueError("Список значений не может быть пустым")
    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def get_percentile(p: float) -> float:
        # Корректная интерполяция перцентиля (ранговый метод)
        k = (n - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(sorted_vals[int(k)])
        d0 = sorted_vals[int(f)] * (c - k)
        d1 = sorted_vals[int(c)] * (k - f)
        return float(d0 + d1)

    return {
        "p50": get_percentile(0.5),
        "p95": get_percentile(0.95),
        "p99": get_percentile(0.99),
    }

def aggregate_metrics(raw_data: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [float(item["latency_ms"]) for item in raw_data if "latency_ms" in item]
    if not latencies:
        raise ValueError("Нет данных latency_ms для агрегации")

    percentiles = calculate_percentiles(latencies)
    return {
        "count": len(latencies),
        "min": min(latencies),
        "max": max(latencies),
        "mean": sum(latencies) / len(latencies),
        "percentiles": percentiles
    }
