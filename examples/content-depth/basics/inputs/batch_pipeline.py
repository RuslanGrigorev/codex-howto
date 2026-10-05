#!/usr/bin/env python3
"""Демонстрация симуляции пакетного конвейера ввода."""
import sys
from pathlib import Path

def main():
    task_file = Path(__file__).parent / "sample_task.txt"
    task_content = task_file.read_text(encoding="utf-8")
    
    print(f"Считана задача ({len(task_content)} байт):")
    for line in task_content.strip().splitlines():
        print(f"  > {line}")
    print("PASS: B04 batch pipeline input demo")

if __name__ == "__main__":
    main()
