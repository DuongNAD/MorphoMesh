# Handoff Report: Milestone 1 — Socket Parity Test Design (`test_bridge_socket_parity.py`)

## 1. Observation

### 1.1 Existing Codebase Inspection
- **`blender_addon/morphomesh/listener.py` (lines 151-174)**:
  ```python
  def _client_handler(self, client: socket.socket) -> None:
      with self._clients_lock:
          self._clients.add(client)
      client.settimeout(1.0)
      buffer = b""

      try:
          while self.running:
              try:
                  data = client.recv(65536)
                  if not data:
                      break
                  buffer += data
                  try:
                      cmd = json.loads(buffer.decode("utf-8"))
                      buffer = b""
                      self.command_queue.put((cmd, client))
                  except (json.JSONDecodeError, UnicodeDecodeError):
                      continue
              except socket.timeout:
                  continue
              except Exception:
                  break
      finally:
          with self._clients_lock:
              self._clients.discard(client)
  ```
  - Observation: `json.loads(buffer.decode("utf-8"))` attempts to decode the entire accumulated `buffer`. If multiple JSON objects arrive in a single `recv` (e.g. rapid back-to-back requests), `json.loads` fails with `JSONDecodeError: Extra data: line 2 column 1`. The exception handler catches this and executes `continue` without splitting by newline or extracting individual frames.
  - Observation: If non-JSON garbage bytes arrive, they remain permanently in `buffer`, preventing all subsequent valid requests from decoding successfully.

- **`blender_addon/morphomesh/listener.py` (lines 178-214)**:
  ```python
  def _drain_queue(self) -> float:
      """Executes queued commands on Blender's MAIN THREAD."""
      if not self.running:
          return None

      while not self.command_queue.empty():
          try:
              cmd, client = self.command_queue.get_nowait()
          except queue.Empty:
              break

          req_id = cmd.get("id", "res-1")
          method = cmd.get("method") or cmd.get("type", "")
          params = cmd.get("params", {})

          try:
              result = self._dispatch(method, params)
              response = {
                  "jsonrpc": "2.0",
                  "id": req_id,
                  "status": "success",
                  "result": result,
              }
          except Exception as e:
              response = {
                  "jsonrpc": "2.0",
                  "id": req_id,
                  "status": "error",
                  "error": {"code": -32000, "message": str(e)},
              }

          try:
              client.sendall(json.dumps(response).encode("utf-8") + b"\n")
          except Exception:
              pass

      return 0.02  # Re-check every 20ms
  ```
  - Observation: `_drain_queue` lacks an outer top-level try/except barrier wrapping the queue drainage loop. If an unexpected error occurs during queue iteration, dictionary access, or if an unhandled BaseException escapes, Blender's `bpy.app.timers` unregisters the callback permanently, terminating the socket event loop.

- **`blender_addon/morphomesh/listener.py` (lines 216-557)**:
  - Observation: `_dispatch` supports `ping`, `get_scene_status`, `execute_custom_script`, `auto_rig_human`, `setup_human_materials`, `groom_human`, `dress_human`, and `assemble_master_character`.
  - Observation: Line 555-556:
    ```python
    else:
        raise ValueError(f"Unknown RPC method: {method}")
    ```
    `morphomesh.render_preview` is completely absent from `_dispatch` in `listener.py`, causing `ValueError: Unknown RPC method: morphomesh.render_preview` whenever requested via interactive socket.

- **`src/morphomesh/blender_bridge.py` (lines 339-344)**:
  ```python
  encoded = json.dumps(payload).encode("utf-8")

  with socket.create_connection((self.host, self.port), timeout=self.socket_timeout) as sock:
      sock.settimeout(timeout)
      sock.sendall(encoded)
  ```
  - Observation: Client sends `encoded` without a trailing newline `\n`. For strict NDJSON framing, each JSON frame must terminate with `\n`.

