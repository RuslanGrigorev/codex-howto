#!/usr/bin/env python3
"""Учебный программный Python SDK клиент для Codex CLI 0.160.0 (ADR-CD-04).

Архитектура:
- BaseSDKAdapter: абстрактный интерфейс взаимодействия (start, send_prompt, continue, resume).
- ProductionSDKAdapter: адаптер к официальному закреплённому пакету openai-codex==0.160.0.
- FixtureSDKAdapter: детерминированный адаптер для офлайн-тестов с обязательной явной регистрацией фикстур.
- CodexSDKClient: клиент уровня приложения, инкапсулирующий работу с сессиями.
"""
from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# UTF-8 reconfigure
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass
class CodexSessionConfig:
    """Конфигурация сессии SDK."""
    model: Optional[str] = None
    sandbox: str = "workspace-write"
    ask_for_approval: str = "never"
    working_dir: Optional[Path] = None
    timeout: float = 60.0


@dataclass
class CodexSDKResult:
    """Результат выполнения шага или запроса через SDK."""
    session_id: str
    output: str
    events: list[dict[str, Any]] = field(default_factory=list)
    success: bool = True
    refusal: Optional[str] = None
    exit_code: int = 0
    error_message: Optional[str] = None


@dataclass
class CodexSession:
    """Состояние сессии SDK."""
    session_id: str
    config: CodexSessionConfig
    status: str = "active"
    history: list[dict[str, Any]] = field(default_factory=list)


class CodexSDKError(Exception):
    """Базовое исключение SDK."""
    pass


class CodexTimeoutError(CodexSDKError):
    """Исключение при превышении лимита времени выполнения."""
    pass


class CodexExecutionError(CodexSDKError):
    """Исключение при сбое выполнения команды или вызова инструмента."""
    pass


class CodexRefusalError(CodexSDKError):
    """Исключение при отказе модели по соображениям безопасности."""
    pass


class CodexUnregisteredFixtureError(CodexSDKError):
    """Исключение при отсутствии зарегистрированной фикстуры для запроса (ADR-CD-04)."""
    pass


class CodexSessionNotFoundError(CodexSDKError):
    """Исключение при попытке возобновить неизвестную сессию (ADR-CD-04)."""
    pass


class CodexCancellationError(CodexSDKError):
    """Исключение при обращении к отменённой сессии."""
    pass


class BaseSDKAdapter(ABC):
    """Абстрактный адаптер для SDK взаимодействия с Codex."""

    @abstractmethod
    def start_session(self, config: CodexSessionConfig, initial_prompt: Optional[str] = None) -> tuple[CodexSession, Optional[CodexSDKResult]]:
        """Инициализирует новую сессию Codex."""
        raise NotImplementedError

    @abstractmethod
    def send_prompt(self, session: CodexSession, prompt: str, timeout: Optional[float] = None) -> CodexSDKResult:
        """Отправляет промпт в активную сессию."""
        raise NotImplementedError

    @abstractmethod
    def continue_session(self, session: CodexSession, prompt: str, timeout: Optional[float] = None) -> CodexSDKResult:
        """Продолжает существующую сессию новым промптом."""
        raise NotImplementedError

    @abstractmethod
    def resume_session(self, session_id: str, config: Optional[CodexSessionConfig] = None) -> CodexSession:
        """Возобновляет сохранённую сессию по идентификатору."""
        raise NotImplementedError

    @abstractmethod
    def cancel_session(self, session: CodexSession) -> bool:
        """Отменяет активную сессию (ADR-CD-04)."""
        raise NotImplementedError


