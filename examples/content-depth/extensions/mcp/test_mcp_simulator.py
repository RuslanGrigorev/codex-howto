#!/usr/bin/env python3
"""Тесты симулятора клиента MCP: вызов инструментов, границы путей, отказ и восстановление (Finding 8)."""
import pytest
from pathlib import Path

from mcp_client_simulator import (
    MCPClientSimulator,
    MockMCPTransport,
    StdioFixtureTransport,
    HttpOAuthFixtureTransport,
    MCPPathBoundaryError,
    MCPRefusalError,
    MCPTimeoutError,
    MCPAuthError,
    MCPToolNotFoundError,
    MCPError
)

def test_mcp_initialize_and_tool_call():
    root = Path(__file__).resolve().parent
    transport = MockMCPTransport(workspace_root=root)
    client = MCPClientSimulator(transport)

    # Инициализация и получение списка
    init_res = client.initialize()
    assert init_res["serverInfo"]["name"] == "mock-mcp-fs"

    tools = client.list_tools()
    assert any(t["name"] == "read_workspace_file" for t in tools)

    # Успешный вызов инструмента
    call_res = client.call_tool("read_workspace_file", {"path": "README.md"})
    assert "content" in call_res
    assert len(call_res["content"]) > 0

def test_mcp_path_boundary_enforcement():
    """Проверка блокировки path traversal атак через аргументы инструмента."""
    root = Path(__file__).resolve().parent
    transport = MockMCPTransport(workspace_root=root)
    client = MCPClientSimulator(transport)
    client.initialize()

    # Попытка прочитать файл за пределами workspace
    try:
        client.call_tool("read_workspace_file", {"path": "../../../etc/passwd"})
        assert False, "Ожидалось исключение MCPPathBoundaryError"
    except MCPPathBoundaryError as exc:
        assert "выходит за пределы workspace" in str(exc) or "заблокировал выход" in str(exc)

def test_mcp_refusal_and_recovery():
    """Проверка обработки отказа сервера и последующего успешного восстановления."""
    root = Path(__file__).resolve().parent
    transport = MockMCPTransport(workspace_root=root)
    client = MCPClientSimulator(transport)
    client.initialize()

    # Вызов запрещённого инструмента
    try:
        client.call_tool("sensitive_admin_action", {})
        assert False, "Ожидалось исключение MCPRefusalError"
    except MCPRefusalError as exc:
        assert "отклонено" in str(exc)

    # Восстановление: последующий легитимный вызов работает штатно
    res = client.call_tool("read_workspace_file", {"path": "README.md"})
    assert res is not None

def test_mcp_timeout_handling():
    """Проверка обработки тайм-аута соединения."""
    root = Path(__file__).resolve().parent
    transport = MockMCPTransport(workspace_root=root)
    transport.should_timeout = True
    client = MCPClientSimulator(transport)

    try:
        client.initialize()
        assert False, "Ожидалось исключение MCPTimeoutError"
    except MCPTimeoutError:
        pass

def test_http_oauth_flow_and_unauthorized_rejection():
    """Проверка HTTP/OAuth: 401 Unauthorized при отсутствии токена и успешный вызов после обмена."""
    transport = HttpOAuthFixtureTransport()
    client = MCPClientSimulator(transport)

    # 1. Без токена вызов отвергается с 401 (MCPAuthError)
    try:
        client.initialize()
        assert False, "Ожидалось исключение MCPAuthError без Bearer токена"
    except MCPAuthError as exc:
        assert "401" in str(exc)

    # 2. Успешный обмен учетных данных OAuth на Bearer токен
    token = transport.authenticate_oauth("trusted-client", "trusted-secret")
    assert token is not None

    # 3. После аутентификации вызовы работают
    init_res = client.initialize()
    assert init_res["serverInfo"]["name"] == "remote-http-mcp"
    tools = client.list_tools()
    assert len(tools) == 1
    call_res = client.call_tool("remote_api_query", {})
    assert call_res["content"][0]["text"] == "OAuth API response"

def test_stdio_notifications_channel():
    """Проверка асинхронного канала уведомлений в stdio транспорте."""
    root = Path(__file__).resolve().parent
    transport = StdioFixtureTransport(workspace_root=root)
    client = MCPClientSimulator(transport)
    assert len(client.notifications) == 0

    client.initialize()
    # Сервер отправляет уведомление при инициализации
    assert len(client.notifications) >= 1
    assert client.notifications[0]["method"] == "notifications/tools/list_changed"

def test_missing_tool_raises_typed_error():
    """Вызов неизвестного инструмента порождает MCPToolNotFoundError."""
    root = Path(__file__).resolve().parent
    transport = MockMCPTransport(workspace_root=root)
    client = MCPClientSimulator(transport)
    client.initialize()

    try:
        client.call_tool("nonexistent_tool", {})
        assert False, "Ожидалось исключение MCPToolNotFoundError"
    except MCPToolNotFoundError as exc:
        assert "not found" in str(exc)

def test_oauth_token_expiry_rejection():
    """Проверка отклонения запроса при истечении срока действия Bearer токена."""
    import time
    transport = HttpOAuthFixtureTransport()
    transport.authenticate_oauth("trusted-client", "trusted-secret")
    client = MCPClientSimulator(transport)
    assert client.initialize() is not None

    # Истечение срока жизни токена
    transport.token_expiry_timestamp = time.time() - 1.0
    try:
        client.list_tools()
        assert False, "Ожидалось исключение MCPAuthError при истёкшем токене"
    except MCPAuthError as exc:
        assert "истёк" in str(exc)

if __name__ == "__main__":
    test_mcp_initialize_and_tool_call()
    test_mcp_path_boundary_enforcement()
    test_mcp_refusal_and_recovery()
    test_mcp_timeout_handling()
    test_http_oauth_flow_and_unauthorized_rejection()
    test_oauth_token_expiry_rejection()
    test_stdio_notifications_channel()
    test_missing_tool_raises_typed_error()
    print("ALL MCP SIMULATOR TESTS PASSED")
