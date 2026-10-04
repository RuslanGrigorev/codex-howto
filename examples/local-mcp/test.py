#!/usr/bin/env python3
"""test.py - Автономный тестовый набор для упражнения local-mcp.

Проверяет:
1. Корректность протокола JSON-RPC 2.0 (initialize, tools/list, tools/call).
2. Защиту от Directory Traversal при вызове инструмента read_file_safe.
3. Корректное чтение разрешенных файлов внутри workspace.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.getcwd())

from mcp_server import LocalMcpHandler


class TestLocalMcpHandler(unittest.TestCase):
    def setUp(self):
        self.temp_root = tempfile.mkdtemp(prefix="mcp_test_ws_")
        self.workspace = Path(self.temp_root) / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)

        # Создаем тестовые файлы
        (self.workspace / "sample.txt").write_text("Hello from inside workspace!", encoding="utf-8")

        # Создаем секретный файл вне workspace
        self.secret_dir = Path(self.temp_root) / "secrets"
        self.secret_dir.mkdir(parents=True, exist_ok=True)
        (self.secret_dir / "secret.key").write_text("SUPER_SECRET_KEY_123", encoding="utf-8")

        self.handler = LocalMcpHandler(self.workspace)

    def tearDown(self):
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_initialize(self):
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = self.handler.handle_request(req)
        self.assertEqual(resp.get("jsonrpc"), "2.0")
        self.assertEqual(resp.get("id"), 1)
        self.assertIn("serverInfo", resp.get("result", {}))

    def test_tools_list(self):
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = self.handler.handle_request(req)
        self.assertEqual(resp.get("jsonrpc"), "2.0")
        self.assertEqual(resp.get("id"), 2)
        tools = resp.get("result", {}).get("tools", [])
        tool_names = [t.get("name") for t in tools]
        self.assertIn("read_file_safe", tool_names)

    def test_safe_read_file(self):
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "read_file_safe",
                "arguments": {"path": "sample.txt"},
            },
        }
        resp = self.handler.handle_request(req)
        self.assertEqual(resp.get("id"), 3)
        res = resp.get("result", {})
        self.assertFalse(res.get("isError", False))
        content = res.get("content", [])
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0].get("text"), "Hello from inside workspace!")

    def test_prevent_directory_traversal(self):
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "read_file_safe",
                "arguments": {"path": "../secrets/secret.key"},
            },
        }
        resp = self.handler.handle_request(req)
        self.assertEqual(resp.get("id"), 4)
        res = resp.get("result", {})
        self.assertTrue(res.get("isError", False), "Чтение за пределами workspace обязано возвращать isError=True")
        text = res.get("content", [{}])[0].get("text", "")
        self.assertNotIn("SUPER_SECRET_KEY_123", text, "Секретный файл вне workspace не должен быть прочитан!")


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestLocalMcpHandler)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
