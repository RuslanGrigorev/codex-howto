#!/usr/bin/env python3
"""Тесты для хука PostToolUse: аудит успешных и ошибочных результатов."""
import json
import os
import subprocess
import sys
from pathlib import Path

AUDITOR_SCRIPT = Path(__file__).parent / "post_tool_auditor.py"

def run_hook(stdin_data: str) -> tuple[dict, str]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(AUDITOR_SCRIPT)],
        input=stdin_data,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env
    )
    assert proc.returncode == 0
    return json.loads(proc.stdout.strip()), proc.stderr

def test_auditor_logs_success():
    res, stderr = run_hook(json.dumps({
        "tool_name": "read_file",
        "result": {"content": "data"}
    }))
    assert res["status"] == "audited"
    assert res["outcome"] == "success"
    assert "успешно" in stderr

def test_auditor_logs_error_outcome():
    res, stderr = run_hook(json.dumps({
        "tool_name": "bash",
        "exit_code": 1,
        "error": "command not found"
    }))
    assert res["status"] == "audited"
    assert res["outcome"] == "error"
    assert "завершился с ошибкой" in stderr
    assert "command not found" in stderr

def test_auditor_fail_closed_on_empty_and_malformed():
    res_empty, stderr_empty = run_hook("")
    assert res_empty["status"] == "deny"
    assert "Пустой ввод" in stderr_empty

    res_bad, stderr_bad = run_hook("{malformed-json")
    assert res_bad["status"] == "deny"
    assert "Ошибка разбора" in stderr_bad

if __name__ == "__main__":
    test_auditor_logs_success()
    test_auditor_logs_error_outcome()
    test_auditor_fail_closed_on_empty_and_malformed()
    print("ALL POST_TOOL_AUDITOR TESTS PASSED")
