#!/usr/bin/env python3
"""Тесты протокола JSON-RPC 2.0 app-server, stdio-транспорта и атомарных переходов (Finding 3)."""
import sys
from pathlib import Path

from app_server_stdio_client import (
    AppServerStdioClient,
    ClientState,
    FixtureStdioTransport,
    SubprocessStdioTransport,
    JsonRpcError,
    AppServerProtocolError,
    AppServerTimeoutError
)

APP_SERVER_DIR = Path(__file__).parent
MOCK_SERVER_SCRIPT = APP_SERVER_DIR / "scripts" / "mock_app_server.py"

def test_happy_path_fixture():
    transport = FixtureStdioTransport()
    transport.register_response("initialize", {"serverInfo": {"name": "codex", "version": "0.160.0"}})
    transport.register_response("thread/create", {"threadId": "th_fixture_1"})
    transport.register_response("turn/start", {"turnId": "turn_1", "status": "done"})

    client = AppServerStdioClient(transport=transport)
    assert client.state == ClientState.DISCONNECTED

    client.initialize()
    assert client.state == ClientState.READY

    th = client.create_thread("/tmp/project")
    assert th == "th_fixture_1"

    turn = client.start_turn("Hello")
    assert turn["status"] == "done"
    assert client.state == ClientState.READY

def test_subprocess_stdio_transport():
    """Тест реального дочернего процесса через SubprocessStdioTransport."""
    transport = SubprocessStdioTransport([sys.executable, "-X", "utf8", str(MOCK_SERVER_SCRIPT)])
    client = AppServerStdioClient(transport=transport, timeout=3.0)

    try:
        init_res = client.initialize()
        assert init_res["serverInfo"]["name"] == "mock-codex-server"
        assert client.state == ClientState.READY

        th_id = client.create_thread("/workspace")
        assert th_id == "th_proc_1"

        turn_res = client.start_turn("Проанализируй код")
        assert turn_res["status"] == "completed"
        assert client.state == ClientState.READY
    finally:
        client.close()
        assert not transport.is_alive()

def test_initialize_failure_and_state_rollback():
    """Проверка требования Finding 3: при ошибке initialize состояние откатывается в DISCONNECTED, позволяя retry."""
    transport = FixtureStdioTransport()
    # 1. Первая попытка возвращает ошибку JSON-RPC
    transport.register_response("initialize", error={"code": -32001, "message": "Server temporarily busy"})

    client = AppServerStdioClient(transport=transport, timeout=1.0)
    assert client.state == ClientState.DISCONNECTED

    try:
        client.initialize()
        assert False, "Ожидалось исключение JsonRpcError"
    except JsonRpcError as exc:
        assert exc.code == -32001

    # Состояние ОБЯЗАНО откатиться в DISCONNECTED, а не оставаться в INITIALIZING
    assert client.state == ClientState.DISCONNECTED, f"Состояние должно откатиться в DISCONNECTED, текущее: {client.state}"

    # 2. Повторная попытка (retry) после восстановления сервера должна быть успешной
    transport.register_response("initialize", result={"serverInfo": {"name": "codex", "version": "0.160.0"}})
    retry_res = client.initialize()
    assert retry_res["serverInfo"]["name"] == "codex"
    assert client.state == ClientState.READY

def test_timeout_rollback_and_retry():
    """Проверка отката при тайм-ауте initialize."""
    transport = FixtureStdioTransport()
    # Не регистрируем ответ на initialize -> сработает тайм-аут
    client = AppServerStdioClient(transport=transport, timeout=0.1)

    try:
        client.initialize()
        assert False, "Ожидалось исключение AppServerTimeoutError"
    except AppServerTimeoutError:
        pass

    assert client.state == ClientState.DISCONNECTED

    # Регистрируем ответ и пробуем снова
    transport.register_response("initialize", result={"serverInfo": {"name": "codex", "version": "0.160.0"}})
    client.default_timeout = 2.0
    client.initialize()
    assert client.state == ClientState.READY

def test_eof_detection_on_process_termination():
    """Проверка обнаружения завершения процесса (EOF) в SubprocessStdioTransport."""
    transport = SubprocessStdioTransport([sys.executable, "-X", "utf8", str(MOCK_SERVER_SCRIPT)])
    client = AppServerStdioClient(transport=transport, timeout=2.0)

    client.initialize()
    assert client.state == ClientState.READY

    # Отправляем команду завершения процесса
    try:
        client.send_request("exit_eof", {})
    except Exception:
        pass

    # Даём процессу завершиться
    import time
    time.sleep(0.2)
    assert not transport.is_alive()

    # Попытка нового запроса должна вызвать AppServerProtocolError из-за мертвого процесса
    try:
        client.send_request("thread/create", {"workspace": "/tmp"})
        assert False, "Ожидалось исключение AppServerProtocolError при отправке в мёртвый процесс"
    except AppServerProtocolError as exc:
        assert "EOF" in str(exc) or "завершён" in str(exc)

    client.close()

if __name__ == "__main__":
    test_happy_path_fixture()
    test_subprocess_stdio_transport()
    test_initialize_failure_and_state_rollback()
    test_timeout_rollback_and_retry()
    test_eof_detection_on_process_termination()
    print("ALL APP-SERVER TESTS PASSED")
