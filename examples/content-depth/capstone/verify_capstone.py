#!/usr/bin/env python3
"""Скрипт сквозной валидации артефактов итогового проекта C01."""
from pathlib import Path

def main():
    root = Path(__file__).parent
    spec = root / "capstone_project_spec.md"
    readme = root / "README.md"
    assert spec.is_file(), "spec отсутствует"
    assert readme.is_file(), "readme отсутствует"
    print("PASS: C01 Capstone project artifacts verified")

if __name__ == "__main__":
    main()
