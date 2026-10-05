"""Модуль агрегации метрик производительности (исходная заготовка с дефектом)."""
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any

def calculate_percentiles(values: list[float]) -> dict[str, float]:
    if not values:
        raise ValueError("Список значений не может быть пустым")
    sorted_vals = sorted(values)
    n = len(sorted_vals)

    # Дефект: неверный расчёт индексов перцентилей (смещение на 1 или округление)
    p50_idx = int(n * 0.5)
    p95_idx = int(n * 0.95)
    p99_idx = int(n * 0.99)

    return {
        "p50": float(sorted_vals[min(p50_idx, n - 1)]),
        "p95": float(sorted_vals[min(p95_idx, n - 1)]),
        "p99": float(sorted_vals[min(p99_idx, n - 1)]),
    }

def aggregate_metrics(raw_data: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [item["latency_ms"] for item in raw_data if "latency_ms" in item]
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
