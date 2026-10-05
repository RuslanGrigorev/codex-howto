#!/usr/bin/env python3
"""Модульные проверки клиента JSON-RPC 2.0 app-server."""
import json
from app_server_stdio_client import (
    AppServerStdioClient,
    ClientState,
    JsonRpcError,
    AppServerProtocolError,
    AppServerTimeoutError
)

def test_happy_path():
    def transport(raw: str):
        msg = json.loads(raw)
        rid = msg["id"]
        m = msg["method"]
        if m == "initialize":
            res = {"serverInfo": {"name": "codex", "version": "0.160.0"}}
        elif m == "thread/create":
            res = {"threadId": "th_test_100"}
        elif m == "turn/start":
            res = {"turnId": "turn_1", "status": "done"}
        client.handle_incoming_message(json.dumps({"jsonrpc": "2.0", "id": rid, "result": res}))

    client = AppServerStdioClient(write_fn=transport)
    assert client.state == ClientState.DISCONNECTED
    client.initialize()
    assert client.state == ClientState.READY
    th = client.create_thread("/tmp/project")
    assert th == "th_test_100"
    turn = client.start_turn("Hello")
    assert turn["status"] == "done"
    assert client.state == ClientState.READY

def test_invalid_state_transition():
    client = AppServerStdioClient(write_fn=lambda _: None)
    try:
        client.create_thread("/tmp/project")
        assert False, "Ожидалось исключение AppServerProtocolError"
    except AppServerProtocolError:
        pass

def test_jsonrpc_error_handling():
    def transport(raw: str):
        msg = json.loads(raw)
        err = {"code": -32601, "message": "Method not found"}
        client.handle_incoming_message(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "error": err}))

    client = AppServerStdioClient(write_fn=transport)
    try:
        client.initialize()
        assert False, "Ожидалось исключение JsonRpcError"
    except JsonRpcError as exc:
        assert exc.code == -32601
        assert "Method not found" in str(exc)

def test_timeout_handling():
    # Транспорт, который ничего не возвращает
    client = AppServerStdioClient(write_fn=lambda _: None, timeout=0.1)
    try:
        client.initialize()
        assert False, "Ожидалось исключение AppServerTimeoutError"
    except AppServerTimeoutError:
        pass

if __name__ == "__main__":
    test_happy_path()
    test_invalid_state_transition()
    test_jsonrpc_error_handling()
    test_timeout_handling()
    print("ALL A04 APP-SERVER TESTS PASSED")
