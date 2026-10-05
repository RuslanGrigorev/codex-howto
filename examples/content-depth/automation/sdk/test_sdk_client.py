#!/usr/bin/env python3
"""Тесты для учебного SDK-клиента Codex CLI."""
from pathlib import Path
from sdk_client import (
    CodexSDKClient,
    FixtureSDKTransport,
    CodexResult,
    CodexExecutionError,
    CodexTimeoutError,
)

def test_successful_execution():
    fixture = FixtureSDKTransport()
    client = CodexSDKClient(Path("."), transport=fixture)
    res = client.run_prompt("Успешный промпт")
    assert res.success is True
    assert res.exit_code == 0
    assert len(fixture.call_history) == 1
    assert "codex" in fixture.call_history[0]["command"]

def test_model_refusal_raises_error():
    fixture = FixtureSDKTransport()
    fixture.register_response(
        "Опасный",
        CodexResult(
            exit_code=0,
            output='{"type": "refusal", "message": "Запрос нарушает политику безопасности"}\n',
            events=[{"type": "refusal", "message": "Запрос нарушает политику безопасности"}],
            success=False,
            refusal="Запрос нарушает политику безопасности"
        )
    )
    client = CodexSDKClient(Path("."), transport=fixture)
    try:
        client.run_prompt("Опасный запрос")
        assert False, "Ожидалось исключение CodexExecutionError"
    except CodexExecutionError as exc:
        assert "отклонила запрос" in str(exc)

def test_nonzero_exit_code_raises_error():
    fixture = FixtureSDKTransport()
    fixture.register_response(
        "Сбой",
        CodexResult(
            exit_code=2,
            output="",
            events=[],
            success=False,
            error_message="SyntaxError in arguments"
        )
    )
    client = CodexSDKClient(Path("."), transport=fixture)
    try:
        client.run_prompt("Сбой")
        assert False, "Ожидалось исключение CodexExecutionError"
    except CodexExecutionError as exc:
        assert "Сбой выполнения" in str(exc)

if __name__ == "__main__":
    test_successful_execution()
    test_model_refusal_raises_error()
    test_nonzero_exit_code_raises_error()
    print("ALL A03 SDK TESTS PASSED")
