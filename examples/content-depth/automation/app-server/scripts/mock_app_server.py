#!/usr/bin/env python3
"""Тестовый дочерний процесс, симулирующий stdio app-server для проверки SubprocessStdioTransport."""
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        req_id = req.get("id")
        method = req.get("method")

        if method == "exit_crash":
            # Имитация аварийного завершения процесса (непустой exit code)
            sys.exit(2)
        elif method == "exit_eof":
            # Имитация планового закрытия дескриптора stdout
            break
        elif method == "initialize":
            res = {"serverInfo": {"name": "mock-codex-server", "version": "0.160.0"}}
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": res}) + "\n")
            sys.stdout.flush()
        elif method == "thread/create":
            res = {"threadId": "th_proc_1"}
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": res}) + "\n")
            sys.stdout.flush()
        elif method == "turn/start":
            res = {"status": "completed"}
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": res}) + "\n")
            sys.stdout.flush()
        elif method == "turn/cancel":
            res = {"status": "cancelled"}
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": res}) + "\n")
            sys.stdout.flush()
        else:
            err = {"code": -32601, "message": f"Method {method} not found"}
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "error": err}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
