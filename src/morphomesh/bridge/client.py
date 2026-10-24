"""
MorphoMesh: Blender Socket Client Transport.

Handles TCP socket connection, NDJSON streaming framing, timeout management,
and response unpacking for communication with the Blender socket server.
"""

from __future__ import annotations

import json
import logging
import re
import socket
import uuid
from typing import Any, Dict, Optional

from morphomesh.bridge.constants import (
    BUFFER_SIZE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    SENTINEL_END,
    SENTINEL_START,
)
from morphomesh.bridge.validator import BlenderExecutionError

logger = logging.getLogger("morphomesh.bridge.client")


class BlenderSocketClient:
    """
    Client for bidirectional NDJSON-based TCP socket communication
    with the Blender interactive listener.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        socket_timeout: float = 2.0,
    ):
        self.host = host
        self.port = port
        self.socket_timeout = socket_timeout

    def is_connected(self) -> bool:
        """Probe whether the Blender Addon TCP socket server is actively listening."""
        try:
            with socket.create_connection((self.host, self.port), timeout=0.25):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def send_request(
        self,
        method: str,
        params: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Transmit request to the interactive Blender socket server."""
        req_id = f"req-{uuid.uuid4().hex[:8]}"
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "type": method,
            "params": params,
        }
        # NDJSON streaming: ensure request is terminated with newline b"\n"
        encoded = json.dumps(payload).encode("utf-8") + b"\n"

        sock = None
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.socket_timeout)
            sock.settimeout(timeout)
            sock.sendall(encoded)

            buffer = b""
            response = None
            while True:
                try:
                    chunk = sock.recv(BUFFER_SIZE)
                except (socket.timeout, TimeoutError) as e:
                    raise TimeoutError(f"Socket request timed out after {timeout}s for method '{method}': {e}") from e

                if not chunk:
                    # Remote closed connection (EOF); parse remaining buffer if present
                    if buffer.strip():
                        try:
                            response = json.loads(buffer.decode("utf-8"))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            pass
                    break

                buffer += chunk
                # Line-buffered NDJSON framing: split on newline delimiter
                if b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.strip()
                    if line:
                        try:
                            response = json.loads(line.decode("utf-8"))
                            break
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue

            if not response:
                raise BlenderExecutionError(f"Empty or malformed response received from Blender socket for method '{method}'.")

            if response.get("status") == "error":
                err_msg = response.get("message") or response.get("error", {}).get("message", "Unknown error")
                raise BlenderExecutionError(
                    f"Blender Socket Error: {err_msg}",
                    details=response,
                )
            if "error" in response:
                err = response["error"]
                err_msg = err.get("message", "Unknown error") if isinstance(err, dict) else str(err)
                err_code = err.get("code") if isinstance(err, dict) else None
                raise BlenderExecutionError(
                    f"Blender Socket Error: [{err_code}] {err_msg}",
                    details=err.get("data", {}) if isinstance(err, dict) else {},
                )

            # JSON-RPC 2.0 result unwrap or direct dictionary fallback
            res = response.get("result") if response.get("result") is not None else response
            # If the socket server is blender-mcp, result might be {"executed": true, "result": "..."}
            if isinstance(res, dict) and "executed" in res and "result" in res:
                out_str = res["result"]
                # Check for MORPHOMESH_RESULT or sentinel JSON
                m = re.search(r"MORPHOMESH_RESULT:(\{.*?\})", out_str)
                if not m:
                    m = re.search(
                        rf"{re.escape(SENTINEL_START)}\s*({{.*?}})\s*{re.escape(SENTINEL_END)}",
                        out_str,
                        re.DOTALL,
                    )
                if m:
                    try:
                        return json.loads(m.group(1))
                    except json.JSONDecodeError:
                        pass
                return res
            return res
        finally:
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    sock.close()
                except OSError:
                    pass


__all__ = ["BlenderSocketClient"]
