"""broken_mutation_paths/validator.py - Мутация без проверки персональных путей."""

import re
from typing import Tuple


def validate_agents_content(content: str) -> Tuple[bool, str]:
    has_commands = bool(re.search(r"##\s+.*команд", content, re.IGNORECASE))
    has_rules = bool(re.search(r"##\s+.*правил", content, re.IGNORECASE))
    if not (has_commands and has_rules):
        return False, "Отсутствуют обязательные разделы"

    secret_patterns = [r"sk-[a-zA-Z0-9_\-]{16,}", r"ghp_[a-zA-Z0-9]{20,}", r"password\s*[:=]\s*\S+"]
    for pattern in secret_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False, "Обнаружен секрет"

    # ОШИБКА: проверка абсолютных путей пропущена
    return True, ""
