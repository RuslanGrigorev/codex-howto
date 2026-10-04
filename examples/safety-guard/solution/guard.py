"""solution/guard.py - Эталонная реализация проверки путей песочницы."""

from pathlib import Path
from typing import Optional


def validate_target_path(path_str: str, workspace_root: Path) -> Optional[Path]:
    """Проверяет, что путь path_str находится строго внутри каталога workspace_root.
    Возвращает разрешенный Path или None, если путь выходит за пределы workspace.
    """
    ws = Path(workspace_root).resolve()
    
    # Запрещаем обращение к домашней директории пользователя через тильду
    if path_str.startswith("~"):
        return None

    target = (ws / path_str).resolve()
    
    try:
        # Проверяем, что target является потомком ws
        target.relative_to(ws)
        return target
    except ValueError:
        return None
