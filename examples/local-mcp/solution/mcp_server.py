"""examples/local-mcp/solution/mcp_server.py - Эталонное решение безопасного MCP-сервера."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class LocalMcpHandler:
    """Обработчик запросов безопасного локального stdio MCP-сервера."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()

    def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        req_id = req.get("id")
        jsonrpc = req.get("jsonrpc")

        if jsonrpc != "2.0" or req_id is None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32600, "message": "Invalid Request: ожидается jsonrpc 2.0 и id"},
            }

        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "local-safe-mcp", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                },
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "read_file_safe",
                            "description": "Безопасное чтение файла строго внутри workspace_root",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string", "description": "Относительный путь к файлу"}
                                },
                                "required": ["path"],
                            },
                        }
                    ]
                },
            }

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "read_file_safe":
                rel_path = arguments.get("path", "")
                target_path = (self.workspace_root / rel_path).resolve()

                # Проверка выхода за границы рабочего каталога
                try:
                    target_path.relative_to(self.workspace_root)
                except ValueError:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "isError": True,
                            "content": [
                                {
                                    "type": "text",
                                    "text": "ОШИБКА БЕЗОПАСНОСТИ: Попытка выхода за пределы рабочей директории",
                                }
                            ],
                        },
                    }

                if not target_path.exists() or not target_path.is_file():
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "isError": True,
                            "content": [{"type": "text", "text": f"Файл не найден: {rel_path}"}],
                        },
                    }

                try:
                    content = target_path.read_text(encoding="utf-8")
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "isError": False,
                            "content": [{"type": "text", "text": content}],
                        },
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "isError": True,
                            "content": [{"type": "text", "text": f"Ошибка чтения: {e}"}],
                        },
                    }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Неизвестный инструмент: {tool_name}"},
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Неизвестный метод: {method}"},
        }