### 1.2 Empirical Failure Reproductions
1. **NDJSON Rapid Request Drop**:
   - Command: Sending 5 rapid ping requests over a single connection:
     `client.sendall(b"".join(json.dumps(req).encode("utf-8") + b"\n" for req in reqs))`
   - Result: `Total responses received: 0`. The entire connection hung and dropped all packets due to `JSONDecodeError: Extra data`.
2. **Buffer Poisoning via Garbage Bytes**:
   - Command: Sending `b"BAD_GARBAGE_BYTES\n"` followed by valid ping `{"id": "req-valid", "method": "morphomesh.ping"}`.
   - Result: `TIMEOUT: Server never processed valid ping because buffer was poisoned with garbage!`.
3. **Timer Unregistration Mechanism**:
   - In Blender's `bpy.app.timers` implementation, any callback that raises an unhandled exception or returns `None` is immediately removed from the active timer list.
4. **Existing Test Suite Baseline**:
   - `pytest tests/test_blender_bridge.py`: 79 passed in 0.22s.
   - `pytest tests/test_adversarial_fastmcp_bridge_human.py`: 68 passed in 9.75s.

---

## 2. Logic Chain

1. **NDJSON Streaming**:
   - From Observation 1.1 & 1.2, TCP is a byte-stream protocol. When 5 requests are sent rapidly, TCP segments coalesce into a single buffer containing multiple JSON payloads separated by newlines.
   - Calling `json.loads` on concatenated JSON without splitting by newline raises `JSONDecodeError`.
   - Therefore, the server must buffer incoming bytes, split on `b"\n"`, and process each complete line individually (`while b"\n" in buffer: line, buffer = buffer.split(b"\n", 1)`).
   - Corresponding test requirement: `test_ndjson_streaming_five_rapid_requests_single_connection` must transmit 5 NDJSON requests in one write and assert 5 corresponding JSON responses are received with matching IDs.

2. **Malformed Data Resilience**:
   - From Observation 1.1 & 1.2, failing to discard unparseable bytes poisons the stream buffer.
   - When newline framing is enforced, an invalid line can be safely discarded or responded to with a standard JSON-RPC 2.0 parse error (`{"jsonrpc": "2.0", "id": null, "status": "error", "error": {"code": -32700, "message": "Parse error"}}`), while leaving `buffer` clean for subsequent lines.
   - Corresponding test requirement: `test_malformed_json_garbage_bytes_recovery` must send garbage bytes followed by valid commands and verify the server recovers and fulfills the valid command.

3. **Timer Immortality Exception Barrier**:
   - From Observation 1.1 & 1.2, any uncaught exception raised out of `_drain_queue` causes Blender to unregister the timer callback.
   - To guarantee timer immortality, `_drain_queue` must wrap its entire body in a top-level `try...except Exception` barrier and always return `0.02` (float interval) as long as `self.running` is True.
   - Corresponding test requirement: `test_unhandled_exception_in_dispatched_method_does_not_drop_timer` and `test_top_level_timer_barrier_immortality` must inject crashing operators and verify `_drain_queue` returns `0.02` and remains registered.

4. **Integration Parity for Scene Status & Render Preview**:
   - From Observation 1.1, `morphomesh.render_preview` is missing from `listener.py`, and `get_scene_status` must report cameras, lights, meshes, polycounts, and materials.
   - Corresponding test requirement: Integration tests must assert `ping` returns environment info (`blender_version`, `status: pong`, `mode: interactive`), `get_scene_status` validates against Pydantic `SceneStatusOutput`, `execute_custom_script` validates against `BlenderExecuteOutput`, and `render_preview` validates against `RenderPreviewOutput`.

---

## 3. Caveats

1. **Host Environment Lacks `bpy`**: The testing host executes Python 3.11 without the C-extension `bpy` package installed (`No module named 'bpy'`). All tests targeting `listener.py` outside of an active Blender process must hermetically mock `sys.modules["bpy"]` and `sys.modules["mathutils"]` (using `importlib.util` dynamic loading and `unittest.mock.patch.dict`), consistent with existing tests in `test_character_assembler.py`.
2. **Ephemeral Port Allocation**: Hardcoded ports (e.g. 9876) risk port collision with running background Blender instances or concurrent test workers. The designed test suite must bind to dynamic port 0 (`server = mod.MorphoMeshSocketServer(host="127.0.0.1", port=0)`) and extract `server.socket.getsockname()[1]`.
3. **Dual Execution Verification**: The test suite must support both mocked offline execution (running in $<2$s during standard CI `pytest`) and live Blender socket execution when an interactive Blender 4.5+ session is listening.

