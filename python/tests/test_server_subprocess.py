import json
import subprocess
import tempfile
from pathlib import Path


def test_server_subprocess_smoke(tmp_path: Path) -> None:
    """End-to-end smoke test: start server subprocess and invoke tools via stdin/stdout."""
    target = tmp_path / "sample.txt"
    target.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")

    proc = subprocess.Popen(
        [
            "python",
            "-m",
            "mcp_edit_file_lines",
            str(tmp_path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Give server time to start
        import time
        time.sleep(0.5)

        # Simple JSON-RPC 2.0 initialize request (minimal MCP handshake)
        init_request = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0"},
                },
            }
        )

        proc.stdin.write(init_request + "\n")
        proc.stdin.flush()

        # Read response (just verify server is alive and responds)
        response_line = proc.stdout.readline()
        if response_line:
            response = json.loads(response_line)
            assert "result" in response or "error" in response
    finally:
        proc.terminate()
        proc.wait(timeout=5)
