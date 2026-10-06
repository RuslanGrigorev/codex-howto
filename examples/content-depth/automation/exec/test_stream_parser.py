#!/usr/bin/env python3
"""Тесты потокового парсера JSONL: валидация успешных, оборванных, аварийных и retry сценариев (Finding 8)."""
import pytest
from pathlib import Path

from batch_exec import (
    JSONLStreamParser,
    StreamParsingError,
    TruncatedStreamError,
    ExecutionFailedError
)

EXEC_DIR = Path(__file__).parent
FIXTURES_DIR = EXEC_DIR / "fixtures"

def test_successful_stream():
    sample_file = EXEC_DIR / "sample_output.jsonl"
    parser = JSONLStreamParser()
    summary = parser.parse_stream(sample_file.read_text(encoding="utf-8").splitlines())

    assert summary.is_completed is True
    assert summary.failure_event is None
    assert len(summary.tool_calls) == 1
    assert summary.terminal_event["status"] == "completed"

def test_truncated_stream_raises_error():
    trunc_file = FIXTURES_DIR / "truncated_stream.jsonl"
    parser = JSONLStreamParser()

    try:
        parser.parse_stream(trunc_file.read_text(encoding="utf-8").splitlines())
        assert False, "Ожидалось исключение TruncatedStreamError"
    except TruncatedStreamError as exc:
        assert "Поток оборван" in str(exc)

def test_failed_stream_raises_error():
    failed_file = FIXTURES_DIR / "failed_stream.jsonl"
    parser = JSONLStreamParser()

    try:
        parser.parse_stream(failed_file.read_text(encoding="utf-8").splitlines())
        assert False, "Ожидалось исключение ExecutionFailedError"
    except ExecutionFailedError as exc:
        assert "сбой исполнения" in str(exc)
        assert "turn.failed" in str(exc)

def test_retry_recovery_stream():
    retry_file = FIXTURES_DIR / "retry_stream.jsonl"
    parser = JSONLStreamParser()
    summary = parser.parse_stream(retry_file.read_text(encoding="utf-8").splitlines())

    assert summary.is_completed is True
    assert len(summary.retries) == 1
    assert summary.retries[0]["attempt"] == 1
    assert len(summary.tool_calls) == 2

def test_malformed_json_tolerance():
    lines = [
        '{"event": "turn_start", "turn": 1}',
        'not valid json line at all',
        '{"event": "turn_complete", "status": "completed"}'
    ]
    parser = JSONLStreamParser()
    summary = parser.parse_stream(lines)

    assert summary.is_completed is True
    assert summary.malformed_lines == 1
    assert summary.valid_events == 2

def test_fixture_runner_nonzero_exit_code():
    from batch_exec import FixtureExecRunner, ExecResult, StreamParseSummary
    runner = FixtureExecRunner()
    runner.register_scenario(
        "fail",
        ExecResult(
            exit_code=2,
            stdout_events=[],
            stderr="Flag error: unknown argument --bad-flag",
            summary=StreamParseSummary(),
            success=False,
            error_message="Execution failed with exit code 2"
        )
    )
    res = runner.run(["--bad-flag"], "fail prompt")
    assert res.exit_code == 2
    assert res.success is False
    assert "unknown argument" in res.stderr

def test_fixture_runner_cancellation():
    from batch_exec import FixtureExecRunner
    runner = FixtureExecRunner()
    runner.cancel()
    res = runner.run([], "any prompt")
    assert res.is_cancelled is True
    assert res.exit_code == 130
    assert "cancelled" in res.stderr.lower()

def test_fixture_runner_timeout():
    from batch_exec import FixtureExecRunner
    runner = FixtureExecRunner()
    res = runner.run([], "prompt", timeout=0.0)
    assert res.is_timeout is True
    assert res.exit_code == 124

def test_last_assistant_message_extraction():
    parser = JSONLStreamParser()
    lines = [
        '{"event": "turn_start"}',
        '{"event": "item.completed", "text": "Финальный структурированный вывод"}',
        '{"event": "turn_complete", "status": "completed"}'
    ]
    summary = parser.parse_stream(lines)
    assert summary.last_assistant_message == "Финальный структурированный вывод"

if __name__ == "__main__":
    test_successful_stream()
    test_truncated_stream_raises_error()
    test_failed_stream_raises_error()
    test_retry_recovery_stream()
    test_malformed_json_tolerance()
    test_fixture_runner_nonzero_exit_code()
    test_fixture_runner_cancellation()
    test_fixture_runner_timeout()
    test_last_assistant_message_extraction()
    print("ALL STREAM PARSER TESTS PASSED")
