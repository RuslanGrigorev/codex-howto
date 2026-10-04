"""solution/validator.py - Эталонная реализация проверки структуры AGENTS.md."""

import re
from typing import Tuple


def validate_agents_content(content: str) -> Tuple[bool, str]:
    """Проверяет соответствие содержимого AGENTS.md стандартам качества и безопасности."""
    # 1. Проверка наличия обязательных секций (Команды и Правила)
    has_commands = bool(re.search(r"##\s+.*команд", content, re.IGNORECASE))
    has_rules = bool(re.search(r"##\s+.*правил", content, re.IGNORECASE))
    
    if not (has_commands and has_rules):
        return False, "Отсутствуют обязательные разделы (Команды и Правила)"

    # 2. Проверка утечки секретов и токенов
    secret_patterns = [
        r"sk-[a-zA-Z0-9_\-]{16,}",
        r"ghp_[a-zA-Z0-9]{20,}",
        r"password\s*[:=]\s*\S+",
    ]
    for pattern in secret_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False, "Обнаружен возможный секрет или токен доступа"

    # 3. Проверка хардкода персональных путей
    path_patterns = [
        r"[a-zA-Z]:\\users\\",
        r"/home/[a-zA-Z0-9_-]+/",
        r"/Users/[a-zA-Z0-9_-]+/",
    ]
    for pattern in path_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False, "Обнаружен абсолютный системный путь пользователя"

    return True, ""