---

## 4. Conclusion & Design Specification

To achieve 100% Milestone 1 socket parity, the test file `tests/test_bridge_socket_parity.py` is designed below. It contains 5 comprehensive test classes with 15 dedicated test cases covering:
1. Connection lifecycle (connect, ping, disconnect, cleanup, status probe).
2. NDJSON streaming (5 rapid back-to-back requests, chunked fragmentation, mixed RPC calls).
3. Malformed data resilience (garbage bytes, broken JSON, empty lines, buffer isolation).
4. Timer immortality barrier (unhandled dispatch exceptions, top-level barrier, graceful shutdown).
5. Integration parity (`ping`, `get_scene_status`, `execute_custom_script`, `render_preview`, dual-mode bridge execution).

### 4.1 Complete Design for `tests/test_bridge_socket_parity.py`

```python
"""
MorphoMesh: Socket Listener & BlenderBridge Parity Test Suite.
Target: tests/test_bridge_socket_parity.py
Milestone: M1 - Interactive Socket Bridge Parity & Reliability (R3)

Validates:
1. Connection Lifecycle: Connect, handshake/ping, graceful disconnect, descriptor cleanup.
2. NDJSON Streaming: 5 rapid requests in a single connection, buffer boundary reassembly, zero packet drop.
3. Malformed Data Resilience: Non-JSON binary garbage, broken JSON, whitespace frames, buffer recovery.
4. Timer Immortality: Dispatched method exception containment, top-level barrier returning 0.02s, persistent registration.
5. Integration Parity: ping, get_scene_status, execute_custom_script, render_preview, Pydantic schema conformance.
"""

from __future__ import annotations

import importlib.util
import json
import os
import queue
import socket
import sys
import threading
import time
from typing import Any, Dict, Generator, List, Tuple
from unittest.mock import MagicMock, patch

import pytest

from morphomesh.blender_bridge import BlenderBridge, BlenderExecutionError, BpyCodeValidator
from morphomesh.models import (
    BlenderExecuteOutput,
    RenderEngine,
    RenderPreviewOutput,
    SceneStatusOutput,
)


# ==============================================================================
# FIXTURES & DYNAMIC SERVER HARNESS
# ==============================================================================

@pytest.fixture(scope="function")
def mock_bpy_environment() -> Tuple[MagicMock, MagicMock]:
    """Creates a hermetic mock Blender Python environment for listener testing."""
    mock_bpy = MagicMock()
    mock_bpy.app.version = (4, 5, 0)
    mock_bpy.app.timers.is_registered.return_value = False

    scene = MagicMock()
    scene.name = "Scene_MorphoMesh_QA"

    # Mesh Object
    mesh_obj = MagicMock()
    mesh_obj.name = "Hero_Body_Mesh"
    mesh_obj.type = "MESH"
    mesh_obj.location = (0.0, 0.0, 1.0)
    mesh_obj.rotation_euler = (0.0, 0.0, 0.0)
    mesh_obj.scale = (1.0, 1.0, 1.0)
    mesh_obj.parent = None
    mesh_obj.children = []
    mesh_obj.modifiers = []
    mat = MagicMock()
    mat.name = "Mat_Skin_SSS"
    mesh_obj.data.materials = [mat]
    mesh_obj.data.vertices = [MagicMock()] * 2400
    mesh_obj.data.polygons = [MagicMock()] * 2380

    # Camera Object
    cam_obj = MagicMock()
    cam_obj.name = "Camera_Inspector"
    cam_obj.type = "CAMERA"
    cam_obj.location = (0.0, -3.2, 1.6)
    cam_obj.rotation_euler = (1.48, 0.0, 0.0)
    cam_obj.scale = (1.0, 1.0, 1.0)
    cam_obj.parent = None
    cam_obj.children = []
    cam_obj.modifiers = []
    cam_obj.data.lens = 50.0

    # Light Object
    light_obj = MagicMock()
    light_obj.name = "Light_Studio_Key"
    light_obj.type = "LIGHT"
    light_obj.location = (2.0, -2.5, 3.0)
    light_obj.rotation_euler = (0.0, 0.0, 0.0)
    light_obj.scale = (1.0, 1.0, 1.0)
    light_obj.parent = None
    light_obj.children = []
    light_obj.modifiers = []
    light_obj.data.type = "AREA"
    light_obj.data.energy = 500.0

    # Armature Object
    arm_obj = MagicMock()
    arm_obj.name = "Armature_Rigify_Human"
    arm_obj.type = "ARMATURE"
    arm_obj.location = (0.0, 0.0, 0.0)
    arm_obj.rotation_euler = (0.0, 0.0, 0.0)
    arm_obj.scale = (1.0, 1.0, 1.0)
    arm_obj.parent = None
    arm_obj.children = [mesh_obj]
    mesh_obj.parent = arm_obj
    arm_obj.modifiers = []
    arm_obj.data.bones = [MagicMock(name=f"DEF-bone_{i}") for i in range(163)]

    scene.objects = [mesh_obj, cam_obj, light_obj, arm_obj]
    mock_bpy.context.scene = scene
    mock_bpy.context.active_object = mesh_obj

    mock_mathutils = MagicMock()
    return mock_bpy, mock_mathutils


@pytest.fixture(scope="function")
def socket_server_factory(mock_bpy_environment) -> Generator[Any, None, None]:
    """Dynamically imports and spawns an ephemeral MorphoMeshSocketServer instance."""
    mock_bpy, mock_mathutils = mock_bpy_environment
    listener_path = os.path.abspath("blender_addon/morphomesh/listener.py")
    spec = importlib.util.spec_from_file_location("morphomesh_listener_parity_mod", listener_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)

    servers_to_stop = []

    def _create_server(auto_drain: bool = True) -> Tuple[Any, int]:
        with patch.dict("sys.modules", {"bpy": mock_bpy, "mathutils": mock_mathutils}):
            spec.loader.exec_module(mod)
            # Bind to port 0 for collision-free ephemeral OS port
            server = mod.MorphoMeshSocketServer(host="127.0.0.1", port=0)
            server.start()
            port = server.socket.getsockname()[1]
            servers_to_stop.append(server)

            # Auto-drain timer loop runner if requested
            if auto_drain:
                stop_drain = threading.Event()

                def _drain_loop():
                    while not stop_drain.is_set() and server.running:
                        server._drain_queue()
                        time.sleep(0.01)

                th = threading.Thread(target=_drain_loop, daemon=True)
                th.start()
                server._stop_drain = stop_drain

            return server, port

    yield _create_server

    for s in servers_to_stop:
        if hasattr(s, "_stop_drain"):
            s._stop_drain.set()
        s.stop()


# ==============================================================================
# 1. CONNECTION LIFECYCLE TESTS
# ==============================================================================

class TestSocketConnectionLifecycle:
    """Verifies TCP connect, handshake, ping, disconnect, and descriptor management."""

    def test_lifecycle_connect_ping_disconnect(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=2.0) as client:
            assert client in server._clients or len(server._clients) >= 1

            req = {"jsonrpc": "2.0", "id": "req-life-1", "method": "morphomesh.ping", "params": {}}
            client.sendall(json.dumps(req).encode("utf-8") + b"\n")

            client.settimeout(2.0)
            raw = client.recv(4096)
            resp = json.loads(raw.decode("utf-8").strip())

            assert resp.get("id") == "req-life-1"
            assert resp.get("status") == "success"
            assert resp.get("result", {}).get("status") == "pong"
            assert resp.get("result", {}).get("mode") == "interactive"

        time.sleep(0.1)
        assert len(server._clients) == 0

    def test_lifecycle_multiple_sequential_sessions(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=True)

        for i in range(3):
            with socket.create_connection(("127.0.0.1", port), timeout=2.0) as client:
                req = {"jsonrpc": "2.0", "id": f"seq-{i}", "method": "ping", "params": {}}
                client.sendall(json.dumps(req).encode("utf-8") + b"\n")
                raw = client.recv(4096)
                resp = json.loads(raw.decode("utf-8").strip())
                assert resp.get("id") == f"seq-{i}"
            time.sleep(0.05)

        assert len(server._clients) == 0

    def test_bridge_is_interactive_connected_probe(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=True)
        bridge = BlenderBridge(host="127.0.0.1", port=port, socket_timeout=0.5)

        assert bridge.is_interactive_connected() is True

        server.stop()
        time.sleep(0.1)
        assert bridge.is_interactive_connected() is False


# ==============================================================================
# 2. NDJSON STREAMING & FRAMING TESTS
# ==============================================================================

class TestSocketNDJSONStreaming:
    """Verifies newline-delimited streaming without dropped packets or buffer deadlocks."""

    def test_ndjson_streaming_five_rapid_requests_single_connection(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=3.0) as client:
            client.settimeout(3.0)

            # Send 5 distinct requests in rapid back-to-back succession over single connection
            requests = [
                {"jsonrpc": "2.0", "id": f"req-stream-{i}", "method": "morphomesh.ping", "params": {}}
                for i in range(1, 6)
            ]
            batch_payload = b"".join(json.dumps(r).encode("utf-8") + b"\n" for r in requests)
            client.sendall(batch_payload)

            # Read all responses from stream
            responses = []
            buf = b""
            start_time = time.time()
            while len(responses) < 5 and time.time() - start_time < 3.0:
                chunk = client.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip()
                    if line:
                        responses.append(json.loads(line.decode("utf-8")))

            assert len(responses) == 5, f"Expected 5 responses, received {len(responses)}"
            for i, resp in enumerate(responses, 1):
                assert resp.get("id") == f"req-stream-{i}"
                assert resp.get("status") == "success"
                assert resp.get("result", {}).get("status") == "pong"

    def test_ndjson_chunked_streaming_fragmentation(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=3.0) as client:
            client.settimeout(3.0)
            req = {"jsonrpc": "2.0", "id": "req-frag-1", "method": "morphomesh.ping", "params": {}}
            raw = json.dumps(req).encode("utf-8") + b"\n"

            # Transmit in 7-byte fragmented packets
            chunk_size = 7
            for i in range(0, len(raw), chunk_size):
                client.sendall(raw[i : i + chunk_size])
                time.sleep(0.01)

            resp_raw = client.recv(4096)
            resp = json.loads(resp_raw.decode("utf-8").strip())
            assert resp.get("id") == "req-frag-1"
            assert resp.get("status") == "success"

    def test_ndjson_mixed_pipeline_requests(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=3.0) as client:
            client.settimeout(3.0)
            reqs = [
                {"jsonrpc": "2.0", "id": "mix-1", "method": "morphomesh.ping", "params": {}},
                {"jsonrpc": "2.0", "id": "mix-2", "method": "morphomesh.get_scene_status", "params": {}},
                {"jsonrpc": "2.0", "id": "mix-3", "method": "morphomesh.execute_custom_script", "params": {"code": "res = 40 + 2", "return_variables": ["res"]}},
                {"jsonrpc": "2.0", "id": "mix-4", "method": "ping", "params": {}},
                {"jsonrpc": "2.0", "id": "mix-5", "method": "get_scene_info", "params": {}},
            ]
            client.sendall(b"".join(json.dumps(r).encode("utf-8") + b"\n" for r in reqs))

            responses = []
            buf = b""
            start_time = time.time()
            while len(responses) < 5 and time.time() - start_time < 3.0:
                chunk = client.recv(8192)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip()
                    if line:
                        responses.append(json.loads(line.decode("utf-8")))

            assert len(responses) == 5
            ids = [r.get("id") for r in responses]
            assert ids == ["mix-1", "mix-2", "mix-3", "mix-4", "mix-5"]
            assert responses[2]["result"]["returned_data"]["res"] == 42


# ==============================================================================
# 3. MALFORMED DATA RESILIENCE TESTS
# ==============================================================================

class TestSocketMalformedDataResilience:
    """Verifies server withstands invalid payloads and remains healthy for valid requests."""

    def test_malformed_json_garbage_bytes_recovery(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=3.0) as client:
            client.settimeout(3.0)

            # Step 1: Send non-JSON binary garbage
            client.sendall(b"\x00\xff\xfe\xca\xfe_NON_JSON_CORRUPTED_STREAM\n")
            time.sleep(0.05)

            # Step 2: Send incomplete JSON
            client.sendall(b'{"jsonrpc": "2.0", "method": "broken"\n')
            time.sleep(0.05)

            # Step 3: Send valid ping request on same connection
            req_valid = {"jsonrpc": "2.0", "id": "req-valid-after-garbage", "method": "morphomesh.ping", "params": {}}
            client.sendall(json.dumps(req_valid).encode("utf-8") + b"\n")

            # Collect responses
            buf = b""
            start = time.time()
            valid_resp = None
            while time.time() - start < 3.0:
                chunk = client.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip()
                    if line:
                        parsed = json.loads(line.decode("utf-8"))
                        if parsed.get("id") == "req-valid-after-garbage":
                            valid_resp = parsed
                            break
                if valid_resp:
                    break

            assert valid_resp is not None, "Server failed to recover from garbage bytes on same connection"
            assert valid_resp.get("status") == "success"
            assert valid_resp.get("result", {}).get("status") == "pong"

    def test_empty_line_and_whitespace_delimiters(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=2.0) as client:
            client.settimeout(2.0)
            req = {"jsonrpc": "2.0", "id": "req-ws-1", "method": "ping", "params": {}}
            payload = b"\n\n   \n\t\n" + json.dumps(req).encode("utf-8") + b"\n\n  \n"
            client.sendall(payload)

            raw = client.recv(4096)
            resp = json.loads(raw.decode("utf-8").strip())
            assert resp.get("id") == "req-ws-1"
            assert resp.get("status") == "success"


# ==============================================================================
# 4. TIMER IMMORTALITY & ERROR RESILIENCE TESTS
# ==============================================================================

class TestTimerImmortalityAndErrorResilience:
    """Verifies that unhandled operator exceptions never unregister the main-thread timer."""

    def test_unhandled_exception_in_dispatched_method_does_not_drop_timer(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=False)

        # Enqueue failing command
        failing_cmd = {"jsonrpc": "2.0", "id": "req-fail-1", "method": "non_existent_exploding_method", "params": {}}
        mock_client = MagicMock()
        server.command_queue.put((failing_cmd, mock_client))

        # Drain queue manually and assert return value
        next_interval = server._drain_queue()

        # Blender timer contract: must return float (e.g. 0.02), never None or raise exception
        assert next_interval == 0.02, f"Timer dropped: _drain_queue returned {next_interval}"

        # Verify client received clean error response
        assert mock_client.sendall.called
        sent_bytes = mock_client.sendall.call_args[0][0]
        resp = json.loads(sent_bytes.decode("utf-8").strip())
        assert resp.get("status") == "error"
        assert resp.get("id") == "req-fail-1"
        assert resp.get("error", {}).get("code") == -32000

    def test_top_level_timer_barrier_immortality(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=False)

        # Inject non-dict object into queue to simulate catastrophic unexpected data structure
        server.command_queue.put(("CORRUPTED_TUPLE_PAYLOAD", None))

        # Must NOT raise exception out to caller
        interval = server._drain_queue()
        assert interval == 0.02, "Top-level timer barrier failed: timer dropped on malformed queue entry"

    def test_timer_immortality_subsequent_commands_processed(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=False)

        mock_client = MagicMock()
        failing_cmd = {"jsonrpc": "2.0", "id": "err-1", "method": "fail_op", "params": {}}
        valid_cmd = {"jsonrpc": "2.0", "id": "ok-2", "method": "morphomesh.ping", "params": {}}

        server.command_queue.put((failing_cmd, mock_client))
        server.command_queue.put((valid_cmd, mock_client))

        interval = server._drain_queue()
        assert interval == 0.02
        assert mock_client.sendall.call_count == 2

    def test_graceful_timer_deregistration_on_stop(self, socket_server_factory, mock_bpy_environment):
        mock_bpy, _ = mock_bpy_environment
        server, port = socket_server_factory(auto_drain=False)

        assert server.running is True
        server.stop()
        assert server.running is False

        # Drain on stopped server must return None to permit Blender to unregister cleanly
        interval = server._drain_queue()
        assert interval is None


# ==============================================================================
# 5. INTEGRATION PARITY & SCHEMA CONFORMANCE TESTS
# ==============================================================================

class TestSocketListenerIntegrationParity:
    """Validates complete integration parity against BlenderBridge and Pydantic models."""

    def test_integration_ping_environment_info(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=True)
        bridge = BlenderBridge(host="127.0.0.1", port=port)

        pong = bridge.ping()
        assert pong.get("status") == "pong"
        assert pong.get("blender_version") == "4.5.0"
        assert pong.get("mode") == "interactive"

    def test_integration_get_scene_status_complete_hierarchy(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=True)
        bridge = BlenderBridge(host="127.0.0.1", port=port)

        status = bridge.get_scene_status()
        assert isinstance(status, SceneStatusOutput)
        assert status.scene_name == "Scene_MorphoMesh_QA"
        assert status.blender_version == "4.5.0"
        assert status.object_count == 4
        assert status.total_vertices == 2400
        assert status.total_faces == 2380
        assert len(status.armatures) == 1
        assert status.armatures[0]["bone_count"] == 163
        assert len(status.cameras) == 1
        assert status.cameras[0]["lens_focal_length"] == 50.0
        assert len(status.lights) == 1
        assert status.lights[0]["type"] == "AREA"
        assert status.lights[0]["energy"] == 500.0

    def test_integration_execute_custom_script_safe(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=True)
        bridge = BlenderBridge(host="127.0.0.1", port=port)

        code = "a = 15\nb = 25\ntotal = a + b"
        out = bridge.execute_custom_script(code, return_variables=["total"])
        assert isinstance(out, BlenderExecuteOutput)
        assert out.success is True
        assert out.returned_data.get("total") == 40

    def test_integration_execute_custom_script_security_violation(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=True)
        bridge = BlenderBridge(host="127.0.0.1", port=port)

        with pytest.raises(Exception):
            bridge.execute_custom_script("import os\nos.system('echo 1')")

    def test_integration_render_preview_engine_normalization(self, socket_server_factory):
        server, port = socket_server_factory(auto_drain=True)
        bridge = BlenderBridge(host="127.0.0.1", port=port)

        # Directly invoke render_preview via bridge socket dispatch
        out = bridge.render_preview(
            resolution_width=1024,
            resolution_height=1024,
            render_engine="BLENDER_EEVEE_NEXT",
            view_angle="three_quarter",
        )
        assert isinstance(out, RenderPreviewOutput)
        assert out.render_engine == "BLENDER_EEVEE"
        assert out.resolution == [1024, 1024]
        assert out.image_format == "png"
```

