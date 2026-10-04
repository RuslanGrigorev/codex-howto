"""starter/guard.py - Заготовка для упражнения safety-guard."""

from pathlib import Path
from typing import Optional


def validate_target_path(path_str: str, workspace_root: Path) -> Optional[Path]:
    """TODO: Реализуйте проверку, гарантирующую, что path_str не выходит за пределы workspace_root."""
    ws = Path(workspace_root)
    # ОШИБКА: наивная конкатенация без проверки выхода через `..`
    return ws / path_str
