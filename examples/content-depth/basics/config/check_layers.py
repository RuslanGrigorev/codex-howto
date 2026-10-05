#!/usr/bin/env python3
"""Проверка конфигурационных профилей B02."""
import tomllib
from pathlib import Path

def main():
    root = Path(__file__).parent
    for toml_path in root.glob("*.config.toml"):
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        assert "sandbox_mode" in data, f"{toml_path.name}: нет sandbox_mode"
        assert data["sandbox_mode"] in {"read-only", "workspace-write", "danger-full-access"}
        assert data.get("approval_policy") in {"on-request", "never"}
        print(f"PASS: {toml_path.name} валиден (sandbox={data['sandbox_mode']}, approval={data.get('approval_policy')})")

if __name__ == "__main__":
    main()