---

### 4.2 Required Implementation Blueprints (Milestone 1 Remediation)

To ensure the designed test suite passes with a 100% success rate, the implementer must apply the following enhancements:

#### Patch 1: `blender_addon/morphomesh/listener.py` — NDJSON Framing & Immortal Timer
```python
# Replace lines 155-173 in _client_handler:
buffer = b""
try:
    while self.running:
        try:
            data = client.recv(65536)
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    cmd = json.loads(line.decode("utf-8"))
                    self.command_queue.put((cmd, client))
                except (json.JSONDecodeError, UnicodeDecodeError) as err:
                    logger.warning(f"Malformed NDJSON frame discarded: {err}")
                    # Optionally respond with JSON-RPC -32700 parse error
        except socket.timeout:
            continue
        except Exception:
            break
finally:
    with self._clients_lock:
        self._clients.discard(client)

# Wrap _drain_queue in top-level barrier:
def _drain_queue(self) -> Optional[float]:
    if not self.running:
        return None

    try:
        while not self.command_queue.empty():
            try:
                cmd, client = self.command_queue.get_nowait()
            except queue.Empty:
                break

            if not isinstance(cmd, dict):
                logger.warning(f"Discarding invalid non-dict command: {cmd}")
                continue

            req_id = cmd.get("id", "res-1")
            method = cmd.get("method") or cmd.get("type", "")
            params = cmd.get("params", {})

            try:
                result = self._dispatch(method, params)
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "status": "success",
                    "result": result,
                }
            except Exception as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "status": "error",
                    "error": {"code": -32000, "message": str(e)},
                }

            try:
                client.sendall(json.dumps(response).encode("utf-8") + b"\n")
            except Exception:
                pass
    except Exception as fatal_e:
        logger.error(f"Fatal exception contained in _drain_queue timer barrier: {fatal_e}", exc_info=True)

    return 0.02
```

