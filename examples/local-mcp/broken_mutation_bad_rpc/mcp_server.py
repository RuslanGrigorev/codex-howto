"""examples/local-mcp/broken_mutation_bad_rpc/mcp_server.py - Ошибочная мутация."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional


class LocalMcpHandler:
    """Ошибочная мутация: нарушает формат JSON-RPC 2.0 (нет поля jsonrpc или id)."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()

    def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        # Ошибка: возвращает некорректный RPC ответ без jsonrpc="2.0" и без id
        return {
            "result": {"status": "ok"},
        }
