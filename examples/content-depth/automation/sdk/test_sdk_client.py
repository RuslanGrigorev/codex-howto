#!/usr/bin/env python3
"""Тесты для архитектуры SDK-адаптера A03 (ADR-CD-04)."""
import pytest
from pathlib import Path
from sdk_client import (
    CodexSDKClient,
    CodexSessionConfig,
    CodexSDKResult,
    FixtureSDKAdapter,
    ProductionSDKAdapter,
    CodexSDKError,
    CodexRefusalError,
    CodexExecutionError,
    CodexUnregisteredFixtureError,
)

def test_successful_fixture_interaction():
    fixture = FixtureSDKAdapter()
    fixture.register_response(
        "Успешный промпт",
        CodexSDKResult(
            session_id="test-session",
            output="Результат успешен",
            events=[{"event": "completed"}],
            success=True
        )
    )
    client = CodexSDKClient(adapter=fixture)
    session = client.start()
    assert session.session_id.startswith("mock-session-")

    res = client.prompt("Успешный промпт")
    assert res.success is True
    assert res.output == "Результат успешен"

def test_unregistered_prompt_strictly_rejected():
    """Проверка запрета фабрикации успеха: неизвестный запрос обязан вызывать ошибку."""
    fixture = FixtureSDKAdapter()
    client = CodexSDKClient(adapter=fixture)
    client.start()

    try:
        client.prompt("Случайный неожиданный промпт без фикстуры")
        assert False, "Ожидалось исключение CodexUnregisteredFixtureError"
    except CodexUnregisteredFixtureError as exc:
        assert "Фабрикация фиктивного успеха запрещена" in str(exc)

def test_model_refusal_raises_typed_error():
    fixture = FixtureSDKAdapter()
    fixture.register_response(
        "Опасный",
        CodexSDKResult(
            session_id="test-session",
            output="",
            events=[{"type": "refusal", "message": "Отказ модели"}],
            success=False,
            refusal="Политика безопасности запрещает эту команду"
        )
    )
    client = CodexSDKClient(adapter=fixture)
    client.start()

    try:
        client.prompt("Опасный запрос")
        assert False, "Ожидалось исключение CodexRefusalError"
    except CodexRefusalError as exc:
        assert "Политика безопасности запрещает" in str(exc)

def test_execution_failure_raises_typed_error():
    fixture = FixtureSDKAdapter()
    fixture.register_response(
        "Сбой",
        CodexSDKResult(
            session_id="test-session",
            output="",
            events=[],
            success=False,
            exit_code=1,
            error_message="Runtime error in code"
        )
    )
    client = CodexSDKClient(adapter=fixture)
    client.start()

    try:
        client.prompt("Сбой")
        assert False, "Ожидалось исключение CodexExecutionError"
    except CodexExecutionError as exc:
        assert "Runtime error in code" in str(exc)

def test_continue_and_resume_session():
    fixture = FixtureSDKAdapter()
    fixture.register_response(
        "Шаг 1",
        CodexSDKResult(session_id="s1", output="Шаг 1 готов", success=True)
    )
    fixture.register_response(
        "Шаг 2",
        CodexSDKResult(session_id="s1", output="Шаг 2 готов", success=True)
    )

    client = CodexSDKClient(adapter=fixture)
    session = client.start()
    sid = session.session_id

    client.prompt("Шаг 1")
    res2 = client.continue_session("Шаг 2")
    assert res2.output == "Шаг 2 готов"

    # Возобновление сессии
    resumed = client.resume(sid)
    assert resumed.session_id == sid

def test_production_adapter_offline_boundary():
    """В офлайн среде ProductionSDKAdapter явно требует openai-codex==0.160.0."""
    prod = ProductionSDKAdapter()
    if prod._sdk is None:
        try:
            prod.start_session(CodexSessionConfig())
            assert False, "Ожидалась ошибка отсутствия официального SDK пакета"
        except CodexSDKError as exc:
            assert "openai-codex==0.160.0" in str(exc)

if __name__ == "__main__":
    test_successful_fixture_interaction()
    test_unregistered_prompt_strictly_rejected()
    test_model_refusal_raises_typed_error()
    test_execution_failure_raises_typed_error()
    test_continue_and_resume_session()
    test_production_adapter_offline_boundary()
    print("ALL SDK TESTS PASSED")
