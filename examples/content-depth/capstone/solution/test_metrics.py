#!/usr/bin/env python3
"""Независимый набор тестов для итогового проекта C01."""
import math
import sys
from metrics import calculate_percentiles, aggregate_metrics

def test_empty_list_raises_value_error():
    try:
        calculate_percentiles([])
        assert False, "Ожидалось исключение ValueError для пустого списка"
    except ValueError:
        pass

def test_precise_percentiles():
    # 100 значений от 1 до 100
    data = [float(i) for i in range(1, 101)]
    res = calculate_percentiles(data)

    # p50 медиана для 1..100 = 50.5
    assert math.isclose(res["p50"], 50.5, rel_tol=1e-2), f"p50: ожидалось 50.5, получено {res['p50']}"
    # p95 = 95.05 или 95.0
    assert math.isclose(res["p95"], 95.0, abs_tol=0.5), f"p95: ожидалось 95.0, получено {res['p95']}"
    # p99 = 99.01 или 99.0
    assert math.isclose(res["p99"], 99.0, abs_tol=0.5), f"p99: ожидалось 99.0, получено {res['p99']}"

def test_aggregate_metrics():
    items = [{"latency_ms": 10.0}, {"latency_ms": 20.0}, {"latency_ms": 30.0}]
    summary = aggregate_metrics(items)
    assert summary["count"] == 3
    assert summary["min"] == 10.0
    assert summary["max"] == 30.0
    assert math.isclose(summary["mean"], 20.0)

if __name__ == "__main__":
    test_empty_list_raises_value_error()
    test_precise_percentiles()
    test_aggregate_metrics()
    print("ALL METRICS TESTS PASSED")
