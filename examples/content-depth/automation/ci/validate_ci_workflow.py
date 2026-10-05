#!/usr/bin/env python3
"""Валидация файла рабочего процесса CI/CD A02."""
from pathlib import Path

def main():
    wf_file = Path(__file__).parent / "codex_review.yml"
    content = wf_file.read_text(encoding="utf-8")
    
    assert "approval-policy never" in content, "В CI обязателен approval-policy never"
    assert "secrets.CODEX_API_KEY" in content, "Ключ должен браться из secrets"
    assert "pull-requests: write" in content, "Не настроены permissions"
    print("PASS: A02 CI workflow safety checks passed")

if __name__ == "__main__":
    main()
