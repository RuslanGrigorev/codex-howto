#!/usr/bin/env python3
"""Хук PreToolUse: валидация аргументов инструментов."""
import json
import sys

def main():
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input) if raw_input.strip() else {}
    except Exception as e:
        sys.stdout.write(json.dumps({"status": "deny", "reason": f"Ошибка JSON: {e}"}) + "\n")
        return

    tool = payload.get("tool_name", "")
    args = payload.get("arguments", {})
    
    # Запрещаем деструктивные команды
    if tool == "run_command":
        cmd = str(args.get("command", ""))
        if "rm -rf" in cmd or "drop database" in cmd.lower():
            sys.stdout.write(json.dumps({
                "status": "deny",
                "reason": "Деструктивная команда отклонена хуком безопасности."
            }) + "\n")
            return

    # Запрещаем чтение секретов
    if tool in {"read_file", "edit_file"}:
        path = str(args.get("path", ""))
        if ".env" in path or "id_rsa" in path or "auth.json" in path:
            sys.stdout.write(json.dumps({
                "status": "deny",
                "reason": "Доступ к файлам секретов заблокирован хуком."
            }) + "\n")
            return

    sys.stdout.write(json.dumps({"status": "allow"}) + "\n")

if __name__ == "__main__":
    main()