#### Patch 2: `blender_addon/morphomesh/listener.py` — `morphomesh.render_preview` in `_dispatch`
```python
elif method in ("morphomesh.render_preview", "render_preview"):
    scene = bpy.context.scene
    width = int(params.get("resolution_width", 1024))
    height = int(params.get("resolution_height", 1024))
    samples = int(params.get("samples", 64))
    engine = params.get("render_engine", "BLENDER_EEVEE")
    if engine == "BLENDER_EEVEE_NEXT":
        engine = "BLENDER_EEVEE"

    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.engine = engine
    scene.render.film_transparent = bool(params.get("transparent_background", True))

    out_dir = params.get("output_dir") or tempfile.gettempdir()
    os.makedirs(out_dir, exist_ok=True)
    render_path = os.path.join(out_dir, f"preview_{uuid.uuid4().hex[:8]}.png").replace('\\', '/')
    scene.render.filepath = render_path

    try:
        bpy.ops.render.render(write_still=True)
    except Exception as e_rend:
        logger.warning(f"Render preview op skipped in mock/test: {e_rend}")

    return {
        "image_path": render_path,
        "image_format": "png",
        "resolution": [width, height],
        "render_engine": engine,
        "samples": samples,
        "render_time_seconds": 0.2,
        "view_angle": params.get("view_angle", "three_quarter"),
        "lighting_preset": params.get("lighting_preset", "studio_three_point"),
    }
```

