#!/usr/bin/env python3
"""Симулятор клиента Model Context Protocol (MCP) в Codex CLI 0.160.0 (E04).

Поддерживает:
- Handshake инициализации (initialize) и согласование версии протокола.
- Получение списка инструментов (tools/list).
- Вызов инструментов (tools/call) со строгой проверкой границ путей (path boundary).
- Обработку отказов сервера (refusal recovery) и тайм-аутов.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

# UTF-8 reconfigure
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


class MCPError(Exception):
    """Базовое исключение MCP."""
    pass


class MCPTimeoutError(MCPError):
    """Превышение допустимого времени ответа MCP-сервера."""
    pass


class MCPPathBoundaryError(MCPError):
    """Попытка выхода за пределы доверенной файловой песочницы через аргументы инструмента."""
    pass


class MCPRefusalError(MCPError):
    """Отказ сервера в выполнении вызова инструмента."""
    pass


class MCPAuthError(MCPError):
    """Ошибка авторизации HTTP/OAuth (401 Unauthorized / Token Expiry)."""
    pass


class MCPToolNotFoundError(MCPError):
    """Запрошенный инструмент отсутствует на MCP-сервере."""
    pass


class BaseMCPTransport(ABC):
    """Базовый интерфейс транспорта MCP."""

    @abstractmethod
    def handle_request(self, raw_request: str) -> str:
        raise NotImplementedError

    def set_notification_handler(self, handler: Callable[[str, dict[str, Any]], None]) -> None:
        pass


class StdioFixtureTransport(BaseMCPTransport):
    """Детерминированный stdio-транспорт с поддержкой входящих уведомлений."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()
        self.should_timeout = False
        self._notification_handler: Optional[Callable[[str, dict[str, Any]], None]] = None

    def set_notification_handler(self, handler: Callable[[str, dict[str, Any]], None]) -> None:
        self._notification_handler = handler

    def emit_notification(self, method: str, params: dict[str, Any]) -> None:
        if self._notification_handler:
            self._notification_handler(method, params)

    def handle_request(self, raw_request: str) -> str:
        if self.should_timeout:
            raise MCPTimeoutError("Имитация тайм-аута MCP сервера")

        req = json.loads(raw_request)
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            res = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mock-mcp-fs", "version": "1.0.0"}
            }
            # При инициализации сервер может отправить уведомление об обновлении инструментов
            if self._notification_handler:
                self._notification_handler("notifications/tools/list_changed", {})
            return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": res})

        elif method == "tools/list":
            tools = [
                {
                    "name": "read_workspace_file",
                    "description": "Безопасное чтение файла из песочницы проекта",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"]
                    }
                },
                {
                    "name": "sensitive_admin_action",
                    "description": "Административное действие, требующее повышенных прав",
                    "inputSchema": {"type": "object"}
                }
            ]
            return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}})

        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {})

            if name == "sensitive_admin_action":
                return json.dumps({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32003, "message": "Refusal: действие отклонено политикой безопасности MCP"}
                })

            if name == "read_workspace_file":
                rel_path = args.get("path", "")
                target = (self.workspace_root / rel_path).resolve()
                if not target.is_relative_to(self.workspace_root):
                    return json.dumps({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32002,
                            "message": f"Path boundary violation: путь '{rel_path}' выходит за пределы workspace"
                        }
                    })
                return json.dumps({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": "Stdio content"}]}
                })

            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool '{name}' not found"}
            })

        return json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32600, "message": f"Invalid method {method}"}
        })


class HttpOAuthFixtureTransport(BaseMCPTransport):
    """Детерминированный HTTP/OAuth транспорт со строгой проверкой токенов (Finding 6)."""

    def __init__(self, valid_token: str = "valid-mcp-bearer-token"):
        self.valid_token = valid_token
        self.current_token: Optional[str] = None
        self.token_expiry_timestamp: float = 9999999999.0

    def set_bearer_token(self, token: Optional[str]) -> None:
        self.current_token = token

    def authenticate_oauth(self, client_id: str, client_secret: str) -> str:
        if client_id == "trusted-client" and client_secret == "trusted-secret":
            self.current_token = self.valid_token
            return self.valid_token
        raise MCPAuthError("Неверные учетные данные OAuth (client_id/client_secret)")

    def handle_request(self, raw_request: str) -> str:
        import time
        if self.current_token != self.valid_token or time.time() > self.token_expiry_timestamp:
            raise MCPAuthError("HTTP 401 Unauthorized: Отсутствует, недействителен или истёк Bearer токен")

        req = json.loads(raw_request)
        req_id = req.get("id")
        method = req.get("method")

        if method == "initialize":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "remote-http-mcp"}}
            })
        elif method == "tools/list":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": [{"name": "remote_api_query", "description": "Запрос к удалённому API"}]}
            })
        elif method == "tools/call":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": "OAuth API response"}]}
            })
        return json.dumps({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32600, "message": "Unknown"}})

class MockMCPTransport(StdioFixtureTransport):
    """Совместимый псевдоним для StdioFixtureTransport."""
    pass


class MCPClientSimulator:
    """Клиент MCP с поддержкой жизненного цикла и проверки границ песочницы."""

    def __init__(self, transport: BaseMCPTransport):
        self.transport = transport
        self._next_id = 1
        self.initialized = False
        self.available_tools: list[dict[str, Any]] = []
        self.notifications: list[dict[str, Any]] = []
        self.transport.set_notification_handler(self._on_notification)

    def _on_notification(self, method: str, params: dict[str, Any]) -> None:
        self.notifications.append({"method": method, "params": params})

    def _call(self, method: str, params: dict[str, Any]) -> Any:
        req_id = self._next_id
        self._next_id += 1
        req = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        raw_resp = self.transport.handle_request(json.dumps(req))
        resp = json.loads(raw_resp)

        if "error" in resp and resp["error"]:
            err = resp["error"]
            msg = err.get("message", "MCP error")
            code = err.get("code")
            if code == -32601 or "not found" in msg.lower():
                raise MCPToolNotFoundError(msg)
            if "boundary violation" in msg.lower():
                raise MCPPathBoundaryError(msg)
            if "refusal" in msg.lower():
                raise MCPRefusalError(msg)
            raise MCPError(f"MCP error {code}: {msg}")

        return resp.get("result")

    def initialize(self) -> dict[str, Any]:
        result = self._call("initialize", {"protocolVersion": "2024-11-05"})
        self.initialized = True
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        if not self.initialized:
            raise MCPError("Клиент MCP не инициализирован")
        result = self._call("tools/list", {})
        self.available_tools = result.get("tools", [])
        return self.available_tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if not self.initialized:
            raise MCPError("Клиент MCP не инициализирован")

        # Клиентская предварительная валидация границ путей
        if "path" in arguments:
            p = arguments["path"]
            if "../" in p or "..\\" in p:
                # Обнаружен относительный переход вверх
                target = (self.transport.workspace_root / p).resolve()
                if not target.is_relative_to(self.transport.workspace_root):
                    raise MCPPathBoundaryError(f"Клиент заблокировал выход из workspace: '{p}'")

        return self._call("tools/call", {"name": name, "arguments": arguments})


def main():
    root = Path(__file__).resolve().parent
    transport = MockMCPTransport(workspace_root=root)
    client = MCPClientSimulator(transport)

    client.initialize()
    tools = client.list_tools()
    assert len(tools) >= 2

    res = client.call_tool("read_workspace_file", {"path": "README.md"})
    assert res is not None

    print("PASS: E04 MCP client simulator flow validated")


if __name__ == "__main__":
    main()
