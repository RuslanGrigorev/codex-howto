#!/usr/bin/env python3
"""Тесты симулятора клиента MCP: вызов инструментов, границы путей, отказ и восстановление (Finding 8)."""
import pytest
from pathlib import Path

from mcp_client_simulator import (
    MCPClientSimulator,
    MockMCPTransport,
    MCPPathBoundaryError,
    MCPRefusalError,
    MCPTimeoutError,
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

if __name__ == "__main__":
    test_mcp_initialize_and_tool_call()
    test_mcp_path_boundary_enforcement()
    test_mcp_refusal_and_recovery()
    test_mcp_timeout_handling()
    print("ALL MCP SIMULATOR TESTS PASSED")
