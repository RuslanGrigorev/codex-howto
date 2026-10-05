#!/usr/bin/env python3
"""Клиент протокола JSON-RPC 2.0 для взаимодействия с Codex CLI app-server."""
from __future__ import annotations
import enum
import json
import queue
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

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
    """Сбой протокола или недопустимый переход состояния."""
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

class AppServerStdioClient:
    """Клиент с конечным автоматом состояний и поддержкой JSON-RPC 2.0."""

    def __init__(self, write_fn: Callable[[str], None], timeout: float = 5.0):
        self.write_fn = write_fn
        self.default_timeout = timeout
        self.state = ClientState.DISCONNECTED
        self._next_id = 1
        self._pending_requests: dict[int, queue.Queue] = {}
        self._active_thread_id: Optional[str] = None
        self._lock = threading.Lock()

    def handle_incoming_message(self, raw_line: str) -> Optional[dict[str, Any]]:
        """Обрабатывает входящую строку от app-server (ответ или уведомление)."""
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
        self.write_fn(req.serialize())

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
        if self.state != ClientState.DISCONNECTED:
            raise AppServerProtocolError(f"Невозможно инициализировать из состояния {self.state.value}")
        self.state = ClientState.INITIALIZING
        result = self.send_request("initialize", {
            "clientInfo": {"name": client_name, "version": version},
            "capabilities": {}
        })
        self.state = ClientState.READY
        return result

    def create_thread(self, workspace_path: str) -> str:
        if self.state != ClientState.READY:
            raise AppServerProtocolError(f"Клиент должен быть в состоянии READY (текущее: {self.state.value})")
        res = self.send_request("thread/create", {"workspace": workspace_path})
        thread_id = res["threadId"]
        self._active_thread_id = thread_id
        return thread_id

    def start_turn(self, prompt: str) -> dict[str, Any]:
        if self.state != ClientState.READY:
            raise AppServerProtocolError(f"Невозможно начать turn: клиент в состоянии {self.state.value}")
        if not self._active_thread_id:
            raise AppServerProtocolError("Нет активного thread. Сначала вызовите create_thread()")

        self.state = ClientState.TURN_IN_PROGRESS
        try:
            result = self.send_request("turn/start", {
                "threadId": self._active_thread_id,
                "prompt": prompt
            })
            return result
        finally:
            self.state = ClientState.READY

    def cancel_turn(self) -> None:
        if self.state != ClientState.TURN_IN_PROGRESS:
            raise AppServerProtocolError(f"Нет активного turn для отмены (текущее состояние: {self.state.value})")
        self.send_request("turn/cancel", {"threadId": self._active_thread_id})
        self.state = ClientState.READY

    def close(self) -> None:
        self.state = ClientState.CLOSED

def main():
    def mock_server_transport(raw: str):
        req = json.loads(raw)
        req_id = req.get("id")
        method = req.get("method")
        if method == "initialize":
            res = {"serverInfo": {"name": "codex-app-server", "version": "0.160.0"}}
        elif method == "thread/create":
            res = {"threadId": "th_demo_1"}
        elif method == "turn/start":
            res = {"status": "completed"}
        elif method == "turn/cancel":
            res = {"status": "cancelled"}
        else:
            res = {}
        client.handle_incoming_message(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": res}))

    client = AppServerStdioClient(write_fn=mock_server_transport)
    client.initialize()
    th = client.create_thread("/workspace")
    assert th == "th_demo_1"
    client.start_turn("Проверь код")
    assert client.state == ClientState.READY
    print("PASS: A04 App-server JSON-RPC client validated")

if __name__ == "__main__":
    main()
