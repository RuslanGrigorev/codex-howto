"""Учебная проверка относительных путей. Не замена системной песочнице."""
from pathlib import Path, PureWindowsPath
from typing import Optional

def validate_target_path(path_str: str, workspace_root: Path) -> Optional[Path]:
    if not isinstance(path_str,str) or not path_str or '\x00' in path_str:
        return None
    if path_str.startswith(('~','/','\\')) or PureWindowsPath(path_str).drive or '\\' in path_str:
        return None
    root=Path(workspace_root).resolve()
    target=(root/path_str).resolve()
    return target if target!=root and target.is_relative_to(root) else None
