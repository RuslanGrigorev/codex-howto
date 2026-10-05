#!/usr/bin/env python3
"""Тесты для хука UserPromptSubmit (fail-closed, secret redaction)."""
import json
import subprocess
import sys
from pathlib import Path

GUARD_SCRIPT = Path(__file__).parent / "prompt_guard.py"

def run_hook(stdin_data: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=stdin_data,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    assert proc.returncode == 0
    return json.loads(proc.stdout.strip())

def test_prompt_guard_allows_safe_prompt():
    res = run_hook(json.dumps({"prompt": "Исправь форматирование в коде"}))
    assert res["status"] == "allow"

def test_prompt_guard_denies_secrets():
    dummy_token = "sk-" + "12345678901234567890123456789012"
    res_key = run_hook(json.dumps({"prompt": f"Вот мой токен {dummy_token}"}))
    assert res_key["status"] == "deny"
    assert "заблокирован" in res_key["reason"]

    res_ssh = run_hook(json.dumps({"prompt": "BEGIN " + "OPENSSH PRIVATE KEY\n..."}))
    assert res_ssh["status"] == "deny"

def test_prompt_guard_fail_closed_on_empty_and_malformed():
    res_empty = run_hook("")
    assert res_empty["status"] == "deny"

    res_bad = run_hook("{broken: json")
    assert res_bad["status"] == "deny"

if __name__ == "__main__":
    test_prompt_guard_allows_safe_prompt()
    test_prompt_guard_denies_secrets()
    test_prompt_guard_fail_closed_on_empty_and_malformed()
    print("ALL PROMPT GUARD TESTS PASSED")
