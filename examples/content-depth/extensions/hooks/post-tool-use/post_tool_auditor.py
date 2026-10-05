#!/usr/bin/env python3
"""Хук PostToolUse: аудит выполненных действий с фиксацией реального статуса и ошибок."""
from __future__ import annotations
import json
import os
import sys

# Обеспечиваем UTF-8 для stdout/stderr на всех платформах
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def audit_event(payload: dict) -> dict:
    tool = payload.get("tool_name") or payload.get("tool") or "unknown"
    error = payload.get("error") or payload.get("error_message")
    status = payload.get("status")
    exit_code = payload.get("exit_code")
    result = payload.get("result")

    is_error = False
    error_detail = None

    if error:
        is_error = True
        error_detail = str(error)
    elif status in {"error", "failed", "failure"}:
        is_error = True
        error_detail = str(payload.get("message") or status)
    elif exit_code is not None and exit_code != 0:
        is_error = True
        error_detail = f"exit_code {exit_code}"
    elif isinstance(result, dict) and (result.get("error") or result.get("is_error")):
        is_error = True
        error_detail = str(result.get("error") or "tool returned error result")

    if is_error:
        sys.stderr.write(f"[AUDIT] Инструмент {tool} завершился с ошибкой: {error_detail}\n")
        return {"status": "audited", "tool": tool, "outcome": "error", "error": error_detail}
    else:
        sys.stderr.write(f"[AUDIT] Инструмент {tool} успешно завершил исполнение.\n")
        return {"status": "audited", "tool": tool, "outcome": "success"}

def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            sys.stderr.write("[AUDIT_ERROR] Пустой ввод в хук PostToolUse.\n")
            sys.stdout.write(json.dumps({"status": "deny", "reason": "Пустой ввод"}, ensure_ascii=False) + "\n")
            return
        payload = json.loads(raw_input)
    except Exception as exc:
        sys.stderr.write(f"[AUDIT_ERROR] Ошибка разбора полезной нагрузки PostToolUse: {exc}\n")
        sys.stdout.write(json.dumps({"status": "deny", "reason": f"Ошибка парсинга JSON: {exc}"}, ensure_ascii=False) + "\n")
        return

    res = audit_event(payload)
    sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
