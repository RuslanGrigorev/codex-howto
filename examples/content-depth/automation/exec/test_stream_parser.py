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

if __name__ == "__main__":
    test_successful_stream()
    test_truncated_stream_raises_error()
    test_failed_stream_raises_error()
    test_retry_recovery_stream()
    test_malformed_json_tolerance()
    print("ALL STREAM PARSER TESTS PASSED")
