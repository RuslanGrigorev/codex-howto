#!/usr/bin/env python3
"""Тесты для хуков плагина E03 (fail-closed, фильтрация секретов, recursion guard)."""
import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).parent
PROMPT_SCRIPT = PLUGIN_DIR / "scripts" / "plugin_prompt_guard.py"
STOP_SCRIPT = PLUGIN_DIR / "scripts" / "plugin_stop_verifier.py"

def run_script(script_path: Path, stdin_data: str) -> dict:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(script_path)],
        input=stdin_data,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env
    )
    assert proc.returncode == 0
    return json.loads(proc.stdout.strip())

def test_plugin_prompt_guard():
    # 1. Разрешенный промпт
    res = run_script(PROMPT_SCRIPT, json.dumps({"prompt": "Объясни архитектуру плагина"}))
    assert res["status"] == "allow"

    # 2. Секрет блокируется
    dummy_key = "sk-" + ("1234567890abcdef" * 3)
    res_secret = run_script(PROMPT_SCRIPT, json.dumps({"prompt": f"Используй ключ {dummy_key}"}))
    assert res_secret["status"] == "deny"
    assert "секретный токен" in res_secret["reason"]

    # 3. Fail-closed на пустой ввод
    res_empty = run_script(PROMPT_SCRIPT, "")
    assert res_empty["status"] == "deny"

def test_plugin_stop_verifier():
    # 1. Разрешено когда тесты пройдены
    res = run_script(STOP_SCRIPT, json.dumps({"tests_passed": True}))
    assert res["status"] == "allow"

    # 2. Запрещено когда тесты не пройдены
    res_fail = run_script(STOP_SCRIPT, json.dumps({"tests_passed": False}))
    assert res_fail["status"] == "deny"

    # 3. Запрещено при рекурсии
    res_rec = run_script(STOP_SCRIPT, json.dumps({"tests_passed": True, "stop_hook_active": True}))
    assert res_rec["status"] == "deny"

    # 4. Fail-closed на пустой ввод
    res_empty = run_script(STOP_SCRIPT, "")
    assert res_empty["status"] == "deny"

if __name__ == "__main__":
    test_plugin_prompt_guard()
    test_plugin_stop_verifier()
    print("ALL PLUGIN HOOK TESTS PASSED")
