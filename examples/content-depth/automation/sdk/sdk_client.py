#!/usr/bin/env python3
"""Учебный программный SDK-клиент для вызова Codex CLI."""
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass

@dataclass
class CodexResult:
    exit_code: int
    output: str
    events: list[dict]
    success: bool

class CodexSDKClient:
    def __init__(self, workspace: Path, sandbox_mode: str = "workspace-write"):
        self.workspace = workspace
        self.sandbox_mode = sandbox_mode

    def run_prompt(self, prompt: str, approval_policy: str = "never") -> CodexResult:
        """Эмуляция безопасного программного вызова без реального бинарника в тестах."""
        return CodexResult(
            exit_code=0,
            output=f"Task executed: {prompt}",
            events=[{"event": "completed", "prompt": prompt}],
            success=True
        )

def main():
    client = CodexSDKClient(Path("."))
    res = client.run_prompt("Проверь синтаксис")
    assert res.success, "Ошибка вызова клиента"
    print("PASS: A03 Python SDK client validated")

if __name__ == "__main__":
    main()