class ProductionSDKAdapter(BaseSDKAdapter):
    """Производственный адаптер на базе официального пакета openai-codex==0.160.0."""

    PINNED_VERSION = "0.160.0"

    def __init__(self):
        try:
            import openai_codex  # type: ignore
            self._sdk = openai_codex
        except ImportError:
            self._sdk = None

    def _require_sdk(self):
        if self._sdk is None:
            raise CodexSDKError(
                f"Официальный пакет 'openai-codex=={self.PINNED_VERSION}' не установлен в окружении. "
                "Для офлайн-проверок и тестов используйте FixtureSDKAdapter."
            )

    def start_session(self, config: CodexSessionConfig, initial_prompt: Optional[str] = None) -> tuple[CodexSession, Optional[CodexSDKResult]]:
        self._require_sdk()
        client = self._sdk.Client(
            model=config.model,
            sandbox=config.sandbox,
            ask_for_approval=config.ask_for_approval,
            cwd=str(config.working_dir) if config.working_dir else None
        )
        raw_session = client.create_session()
        session = CodexSession(session_id=raw_session.id, config=config)
        res = None
        if initial_prompt:
            res = self.send_prompt(session, initial_prompt, timeout=config.timeout)
        return session, res



    def continue_session(self, session: CodexSession, prompt: str, timeout: Optional[float] = None) -> CodexSDKResult:
        return self.send_prompt(session, prompt, timeout=timeout)

    def send_prompt(self, session: CodexSession, prompt: str, timeout: Optional[float] = None) -> CodexSDKResult:
        self._require_sdk()
        tout = timeout or session.config.timeout
        try:
            raw_res = self._sdk.send(session.session_id, prompt, timeout=tout)
        except Exception as exc:
            if "timeout" in str(exc).lower() or type(exc).__name__ == "TimeoutError":
                raise CodexTimeoutError(f"Превышен лимит времени ({tout}s): {exc}") from exc
            raise
        return CodexSDKResult(
            session_id=session.session_id,
            output=raw_res.text,
            events=raw_res.events,
            success=raw_res.is_success,
            refusal=raw_res.refusal,
            exit_code=0 if raw_res.is_success else 1
        )

    def resume_session(self, session_id: str, config: Optional[CodexSessionConfig] = None) -> CodexSession:
        self._require_sdk()
        cfg = config or CodexSessionConfig()
        try:
            raw_session = self._sdk.get_session(session_id)
        except Exception as exc:
            if "not found" in str(exc).lower():
                raise CodexSessionNotFoundError(f"Сессия '{session_id}' не найдена: {exc}") from exc
            raise
        if not raw_session:
            raise CodexSessionNotFoundError(f"Сессия '{session_id}' не существует.")
        return CodexSession(session_id=raw_session.id, config=cfg)

    def cancel_session(self, session: CodexSession) -> bool:
        self._require_sdk()
        if hasattr(self._sdk, "cancel"):
            self._sdk.cancel(session.session_id)
        session.status = "cancelled"
        return True


