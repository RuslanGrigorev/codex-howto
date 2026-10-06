#!/usr/bin/env python3
"""Симулятор клиента удалённого подключения и облачных сред для Codex CLI 0.160.0 (A05, ADR-CD-04).

Разделение архитектурных слоёв (Finding 7):
- RemoteAppServerAdapter: подключение к удалённому app-server через SSH/TLS туннель или loopback.
- CloudWorkerAdapter: подключение к облачным воркерам с обязательной проверкой Cloud Entitlement и пошаговым diff/test workflow.
- RemoteClientSimulator: совместимый фасад для интеграционных сценариев.
"""
from __future__ import annotations

import enum
import json
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

# UTF-8 reconfigure
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


class RemoteState(enum.Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    AUTHENTICATED = "AUTHENTICATED"
    DIFF_RETRIEVED = "DIFF_RETRIEVED"
    REVIEWING = "REVIEWING"
    APPLYING_DIFF = "APPLYING_DIFF"
    TESTING_LOCAL = "TESTING_LOCAL"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class RemoteError(Exception):
    """Базовое исключение удалённого подключения."""
    pass


class RemoteAuthError(RemoteError):
    """Ошибка авторизации: неверный или отсутствующий токен."""
    pass


class RemoteUnavailableError(RemoteError):
    """Удалённый сервер недоступен или отклонил соединение."""
    pass


class RemoteTimeoutError(RemoteError):
    """Превышено время ожидания ответа удалённой среды."""
    pass


class CloudEntitlementError(RemoteError):
    """Отсутствует право доступа (entitlement) к Codex Cloud."""
    pass


@dataclass
class RemoteConnectionConfig:
    endpoint: str
    auth_token_env: str = "CODEX_REMOTE_TOKEN"
    tls_verify: bool = True
    timeout: float = 5.0
    use_ssh_tunnel: bool = False
    tunnel_port: int = 2222
    cloud_entitled: bool = True


class BaseRemoteAdapter(ABC):
    @abstractmethod
    def connect(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def execute_task(self, prompt: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError


class RemoteAppServerAdapter(BaseRemoteAdapter):
    """Адаптер для самостоятельного удалённого app-server (SSH tunnel / Loopback)."""

    def __init__(self, config: RemoteConnectionConfig, fixture_mode: str = "success"):
        self.config = config
        self.fixture_mode = fixture_mode
        self.state = RemoteState.DISCONNECTED
        self.session_id: Optional[str] = None

    def connect(self) -> dict[str, Any]:
        self.state = RemoteState.CONNECTING
        if self.fixture_mode == "unavailable":
            self.state = RemoteState.ERROR
            raise RemoteUnavailableError(f"Удалённая среда {self.config.endpoint} недоступна")
        if self.fixture_mode == "timeout":
            self.state = RemoteState.ERROR
            raise RemoteTimeoutError(f"Тайм-аут подключения ({self.config.timeout}s)")

        token = os.environ.get(self.config.auth_token_env)
        if not token or self.fixture_mode == "auth_failed" or token == "invalid_token":
            self.state = RemoteState.ERROR
            raise RemoteAuthError(f"Ошибка авторизации: переменная окружения '{self.config.auth_token_env}' содержит недействительный токен")

        self.state = RemoteState.AUTHENTICATED
        self.session_id = "app_server_sess_42"
        return {"status": "connected", "session_id": self.session_id, "mode": "app_server"}

    def execute_task(self, prompt: str) -> dict[str, Any]:
        if self.state != RemoteState.AUTHENTICATED:
            raise RemoteError(f"Не авторизован: {self.state.value}")
        return {"status": "completed", "output": f"App-server выполнил: {prompt}"}

    def disconnect(self) -> None:
        self.state = RemoteState.DISCONNECTED
        self.session_id = None


class CloudWorkerAdapter(BaseRemoteAdapter):
    """Адаптер для управляемого Codex Cloud с обязательной проверкой прав (ADR-CD-04)."""

    def __init__(self, config: RemoteConnectionConfig, fixture_mode: str = "success"):
        self.config = config
        self.fixture_mode = fixture_mode
        self.state = RemoteState.DISCONNECTED
        self.session_id: Optional[str] = None
        self.workflow_history: list[str] = []

    def connect(self) -> dict[str, Any]:
        self.state = RemoteState.CONNECTING
        if self.fixture_mode == "unavailable":
            self.state = RemoteState.ERROR
            raise RemoteUnavailableError("Codex Cloud API недоступен")
        if self.fixture_mode == "timeout":
            self.state = RemoteState.ERROR
            raise RemoteTimeoutError("Тайм-аут облачного шлюза")

        # 1. Проверка токена
        token = os.environ.get(self.config.auth_token_env)
        if not token or self.fixture_mode == "auth_failed" or token == "invalid_token":
            self.state = RemoteState.ERROR
            raise RemoteAuthError(f"Ошибка авторизации: переменная окружения '{self.config.auth_token_env}' содержит недействительный токен")

        # 2. Строгий гейт прав (Cloud Entitlement)
        if not self.config.cloud_entitled or self.fixture_mode == "no_entitlement":
            self.state = RemoteState.ERROR
            raise CloudEntitlementError(
                "Учётная запись не имеет активной подписки/прав (entitlement) на использование Codex Cloud. "
                "Автономный режим требует локального запуска модели."
            )

        self.state = RemoteState.AUTHENTICATED
        self.session_id = "cloud_worker_sess_99"
        return {"status": "connected", "session_id": self.session_id, "mode": "cloud"}

    def execute_workflow(self, task_description: str) -> dict[str, Any]:
        """Полный цикл работы с облачным воркером: get-diff -> review -> apply -> test."""
        if self.state != RemoteState.AUTHENTICATED:
            raise RemoteError(f"Требуется аутентификация в Cloud: {self.state.value}")

        self.state = RemoteState.DIFF_RETRIEVED
        self.workflow_history.append("get-diff")

        self.state = RemoteState.REVIEWING
        self.workflow_history.append("review")

        self.state = RemoteState.APPLYING_DIFF
        self.workflow_history.append("apply")

        self.state = RemoteState.TESTING_LOCAL
        self.workflow_history.append("local-tests")

        self.state = RemoteState.COMPLETED
        return {
            "status": "completed",
            "session_id": self.session_id,
            "steps": list(self.workflow_history),
            "output": f"Cloud воркер успешно выполнил задачу: {task_description}"
        }

    def execute_task(self, prompt: str) -> dict[str, Any]:
        return self.execute_workflow(prompt)

    def disconnect(self) -> None:
        self.state = RemoteState.DISCONNECTED
        self.session_id = None


class RemoteClientSimulator:
    """Совместимый симулятор клиента для внешних тестов и курса."""

    def __init__(self, config: RemoteConnectionConfig, fixture_mode: str = "success"):
        self.config = config
        self.fixture_mode = fixture_mode
        if "cloud" in config.endpoint.lower():
            self._adapter: BaseRemoteAdapter = CloudWorkerAdapter(config, fixture_mode=fixture_mode)
        else:
            self._adapter = RemoteAppServerAdapter(config, fixture_mode=fixture_mode)

    @property
    def state(self) -> RemoteState:
        return getattr(self._adapter, "state")

    @state.setter
    def state(self, value: RemoteState):
        setattr(self._adapter, "state", value)

    @property
    def session_id(self) -> Optional[str]:
        return getattr(self._adapter, "session_id")

    def connect(self) -> dict[str, Any]:
        return self._adapter.connect()

    def execute_task(self, prompt: str) -> dict[str, Any]:
        return self._adapter.execute_task(prompt)

    def disconnect(self) -> None:
        self._adapter.disconnect()


def main():
    os.environ["CODEX_REMOTE_TOKEN"] = "valid_secret_test_token"
    cfg = RemoteConnectionConfig(endpoint="https://cloud.example.org:443", cloud_entitled=True)
    client = RemoteClientSimulator(cfg, fixture_mode="success")
    res = client.connect()
    assert res["status"] == "connected"
    task_res = client.execute_task("Проверь распределённые тесты")
    assert task_res["status"] == "completed"
    client.disconnect()
    print("PASS: A05 remote and cloud client fixture flow validated")


if __name__ == "__main__":
    main()
