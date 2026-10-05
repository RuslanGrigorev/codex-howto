"""Независимый контракт относительных путей; не проверка всей песочницы Codex."""
import tempfile,sys
from pathlib import Path
from guard import validate_target_path

def main():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)/'workspace';root.mkdir()
        for rel in ['file.txt','subdir/nested.py','./deep/path/data.json']:
            result=validate_target_path(rel,root)
            assert result is not None and Path(result).resolve().is_relative_to(root.resolve()),rel
        bad=['../outside.txt','subdir/../../escape.txt','/etc/passwd','~/.codex/config.toml','C:\\Windows\\System32','C:relative.txt','\\\\server\\share','.',str(root.parent/'workspace-other/file')]
        for rel in bad:
            try:result=validate_target_path(rel,root)
            except (ValueError,PermissionError):continue
            assert result is None,'Опасный путь не отклонён: '+rel
        try:
            (root/'outside').symlink_to(root.parent,target_is_directory=True)
        except (OSError,NotImplementedError):
            pass  # OS без права symlink: отдельная нативная проверка обязательна.
        else:
            assert validate_target_path('outside/file',root) is None
    print('PASS: контракт учебных путей')

if __name__=='__main__':
    try:main()
    except Exception as exc:print('FAIL: '+str(exc),file=sys.stderr);sys.exit(1)
