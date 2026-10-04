"""broken_mutation_relative/guard.py - Мутация с уязвимостью относительного пути."""

from pathlib import Path
from typing import Optional


def validate_target_path(path_str: str, workspace_root: Path) -> Optional[Path]:
    ws = Path(workspace_root)
    # ОШИБКА: строковая проверка не предотвращает обход через `subdir/../../`
    if ".." in path_str and not path_str.startswith("subdir"):
        return None
    return ws / path_str
