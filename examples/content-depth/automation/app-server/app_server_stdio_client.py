#!/usr/bin/env python3
"""Клиент протокола JSON-RPC 2.0 для взаимодействия с Codex CLI app-server (ADR-CD-04).

Архитектура:
- BaseJsonRpcTransport: интерфейс транспорта сообщений JSON-RPC 2.0.
- SubprocessStdioTransport: полноценный процессный транспорт поверх потоков stdin/stdout дочернего процесса.
- FixtureStdioTransport: детерминированный in-memory транспорт для модульного тестирования.
- AppServerStdioClient: клиент с конечным автоматом состояний, атомарными переходами и откатом ошибок (rollback).
"""
from __future__ import annotations

import enum
import json
import os
import queue
import subprocess
import sys
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

# UTF-8 reconfigure
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


class ClientState(enum.Enum):
    DISCONNECTED = "DISCONNECTED"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    TURN_IN_PROGRESS = "TURN_IN_PROGRESS"
    CLOSED = "CLOSED"


class JsonRpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(f"JSON-RPC Error {code}: {message}")
        self.code = code
        self.message = message
        self.data = data


class AppServerProtocolError(Exception):
    """Сбой протокола, непредвиденный EOF или недопустимый переход состояния."""
    pass


class AppServerTimeoutError(Exception):
    """Превышение допустимого времени ожидания ответа сервера."""
    pass


