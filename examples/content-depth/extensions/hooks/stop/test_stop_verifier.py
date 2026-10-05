#!/usr/bin/env python3
"""Тесты для хука Stop (fail-closed, tests_passed verification)."""
import json
import subprocess
import sys
from pathlib import Path

STOP_SCRIPT = Path(__file__).parent / "stop_verifier.py"

def run_hook(stdin_data: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(STOP_SCRIPT)],
        input=stdin_data,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    assert proc.returncode == 0
    return json.loads(proc.stdout.strip())

def test_stop_hook_allows_when_tests_passed():
    res = run_hook(json.dumps({"task_id": "T1", "tests_passed": True}))
    assert res["status"] == "allow"
    assert "успешна" in res["message"]

def test_stop_hook_denies_when_tests_failed_or_missing():
    res = run_hook(json.dumps({"task_id": "T1", "tests_passed": False}))
    assert res["status"] == "deny"
    assert "отклонено" in res["reason"]

    res_missing = run_hook(json.dumps({"task_id": "T1"}))
    assert res_missing["status"] == "deny"

def test_stop_hook_fail_closed_on_empty_and_malformed():
    res_empty = run_hook("")
    assert res_empty["status"] == "deny"

    res_bad = run_hook("{malformed-json")
    assert res_bad["status"] == "deny"

if __name__ == "__main__":
    test_stop_hook_allows_when_tests_passed()
    test_stop_hook_denies_when_tests_failed_or_missing()
    test_stop_hook_fail_closed_on_empty_and_malformed()
    print("ALL STOP HOOK TESTS PASSED")