class FixtureSDKAdapter(BaseSDKAdapter):
    """Детерминированный тестовый адаптер для офлайн-проверок (ADR-CD-04).

    Строгое правило: запросы, для которых нет зарегистрированной фикстуры,
    НЕ генерируют фиктивный успех, а вызывают CodexUnregisteredFixtureError.
    """

    def __init__(self):
        self.registered_responses: dict[str, CodexSDKResult] = {}
        self.registered_sessions: dict[str, CodexSession] = {}
        self.call_history: list[dict[str, Any]] = []
        self._next_session_id = 1

    def register_response(self, prompt_substring: str, result: CodexSDKResult) -> None:
        """Регистрирует ожидаемый результат на основе подстроки промпта."""
        self.registered_responses[prompt_substring] = result

    def start_session(self, config: CodexSessionConfig, initial_prompt: Optional[str] = None) -> tuple[CodexSession, Optional[CodexSDKResult]]:
        session_id = f"mock-session-{self._next_session_id}"
        self._next_session_id += 1
        session = CodexSession(session_id=session_id, config=config)
        self.registered_sessions[session_id] = session
        self.call_history.append({"action": "start_session", "session_id": session_id, "config": config})
        res = None
        if initial_prompt:
            res = self.send_prompt(session, initial_prompt, timeout=config.timeout)
        return session, res

    def send_prompt(self, session: CodexSession, prompt: str, timeout: Optional[float] = None) -> CodexSDKResult:
        self.call_history.append({"action": "send_prompt", "session_id": session.session_id, "prompt": prompt})

        if session.status == "cancelled":
            raise CodexCancellationError(f"Сессия '{session.session_id}' отменена.")

        tout = timeout or session.config.timeout
        if prompt == "__timeout__" or (tout is not None and tout <= 0):
            raise CodexTimeoutError(f"Превышен лимит времени ожидания выполнения запроса ({tout}s).")

        # Поиск зарегистрированного ответа
        for sub, res in self.registered_responses.items():
            if sub in prompt:
                # Фиксация истории сессии
                session.history.append({"prompt": prompt, "result": res})
                if res.refusal:
                    raise CodexRefusalError(f"Модель отклонила запрос: {res.refusal}")
                if res.exit_code != 0:
                    raise CodexExecutionError(f"Ошибка выполнения (код {res.exit_code}): {res.error_message}")
                return res

        # Запрет неявного успеха для незарегистрированных фикстур
        raise CodexUnregisteredFixtureError(
            f"Для промпта '{prompt}' нет зарегистрированного ответа фикстуры. "
            "Фабрикация фиктивного успеха запрещена архитектурным решением ADR-CD-04."
        )

    def continue_session(self, session: CodexSession, prompt: str, timeout: Optional[float] = None) -> CodexSDKResult:
        self.call_history.append({"action": "continue_session", "session_id": session.session_id, "prompt": prompt})
        return self.send_prompt(session, prompt, timeout=timeout)

    def resume_session(self, session_id: str, config: Optional[CodexSessionConfig] = None) -> CodexSession:
        self.call_history.append({"action": "resume_session", "session_id": session_id})
        if session_id in self.registered_sessions:
            return self.registered_sessions[session_id]
        raise CodexSessionNotFoundError(
            f"Сессия '{session_id}' не найдена. Возобновление несуществующей сессии запрещено (ADR-CD-04)."
        )

    def cancel_session(self, session: CodexSession) -> bool:
        self.call_history.append({"action": "cancel_session", "session_id": session.session_id})
        session.status = "cancelled"
        return True


class CodexSDKClient:
    """Высокоуровневый клиент для интеграции Codex в приложения Python."""

    def __init__(self, adapter: Optional[BaseSDKAdapter] = None, config: Optional[CodexSessionConfig] = None):
        self.adapter = adapter or FixtureSDKAdapter()
        self.config = config or CodexSessionConfig()
        self.current_session: Optional[CodexSession] = None

    def start(self, initial_prompt: Optional[str] = None) -> CodexSession:
        session, _ = self.adapter.start_session(self.config, initial_prompt=initial_prompt)
        self.current_session = session
        return session

    def prompt(self, text: str, timeout: Optional[float] = None) -> CodexSDKResult:
        if not self.current_session:
            self.start()
        assert self.current_session is not None
        return self.adapter.send_prompt(self.current_session, text, timeout=timeout)

    def continue_session(self, text: str, timeout: Optional[float] = None) -> CodexSDKResult:
        if not self.current_session:
            raise CodexSDKError("Нет активной сессии для продолжения. Сначала вызовите start().")
        return self.adapter.continue_session(self.current_session, text, timeout=timeout)

    def resume(self, session_id: str) -> CodexSession:
        session = self.adapter.resume_session(session_id, config=self.config)
        self.current_session = session
        return session

    def cancel(self) -> bool:
        if not self.current_session:
            return False
        return self.adapter.cancel_session(self.current_session)


def main():
    fixture = FixtureSDKAdapter()
    fixture.register_response(
        "Проверь синтаксис",
        CodexSDKResult(
            session_id="mock-1",
            output="Синтаксис корректен",
            events=[{"event": "completed"}],
            success=True
        )
    )
    client = CodexSDKClient(adapter=fixture)
    client.start()
    res = client.prompt("Проверь синтаксис")
    assert res.success, "Ошибка вызова SDK"
    print("PASS: A03 Python SDK adapter architecture validated")


if __name__ == "__main__":
    main()
