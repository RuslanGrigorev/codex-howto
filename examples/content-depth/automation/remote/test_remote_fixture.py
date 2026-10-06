#!/usr/bin/env python3
"""Тесты клиента удалённого подключения A05: авторизация, недоступность и тайм-ауты (Finding 8)."""
import os
import pytest
from remote_fixture import (
    RemoteClientSimulator,
    RemoteConnectionConfig,
    CloudWorkerAdapter,
    RemoteAuthError,
    RemoteUnavailableError,
    RemoteTimeoutError,
    CloudEntitlementError,
    RemoteState
)

def test_successful_remote_connection():
    os.environ["CODEX_REMOTE_TOKEN"] = "valid_test_token"
    cfg = RemoteConnectionConfig(endpoint="https://cloud.codex.internal:8443")
    client = RemoteClientSimulator(cfg, fixture_mode="success")

    conn = client.connect()
    assert conn["status"] == "connected"
    assert client.state == RemoteState.AUTHENTICATED

    res = client.execute_task("Собери проект")
    assert res["status"] == "completed"
    client.disconnect()
    assert client.state == RemoteState.DISCONNECTED

def test_auth_failure_missing_or_invalid_token():
    # Удаляем токен или выставляем неверный
    if "CODEX_REMOTE_TOKEN" in os.environ:
        del os.environ["CODEX_REMOTE_TOKEN"]

    cfg = RemoteConnectionConfig(endpoint="https://cloud.codex.internal:8443")
    client = RemoteClientSimulator(cfg, fixture_mode="auth_failed")

    try:
        client.connect()
        assert False, "Ожидалось исключение RemoteAuthError"
    except RemoteAuthError as exc:
        assert "недействительный токен" in str(exc)
        assert client.state == RemoteState.ERROR

def test_remote_unavailable():
    os.environ["CODEX_REMOTE_TOKEN"] = "valid_token"
    cfg = RemoteConnectionConfig(endpoint="https://offline-server:8443")
    client = RemoteClientSimulator(cfg, fixture_mode="unavailable")

    try:
        client.connect()
        assert False, "Ожидалось исключение RemoteUnavailableError"
    except RemoteUnavailableError as exc:
        assert "недоступна" in str(exc)
        assert client.state == RemoteState.ERROR

def test_remote_timeout():
    os.environ["CODEX_REMOTE_TOKEN"] = "valid_token"
    cfg = RemoteConnectionConfig(endpoint="https://slow-server:8443", timeout=1.0)
    client = RemoteClientSimulator(cfg, fixture_mode="timeout")

    try:
        client.connect()
        assert False, "Ожидалось исключение RemoteTimeoutError"
    except RemoteTimeoutError as exc:
        assert "Тайм-аут" in str(exc)
        assert client.state == RemoteState.ERROR

def test_cloud_entitlement_rejection():
    """При отсутствии прав доступа к Cloud подключение отвергается (CloudEntitlementError)."""
    os.environ["CODEX_REMOTE_TOKEN"] = "valid_token"
    cfg = RemoteConnectionConfig(endpoint="https://cloud.codex.internal:8443", cloud_entitled=False)
    client = RemoteClientSimulator(cfg)

    try:
        client.connect()
        assert False, "Ожидалось исключение CloudEntitlementError"
    except CloudEntitlementError as exc:
        assert "entitlement" in str(exc).lower() or "подписки" in str(exc).lower()
        assert client.state == RemoteState.ERROR

def test_cloud_stepwise_workflow():
    """Проверка пошагового цикла работы с облачным воркером (get-diff -> review -> apply -> test)."""
    os.environ["CODEX_REMOTE_TOKEN"] = "valid_token"
    cfg = RemoteConnectionConfig(endpoint="https://cloud.codex.internal:8443", cloud_entitled=True)
    adapter = CloudWorkerAdapter(cfg)
    adapter.connect()
    assert adapter.state == RemoteState.AUTHENTICATED

    res = adapter.execute_workflow("Добавь тесты к модулю")
    assert res["status"] == "completed"
    assert res["steps"] == ["get-diff", "review", "apply", "local-tests"]
    assert adapter.state == RemoteState.COMPLETED

if __name__ == "__main__":
    test_successful_remote_connection()
    test_auth_failure_missing_or_invalid_token()
    test_remote_unavailable()
    test_remote_timeout()
    test_cloud_entitlement_rejection()
    test_cloud_stepwise_workflow()
    print("ALL REMOTE FIXTURE TESTS PASSED")
