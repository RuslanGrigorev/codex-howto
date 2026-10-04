"""examples/local-mcp/broken_mutation_no_bounds/mcp_server.py - Ошибочная мутация."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional


class LocalMcpHandler:
    """Ошибочная мутация: не проверяет выход за границы каталога workspace (уязвима к Directory Traversal)."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()

    def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"serverInfo": {"name": "insecure"}}}

        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": [{"name": "read_file_safe"}]}}

        if method == "tools/call":
            arguments = params.get("arguments", {})
            rel_path = arguments.get("path", "")
            # Ошибка: прямое открытие пути без проверки выхода за workspace!
            target_path = (self.workspace_root / rel_path).resolve()
            if target_path.exists():
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"isError": False, "content": [{"type": "text", "text": target_path.read_text(encoding="utf-8")}]},
                }
            return {"jsonrpc": "2.0", "id": req_id, "result": {"isError": True, "content": [{"type": "text", "text": "not found"}]}}

        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}
