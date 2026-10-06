#!/usr/bin/env python3
"""Валидация файла рабочего процесса CI/CD A02 на соответствие контракту безопасности."""
import re
import sys
from pathlib import Path

def main():
    wf_file = Path(__file__).parent / "codex_review.yml"
    content = wf_file.read_text(encoding="utf-8")

    # 1. Запрет автоматического запуска на untrusted pull_request без доверенной изоляции
    assert "workflow_dispatch" in content, "В A02 обязателен доверенный запуск workflow_dispatch"
    assert "pull_request:" not in content, "Автоматический запуск на pull_request без изоляции запрещён"

    # 2. Безопасность checkout
    assert "persist-credentials: false" in content, "Checkout обязан указывать persist-credentials: false"

    # 3. Закрепление actions по полным commit SHA (immutable pinning)
    for action_match in re.finditer(r"uses:\s+([^@\s]+)@([^\s#]+)", content):
        action, ref = action_match.groups()
        assert len(ref) == 40, f"Action {action} должен быть закреплён по полному 40-значному SHA коммита, а не тегу: {ref}"

    # 4. Канонический синтаксис флагов Codex CLI 0.160.0
    assert "--sandbox read-only" in content, "Ревью в CI должно выполняться в режиме --sandbox read-only"
    assert "--ask-for-approval" in content, "Должен использоваться канонический флаг --ask-for-approval"
    assert "--sandbox-mode" not in content, "Устаревший флаг --sandbox-mode запрещён"
    assert "--approval-policy" not in content, "Устаревший флаг --approval-policy запрещён"

    # 5. Многоэтапная изоляция рабочих мест (Finding 5)
    assert "fetch_pr:" in content, "В A02 обязательна стадия fetch_pr"
    assert "review:" in content, "В A02 обязательна стадия review"
    assert "publish:" in content, "В A02 обязательна стадия publish"
    assert "needs: fetch_pr" in content, "Стадия review обязана зависеть от fetch_pr"
    assert "needs: review" in content, "Стадия publish обязана зависеть от review"

    # 6. Запрет утечки общих секретов в окружение процесса
    assert "CI_RUNNER_SECRET" not in content, "Переменная CI_RUNNER_SECRET не должна передаваться в окружение"

    print("PASS: A02 CI workflow security and syntax verification passed")

if __name__ == "__main__":
    main()