@dataclass
class JsonRpcRequest:
    id: int
    method: str
    params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": self.method,
            "params": self.params
        }

    def serialize(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class BaseJsonRpcTransport(ABC):
    """Абстрактный интерфейс транспорта JSON-RPC сообщений."""

    @abstractmethod
    def set_message_handler(self, handler: Callable[[str], None]) -> None:
        """Устанавливает обработчик входящих текстовых строк от сервера."""
        raise NotImplementedError

    @abstractmethod
    def write_message(self, message: str) -> None:
        """Отправляет сериализованную строку запроса серверу."""
        raise NotImplementedError

    @abstractmethod
    def is_alive(self) -> bool:
        """Проверяет работоспособность и доступность транспорта."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Корректно закрывает соединение и освобождает ресурсы."""
        raise NotImplementedError


class SubprocessStdioTransport(BaseJsonRpcTransport):
    """Полноценный транспорт на базе дочернего процесса со stdio-каналами (ADR-CD-04)."""

    def __init__(self, command: list[str], cwd: Optional[Path] = None, env: Optional[dict[str, str]] = None):
        self.command = command
        self.cwd = cwd
        self.env = env or dict(os.environ)
        self.env.setdefault("PYTHONUTF8", "1")
        self.env.setdefault("PYTHONIOENCODING", "utf-8")

        self._handler: Optional[Callable[[str], None]] = None
        self._proc: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._is_closed = False
        self._lock = threading.Lock()

        self._start_process()

    def _start_process(self) -> None:
        self._proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            cwd=str(self.cwd) if self.cwd else None,
            env=self.env,
            bufsize=1
        )
        self._reader_thread = threading.Thread(target=self._read_stdout_loop, daemon=True)
        self._reader_thread.start()

    def _read_stdout_loop(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        try:
            for line in self._proc.stdout:
                if self._handler and line:
                    self._handler(line)
        except Exception:
            pass
        finally:
            self._is_closed = True

    def set_message_handler(self, handler: Callable[[str], None]) -> None:
        self._handler = handler

    def write_message(self, message: str) -> None:
        if not self.is_alive():
            raise AppServerProtocolError("Невозможно отправить сообщение: процесс app-server завершён (EOF)")
        assert self._proc is not None and self._proc.stdin is not None
        try:
            with self._lock:
                self._proc.stdin.write(message + "\n")
                self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            self._is_closed = True
            raise AppServerProtocolError(f"Ошибка записи в stdin процесса: {exc}") from exc

    def is_alive(self) -> bool:
        if self._is_closed or self._proc is None:
            return False
        return self._proc.poll() is None

    def close(self) -> None:
        self._is_closed = True
        if self._proc is not None:
            try:
                if self._proc.stdin:
                    self._proc.stdin.close()
                self._proc.terminate()
                self._proc.wait(timeout=2.0)
            except Exception:
                self._proc.kill()


class FixtureStdioTransport(BaseJsonRpcTransport):
    """Детерминированный in-memory транспорт для автономных тестов."""

    def __init__(self):
        self._handler: Optional[Callable[[str], None]] = None
        self._is_alive = True
        self.sent_messages: list[str] = []
        self._responses: dict[str, dict[str, Any]] = {}

    def register_response(self, method: str, result: Optional[dict[str, Any]] = None, error: Optional[dict[str, Any]] = None):
        self._responses[method] = {"result": result, "error": error}

    def set_message_handler(self, handler: Callable[[str], None]) -> None:
        self._handler = handler

    def write_message(self, message: str) -> None:
        if not self._is_alive:
            raise AppServerProtocolError("Транспорт закрыт")
        self.sent_messages.append(message)
        req = json.loads(message)
        req_id = req.get("id")
        method = req.get("method")

        if method in self._responses:
            data = self._responses[method]
            resp = {"jsonrpc": "2.0", "id": req_id}
            if data["error"]:
                resp["error"] = data["error"]
            else:
                resp["result"] = data["result"]
            if self._handler:
                self._handler(json.dumps(resp))

    def is_alive(self) -> bool:
        return self._is_alive

    def close(self) -> None:
        self._is_alive = False


class AppServerStdioClient:
    """Клиент с конечным автоматом состояний, атомарными переходами и откатом при сбоях."""

    def __init__(
        self,
        transport: Optional[BaseJsonRpcTransport] = None,
        write_fn: Optional[Callable[[str], None]] = None,
        timeout: float = 5.0
    ):
        if transport is not None:
            self.transport = transport
        elif write_fn is not None:
            # Обёртка обратной совместимости для write_fn
            class CallbackTransport(BaseJsonRpcTransport):
                def __init__(self, fn):
                    self.fn = fn
                    self._alive = True
                    self._handler = None
                def set_message_handler(self, h): self._handler = h
                def write_message(self, m): self.fn(m)
                def is_alive(self): return self._alive
                def close(self): self._alive = False

            self.transport = CallbackTransport(write_fn)
        else:
            self.transport = FixtureStdioTransport()

        self.default_timeout = timeout
        self.state = ClientState.DISCONNECTED
        self._next_id = 1
        self._pending_requests: dict[int, queue.Queue] = {}
        self._active_thread_id: Optional[str] = None
        self._lock = threading.Lock()

        self.transport.set_message_handler(self.handle_incoming_message)

    def handle_incoming_message(self, raw_line: str) -> Optional[dict[str, Any]]:
        raw_line = raw_line.strip()
        if not raw_line:
            return None
        msg = json.loads(raw_line)
        if msg.get("jsonrpc") != "2.0":
            raise AppServerProtocolError(f"Неподдерживаемая версия протокола: {msg.get('jsonrpc')}")

        req_id = msg.get("id")
        if req_id is not None:
            with self._lock:
                q = self._pending_requests.pop(req_id, None)
            if q is not None:
                q.put(msg)
        return msg

    def send_request(self, method: str, params: dict[str, Any], timeout: Optional[float] = None) -> Any:
        tout = timeout or self.default_timeout
        with self._lock:
            req_id = self._next_id
            self._next_id += 1
            resp_q: queue.Queue = queue.Queue()
            self._pending_requests[req_id] = resp_q

        req = JsonRpcRequest(id=req_id, method=method, params=params)
        self.transport.write_message(req.serialize())

        try:
            resp = resp_q.get(timeout=tout)
        except queue.Empty:
            with self._lock:
                self._pending_requests.pop(req_id, None)
            raise AppServerTimeoutError(f"Тайм-аут ожидания ответа на метод '{method}' ({tout}s)")

        if "error" in resp and resp["error"] is not None:
            err = resp["error"]
            raise JsonRpcError(code=err.get("code", -32000), message=err.get("message", "Unknown error"), data=err.get("data"))

        return resp.get("result")

    def initialize(self, client_name: str = "CourseClient", version: str = "1.0") -> dict[str, Any]:
        """Инициализация с гарантированным откатом состояния при сбое (Finding 3)."""
        if self.state != ClientState.DISCONNECTED:
            raise AppServerProtocolError(f"Невозможно инициализировать из состояния {self.state.value}")

        self.state = ClientState.INITIALIZING
        try:
            result = self.send_request("initialize", {
                "clientInfo": {"name": client_name, "version": version},
                "capabilities": {}
            })
            self.state = ClientState.READY
            return result
        except Exception:
            # Атомарный откат в исходное состояние DISCONNECTED при ошибке инициализации
            self.state = ClientState.DISCONNECTED
            raise

    def create_thread(self, workspace_path: str) -> str:
        if self.state != ClientState.READY:
            raise AppServerProtocolError(f"Клиент должен быть в состоянии READY (текущее: {self.state.value})")
        res = self.send_request("thread/create", {"workspace": workspace_path})
        thread_id = res["threadId"]
        self._active_thread_id = thread_id
        return thread_id

    def start_turn(self, prompt: str, timeout: Optional[float] = None) -> dict[str, Any]:
        """Начало turn с возвратом в состояние READY даже при возникновении ошибки."""
        if self.state != ClientState.READY:
            raise AppServerProtocolError(f"Невозможно начать turn: клиент в состоянии {self.state.value}")
        if not self._active_thread_id:
            raise AppServerProtocolError("Нет активного thread. Сначала вызовите create_thread()")

        self.state = ClientState.TURN_IN_PROGRESS
        try:
            result = self.send_request("turn/start", {
                "threadId": self._active_thread_id,
                "prompt": prompt
            }, timeout=timeout)
            return result
        finally:
            self.state = ClientState.READY

    def cancel_turn(self) -> None:
        if self.state != ClientState.TURN_IN_PROGRESS:
            raise AppServerProtocolError(f"Нет активного turn для отмены (текущее состояние: {self.state.value})")
        try:
            self.send_request("turn/cancel", {"threadId": self._active_thread_id})
        finally:
            self.state = ClientState.READY

    def close(self) -> None:
        self.state = ClientState.CLOSED
        self.transport.close()


def main():
    transport = FixtureStdioTransport()
    transport.register_response("initialize", {"serverInfo": {"name": "codex-app-server", "version": "0.160.0"}})
    transport.register_response("thread/create", {"threadId": "th_main_1"})
    transport.register_response("turn/start", {"status": "completed"})

    client = AppServerStdioClient(transport=transport)
    client.initialize()
    th = client.create_thread("/workspace")
    assert th == "th_main_1"
    client.start_turn("Проверь код")
    assert client.state == ClientState.READY
    client.close()
    print("PASS: A04 App-server JSON-RPC client validated")


if __name__ == "__main__":
    main()
