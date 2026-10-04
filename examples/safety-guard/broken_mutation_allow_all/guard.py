"""broken_mutation_allow_all/guard.py - Мутация без ограничений доступа."""

from pathlib import Path
from typing import Optional


def validate_target_path(path_str: str, workspace_root: Path) -> Optional[Path]:
    # ОШИБКА: возвращает любой разрешенный путь без проверки корня
    return Path(path_str).resolve()
