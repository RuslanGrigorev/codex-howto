"""broken_mutation_secrets/validator.py - Мутация без проверки секретов."""

import re
from typing import Tuple


def validate_agents_content(content: str) -> Tuple[bool, str]:
    has_commands = bool(re.search(r"##\s+.*команд", content, re.IGNORECASE))
    has_rules = bool(re.search(r"##\s+.*правил", content, re.IGNORECASE))
    if not (has_commands and has_rules):
        return False, "Отсутствуют обязательные разделы"

    # ОШИБКА: проверка секретов пропущена

    path_patterns = [r"[a-zA-Z]:\\users\\", r"/home/[a-zA-Z0-9_-]+/", r"/Users/[a-zA-Z0-9_-]+/"]
    for pattern in path_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False, "Обнаружен путь"

    return True, ""
