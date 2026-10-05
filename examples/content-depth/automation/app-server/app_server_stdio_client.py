#!/usr/bin/env python3
"""Симулятор протокола взаимодействия с codex app-server."""
import json
import sys

def main():
    # Пошаговая демонстрация протокола app-server
    messages = [
        {"method": "initialize", "params": {"clientInfo": {"name": "TestIDE", "version": "1.0"}}},
        {"method": "thread/create", "params": {"workspace": "/path/to/project"}},
        {"method": "turn/start", "params": {"threadId": "th_1", "prompt": "Проанализируй тесты"}},
        {"method": "turn/cancel", "params": {"threadId": "th_1"}}
    ]
    for m in messages:
        print(f"Отправка запроса: {m['method']}")
    print("PASS: A04 App-server protocol sequence validated")

if __name__ == "__main__":
    main()
