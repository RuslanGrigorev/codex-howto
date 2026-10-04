"""examples/local-mcp/starter/mcp_server.py - Заготовка для упражнения."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional


class LocalMcpHandler:
    """Обработчик запросов безопасного локального stdio MCP-сервера."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()

    def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Реализовать обработку JSON-RPC 2.0 (initialize, tools/list, tools/call)
        # с обязательной проверкой выхода за пределы workspace_root
        raise NotImplementedError("handle_request не реализован")