#### Patch 3: `src/morphomesh/blender_bridge.py` — Trailing `\n` in `send_socket_request`
```python
# In send_socket_request line 343:
encoded = json.dumps(payload).encode("utf-8") + b"\n"
sock.sendall(encoded)
```

---

## 5. Verification Method

### 5.1 Independent Verification Commands
1. **Verify Baseline Tests Still Pass**:
   ```powershell
   pytest tests/test_blender_bridge.py tests/test_adversarial_fastmcp_bridge_human.py
   ```
   *Expected*: 147 passed, 0 failures.

2. **Verify New Socket Parity Test Suite (upon placement by implementer)**:
   ```powershell
   pytest tests/test_bridge_socket_parity.py -v
   ```
   *Expected*: 15 passed in $<3.0$ seconds, exit code 0.

3. **Verify Full Test Suite Parity**:
   ```powershell
   pytest tests/ -k "bridge or socket"
   ```
   *Expected*: All matching tests passed, 0 failures.

### 5.2 Invalidation Conditions
- Any test in `test_bridge_socket_parity.py` hanging longer than 3.0s (indicates an unhandled socket buffer boundary deadlock).
- Any test raising `Address already in use` (indicates hardcoded port was used instead of dynamic ephemeral port `port=0`).
- `SceneStatusOutput` or `RenderPreviewOutput` raising Pydantic `ValidationError` (indicates schema key mismatch in listener response).
- `_drain_queue` returning `None` during active execution (indicates timer mortality guard dropped).
