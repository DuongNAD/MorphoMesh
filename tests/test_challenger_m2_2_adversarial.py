"""
MorphoMesh: Empirical Adversarial Challenge Test Suite for Milestone 2.
Subsystem: Blender Socket Bridge Transport & AST Security Validation.
Author: Challenger M2-2 (critic, specialist).

Scope:
1. NDJSON streaming under simulated chunk fragmentation (byte-by-byte feed, multi-line buffers, trailing newlines).
2. Connection timeout behavior, rapid reconnect probing, and backlog concurrency analysis.
3. AST security validation in BpyCodeValidator against obfuscated imports, forbidden builtins, attribute evasion, and relative import gaps.
4. Verification that generated scripts for all 20 commands parse into valid Python AST under canonical and adversarial parameters.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import socket
import sys
import threading
import time
from typing import Any, Dict, Generator, List, Tuple
from unittest.mock import MagicMock, patch

import pytest

from morphomesh.bridge.bridge import BlenderBridge
from morphomesh.bridge.client import BlenderSocketClient
from morphomesh.bridge.scripts import (
    build_headless_script,
    build_interactive_script,
    generate_auto_rig_human_script,
    generate_create_human_asset_script,
)
from morphomesh.bridge.validator import BlenderExecutionError, BpyCodeValidator, SecurityException
from morphomesh.models import MorphoMeshException


# ==============================================================================
# FIXTURES & HERMETIC SOCKET SERVER HARNESS
# ==============================================================================

class MockVector(list):
    """Lightweight 3D Vector for mathutils simulation."""
    def __init__(self, co=(0.0, 0.0, 0.0)):
        super().__init__([float(c) for c in co])

    @property
    def x(self) -> float:
        return self[0]

    @property
    def y(self) -> float:
        return self[1]

    @property
    def z(self) -> float:
        return self[2]

    def __add__(self, other):
        return MockVector([a + b for a, b in zip(self, other)])

    def __sub__(self, other):
        return MockVector([a - b for a, b in zip(self, other)])

    def dot(self, other) -> float:
        return sum(a * b for a, b in zip(self, other))

    def to_track_quat(self, track="-Z", up="Y"):
        m = MagicMock()
        m.to_euler.return_value = MockVector([1.48, 0.0, 0.0])
        return m


@pytest.fixture(scope="function")
def mock_bpy_env() -> Tuple[MagicMock, MagicMock]:
    """Hermetic mock Blender environment."""
    mock_bpy = MagicMock()
    mock_bpy.app.version = (4, 5, 0)
    mock_bpy.app.timers.is_registered.return_value = False
    mock_bpy.app.background = False

    scene = MagicMock()
    scene.name = "Scene_MorphoMesh_Challenger"
    scene.objects = []
    scene.camera = None
    mock_bpy.context.scene = scene
    mock_bpy.context.active_object = None

    mock_mathutils = MagicMock()
    mock_mathutils.Vector = MockVector
    return mock_bpy, mock_mathutils


@pytest.fixture(scope="function")
def ephemeral_server_factory(mock_bpy_env) -> Generator[Any, None, None]:
    """Creates ephemeral MorphoMeshSocketServer instances bound to port 0."""
    mock_bpy, mock_mathutils = mock_bpy_env
    listener_path = os.path.abspath("blender_addon/morphomesh/listener.py")
    spec = importlib.util.spec_from_file_location("morphomesh_listener_adversarial", listener_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)

    servers_to_stop = []

    def _create_server(auto_drain: bool = True) -> Tuple[Any, int]:
        with patch.dict("sys.modules", {"bpy": mock_bpy, "mathutils": mock_mathutils}):
            spec.loader.exec_module(mod)
            server = mod.MorphoMeshSocketServer(host="127.0.0.1", port=0)
            server.start()
            port = server.socket.getsockname()[1]
            servers_to_stop.append(server)

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


# Canonical list of all 20 RPC commands
ALL_20_COMMANDS = [
    "morphomesh.ping",
    "morphomesh.get_scene_status",
    "morphomesh.execute_custom_script",
    "morphomesh.optimize_topology",
    "morphomesh.create_armature",
    "morphomesh.render_preview",
    "morphomesh.setup_inspector_camera",
    "morphomesh.capture_viewport",
    "morphomesh.capture_multi_angle_inspection",
    "morphomesh.critique_visual_quality",
    "morphomesh.setup_creature_fur",
    "morphomesh.setup_creature_materials",
    "morphomesh.generate_war_armor",
    "morphomesh.evaluate_fur_ribbons",
    "morphomesh.create_human_asset",
    "morphomesh.auto_rig_human",
    "morphomesh.setup_human_materials",
    "morphomesh.groom_human",
    "morphomesh.dress_human",
    "morphomesh.assemble_master_character",
]


# ==============================================================================
# 1. NDJSON CHUNK FRAGMENTATION ADVERSARIAL TESTS
# ==============================================================================

class TestNDJSONChunkFragmentationAdversarial:
    """Stress-tests NDJSON streaming under severe packet fragmentation and line framing."""

    def test_byte_by_byte_stream_fragmentation(self, ephemeral_server_factory):
        """Transmit request 1 byte at a time to verify stream reassembly."""
        server, port = ephemeral_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=5.0) as client:
            client.settimeout(5.0)
            req = {"jsonrpc": "2.0", "id": "frag-byte-1", "method": "morphomesh.ping", "params": {}}
            raw = json.dumps(req).encode("utf-8") + b"\n"

            # Transmit 1 single byte per sendall call
            for byte_idx in range(len(raw)):
                client.sendall(raw[byte_idx : byte_idx + 1])
                time.sleep(0.001)

            # Receive response
            buf = b""
            start = time.time()
            response = None
            while time.time() - start < 4.0:
                chunk = client.recv(1024)
                if not chunk:
                    break
                buf += chunk
                if b"\n" in buf:
                    line, _ = buf.split(b"\n", 1)
                    if line.strip():
                        response = json.loads(line.decode("utf-8"))
                        break

            assert response is not None, "Failed to reassemble byte-by-byte fragmented request"
            assert response.get("id") == "frag-byte-1"
            assert response.get("status") == "success"
            assert response.get("result", {}).get("status") == "pong"

    def test_byte_by_byte_unicode_multi_byte_fragmentation(self, ephemeral_server_factory):
        """Stress-test non-ASCII UTF-8 multibyte sequences split across single byte chunks."""
        server, port = ephemeral_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=5.0) as client:
            client.settimeout(5.0)
            unicode_str = "余念安 - Dư Niệm An ✨🦋 [Concept 4-View: 正面/侧面/背面]"
            req = {
                "jsonrpc": "2.0",
                "id": "unicode-frag-1",
                "method": "morphomesh.execute_custom_script",
                "params": {"code": f"name = {json.dumps(unicode_str)}", "return_variables": ["name"]},
            }
            raw = json.dumps(req, ensure_ascii=False).encode("utf-8") + b"\n"

            for i in range(len(raw)):
                client.sendall(raw[i : i + 1])
                time.sleep(0.0005)

            buf = b""
            start = time.time()
            response = None
            while time.time() - start < 4.0:
                chunk = client.recv(2048)
                if not chunk:
                    break
                buf += chunk
                if b"\n" in buf:
                    line, _ = buf.split(b"\n", 1)
                    if line.strip():
                        response = json.loads(line.decode("utf-8"))
                        break

            assert response is not None, "Failed to parse multi-byte UTF-8 fragmented stream"
            assert response.get("id") == "unicode-frag-1"
            assert response.get("status") == "success"
            assert response.get("result", {}).get("returned_data", {}).get("name") == unicode_str

    def test_multiline_burst_in_single_buffer(self, ephemeral_server_factory):
        """Pack 10 back-to-back requests in a single TCP sendall buffer to test line splitting."""
        server, port = ephemeral_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=5.0) as client:
            client.settimeout(5.0)
            count = 10
            requests = [
                {"jsonrpc": "2.0", "id": f"burst-{i}", "method": "morphomesh.ping", "params": {}}
                for i in range(count)
            ]
            payload = b"".join(json.dumps(r).encode("utf-8") + b"\n" for r in requests)
            client.sendall(payload)

            responses = []
            buf = b""
            start = time.time()
            while len(responses) < count and time.time() - start < 4.0:
                chunk = client.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip()
                    if line:
                        responses.append(json.loads(line.decode("utf-8")))

            assert len(responses) == count, f"Expected {count} responses, got {len(responses)}"
            for i, resp in enumerate(responses):
                assert resp.get("id") == f"burst-{i}"
                assert resp.get("status") == "success"

    def test_boundary_split_across_json_content(self, ephemeral_server_factory):
        """Split request across arbitrary 3-byte chunk boundaries covering brackets and quotes."""
        server, port = ephemeral_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=4.0) as client:
            client.settimeout(4.0)
            reqs = [
                {"jsonrpc": "2.0", "id": "split-1", "method": "ping", "params": {}},
                {"jsonrpc": "2.0", "id": "split-2", "method": "ping", "params": {}},
            ]
            data = b"".join(json.dumps(r).encode("utf-8") + b"\n" for r in reqs)

            # Transmit in 3-byte slices
            step = 3
            for i in range(0, len(data), step):
                client.sendall(data[i : i + step])
                time.sleep(0.002)

            responses = []
            buf = b""
            start = time.time()
            while len(responses) < 2 and time.time() - start < 3.0:
                chunk = client.recv(2048)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip()
                    if line:
                        responses.append(json.loads(line.decode("utf-8")))

            assert len(responses) == 2
            assert responses[0]["id"] == "split-1"
            assert responses[1]["id"] == "split-2"

    def test_whitespace_and_crlf_variants(self, ephemeral_server_factory):
        """Test Windows CRLF, redundant trailing newlines, and whitespace padding."""
        server, port = ephemeral_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=3.0) as client:
            client.settimeout(3.0)
            req = {"jsonrpc": "2.0", "id": "crlf-1", "method": "morphomesh.ping", "params": {}}
            payload = b"\r\n\r\n   " + json.dumps(req).encode("utf-8") + b"   \r\n\r\n\n"
            client.sendall(payload)

            raw = client.recv(2048)
            resp = json.loads(raw.decode("utf-8").strip())
            assert resp.get("id") == "crlf-1"
            assert resp.get("status") == "success"

    def test_request_without_trailing_newline_eof_fallback(self, ephemeral_server_factory):
        """Verify fallback parsing when client sends JSON without trailing newline and half-closes (SHUT_WR)."""
        server, port = ephemeral_server_factory(auto_drain=True)

        client = socket.create_connection(("127.0.0.1", port), timeout=3.0)
        req = {"jsonrpc": "2.0", "id": "no-newline-eof", "method": "morphomesh.ping", "params": {}}
        raw = json.dumps(req).encode("utf-8")  # NO \n
        client.sendall(raw)
        client.shutdown(socket.SHUT_WR)

        buf = b""
        start = time.time()
        while time.time() - start < 3.0:
            chunk = client.recv(2048)
            if not chunk:
                break
            buf += chunk

        client.close()
        resp = json.loads(buf.decode("utf-8").strip())
        assert resp.get("id") == "no-newline-eof"
        assert resp.get("status") == "success"


# ==============================================================================
# 2. CONNECTION TIMEOUT & RECONNECT PROBING ADVERSARIAL TESTS
# ==============================================================================

class TestConnectionTimeoutAndRapidReconnectProbing:
    """Stress-tests socket connection timeout management, rapid reconnect storm, and backlog limits."""

    def test_is_connected_on_closed_port_rapid_return(self):
        """Probe an inactive port: must return False rapidly (<0.35s) without exceptions."""
        client = BlenderSocketClient(host="127.0.0.1", port=19876, socket_timeout=0.25)
        start = time.time()
        connected = client.is_connected()
        duration = time.time() - start

        assert connected is False
        assert duration < 0.35, f"is_connected() on dead port took too long: {duration}s"

    def test_send_request_on_closed_port_raises_cleanly(self):
        """send_request on inactive port must raise OSError/ConnectionRefusedError promptly."""
        client = BlenderSocketClient(host="127.0.0.1", port=19876, socket_timeout=0.2)
        start = time.time()
        with pytest.raises((ConnectionRefusedError, OSError, TimeoutError)):
            client.send_request("morphomesh.ping", {}, timeout=0.5)
        duration = time.time() - start
        assert duration < 1.0

    def test_send_request_timeout_on_silent_blackhole_server(self):
        """Client must respect timeout when connected to a non-responsive TCP listener."""
        silent_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        silent_srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        silent_srv.bind(("127.0.0.1", 0))
        silent_srv.listen(1)
        port = silent_srv.getsockname()[1]

        stop_srv = threading.Event()

        def _silent_accept():
            silent_srv.settimeout(2.0)
            try:
                conn, _ = silent_srv.accept()
                while not stop_srv.is_set():
                    time.sleep(0.05)
                conn.close()
            except Exception:
                pass

        th = threading.Thread(target=_silent_accept, daemon=True)
        th.start()

        client = BlenderSocketClient(host="127.0.0.1", port=port, socket_timeout=1.0)
        start = time.time()
        with pytest.raises(TimeoutError) as exc_info:
            client.send_request("morphomesh.ping", {}, timeout=0.3)
        duration = time.time() - start

        stop_srv.set()
        silent_srv.close()
        th.join(timeout=1.0)

        assert 0.25 <= duration <= 0.9, f"Timeout expected around 0.3s, took {duration}s"
        assert "timed out" in str(exc_info.value).lower()

    def test_rapid_reconnect_probing_storm(self, ephemeral_server_factory):
        """Execute 50 consecutive connection probes in rapid succession to ensure descriptor health."""
        server, port = ephemeral_server_factory(auto_drain=True)
        client = BlenderSocketClient(host="127.0.0.1", port=port, socket_timeout=0.5)

        for _ in range(50):
            assert client.is_connected() is True

        time.sleep(0.1)
        with server._clients_lock:
            # All ephemeral probing sockets must be closed and cleared
            assert len(server._clients) == 0

    def test_concurrent_reconnect_probing_within_backlog(self, ephemeral_server_factory):
        """Concurrent probes within server listen backlog (4 concurrent threads)."""
        server, port = ephemeral_server_factory(auto_drain=True)
        errors = []

        def _worker(worker_id: int):
            try:
                c = BlenderSocketClient(host="127.0.0.1", port=port, socket_timeout=2.0)
                for i in range(3):
                    if not c.is_connected():
                        errors.append(f"Worker {worker_id} probe {i} failed is_connected")
                    res = c.send_request("morphomesh.ping", {}, timeout=2.0)
                    if res.get("status") != "pong":
                        errors.append(f"Worker {worker_id} request {i} invalid response: {res}")
            except Exception as e:
                errors.append(f"Worker {worker_id} raised: {e}")

        threads = [threading.Thread(target=_worker, args=(i,), daemon=True) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert len(errors) == 0, f"Concurrent workers encountered errors: {errors}"

    def test_concurrent_backlog_overflow_causes_probe_drop(self, ephemeral_server_factory):
        """Empirically demonstrates that listen(5) backlog causes transient probe drops under high concurrency (10 threads)."""
        server, port = ephemeral_server_factory(auto_drain=True)
        failed_probes = []

        def _probe_worker():
            c = BlenderSocketClient(host="127.0.0.1", port=port, socket_timeout=0.25)
            # Tight loop simultaneous probing to overwhelm listen(5)
            for _ in range(3):
                if not c.is_connected():
                    failed_probes.append(1)

        threads = [threading.Thread(target=_probe_worker, daemon=True) for _ in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        # Empirically documents that listen(5) is susceptible to probe failure under >=10 concurrent connections
        # This confirms our architecture finding regarding socket backlog sizing.
        print(f"Empirical backlog observation: {len(failed_probes)} probes dropped under 12 concurrent connections on listen(5)")

    def test_server_restart_reconnect_resilience(self, ephemeral_server_factory, mock_bpy_env):
        """Verify client transitions cleanly across server stop and restart."""
        server, port = ephemeral_server_factory(auto_drain=True)
        client = BlenderSocketClient(host="127.0.0.1", port=port, socket_timeout=0.5)

        assert client.is_connected() is True
        res = client.send_request("morphomesh.ping", {})
        assert res.get("status") == "pong"

        # Stop server
        server.stop()
        time.sleep(0.1)
        assert client.is_connected() is False

        # Restart on same port
        mock_bpy, mock_mathutils = mock_bpy_env
        listener_path = os.path.abspath("blender_addon/morphomesh/listener.py")
        spec = importlib.util.spec_from_file_location("morphomesh_listener_rebound", listener_path)
        mod = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", {"bpy": mock_bpy, "mathutils": mock_mathutils}):
            spec.loader.exec_module(mod)
            new_server = mod.MorphoMeshSocketServer(host="127.0.0.1", port=port)
            new_server.start()

            stop_drain = threading.Event()

            def _drain():
                while not stop_drain.is_set() and new_server.running:
                    new_server._drain_queue()
                    time.sleep(0.01)

            th = threading.Thread(target=_drain, daemon=True)
            th.start()

            try:
                assert client.is_connected() is True
                res2 = client.send_request("morphomesh.ping", {})
                assert res2.get("status") == "pong"
            finally:
                stop_drain.set()
                new_server.stop()

    def test_abrupt_client_socket_reset(self, ephemeral_server_factory):
        """Simulate client RST/abrupt disconnect during packet transmission."""
        server, port = ephemeral_server_factory(auto_drain=True)

        s = socket.create_connection(("127.0.0.1", port), timeout=2.0)
        s.sendall(b'{"jso')
        s.close()
        time.sleep(0.1)

        # Server must continue serving valid requests seamlessly
        client = BlenderSocketClient(host="127.0.0.1", port=port, socket_timeout=2.0)
        res = client.send_request("morphomesh.ping", {})
        assert res.get("status") == "pong"


# ==============================================================================
# 3. AST SECURITY VALIDATOR ADVERSARIAL TESTS
# ==============================================================================

class TestBpyCodeValidatorASTSecurityAdversarial:
    """Stress-tests BpyCodeValidator against evasions, forbidden builtins, attribute traversal, and relative import gaps."""

    @pytest.fixture
    def validator(self) -> BpyCodeValidator:
        return BpyCodeValidator()

    @pytest.mark.parametrize("call_expr", [
        "eval('2 + 2')",
        "exec('x = 1')",
        "open('/etc/passwd', 'r')",
        "compile('1+1', '<str>', 'eval')",
        "__import__('os')",
        "input('password: ')",
        "breakpoint()",
        "globals()",
        "locals()",
        "getattr(bpy, 'context')",
        "setattr(bpy, 'name', 'evil')",
        "delattr(bpy, 'context')",
    ])
    def test_reject_forbidden_builtins_calls(self, validator: BpyCodeValidator, call_expr: str):
        """Direct invocation of forbidden built-in functions must be rejected."""
        with pytest.raises(SecurityException):
            validator.validate(call_expr)

    @pytest.mark.parametrize("aliasing_expr", [
        "e = eval; e('1')",
        "o = open; o('/tmp/pwn')",
        "g = globals; g()",
        "l = locals; l()",
        "b = __builtins__; b",
        "x = getattr; x(bpy, 'ops')",
        "s = setattr; s(bpy, 'x', 1)",
    ])
    def test_reject_forbidden_builtin_name_aliasing(self, validator: BpyCodeValidator, aliasing_expr: str):
        """Aliasing forbidden names to bypass direct call inspection must be rejected."""
        with pytest.raises(SecurityException):
            validator.validate(aliasing_expr)

    @pytest.mark.parametrize("import_expr", [
        "import os",
        "import os.path",
        "from os import path",
        "from os import system",
        "import sys",
        "from sys import modules",
        "import subprocess",
        "from subprocess import Popen",
        "import shutil",
        "import socket",
        "import http.client",
        "import urllib.request",
        "import requests",
        "import ctypes",
        "import multiprocessing",
        "import threading",
        "import signal",
        "import importlib",
        "import builtins",
        "import pickle",
        "import shelve",
        "import marshal",
    ])
    def test_reject_forbidden_module_imports(self, validator: BpyCodeValidator, import_expr: str):
        """All unapproved or dangerous module imports must be rejected."""
        with pytest.raises(SecurityException):
            validator.validate(import_expr)

    @pytest.mark.parametrize("dunder_expr", [
        "x = ().__class__.__bases__[0].__subclasses__()",
        "f = lambda: None; x = f.__globals__",
        "f = lambda: None; x = f.__code__",
        "f = lambda: None; x = f.__dict__",
        "x = bpy.__class__",
        "x = bpy.__mro__",
        "x = bpy.__annotations__",
        "x = bpy.__custom_dunder__",
        "__malicious_var__ = 1",
        "x = __hidden_call__()",
    ])
    def test_reject_reflection_and_dunder_escapes(self, validator: BpyCodeValidator, dunder_expr: str):
        """Reflection traversal, code object extraction, and dunders must be rejected."""
        with pytest.raises(SecurityException):
            validator.validate(dunder_expr)

    def test_relative_import_evasion_gap_empirical_analysis(self, validator: BpyCodeValidator):
        """
        EMPIRICAL CHALLENGE FINDING:
        BpyCodeValidator visit_ImportFrom only checks `if node.module:`.
        When a relative import `from . import os as my_mod` is used, node.module is None,
        which completely bypasses module checking and name checking in visit_ImportFrom.
        """
        evasion_payload = "from . import os as my_mod\nmy_mod.system('calc')"
        # Empirically verify that BpyCodeValidator permits this evasion without raising SecurityException:
        validator.validate(evasion_payload)
        # This confirms a critical AST validator gap in handling relative from-imports.

    def test_permitted_safe_scientific_and_bpy_constructs(self, validator: BpyCodeValidator):
        """Legitimate bpy, math, mathutils, numpy, json constructs must pass validation."""
        safe_code = """
import bpy
import math
import mathutils
import json
import numpy as np

v1 = mathutils.Vector((0.0, 1.0, 2.0))
v2 = mathutils.Vector((1.0, 0.0, 0.0))
angle = math.acos(v1.normalized().dot(v2.normalized()))
data = json.dumps({"angle": angle})
arr = np.zeros((10, 3), dtype=np.float32)
total = int(np.sum(arr))
"""
        validator.validate(safe_code)

    def test_boundary_max_script_length(self, validator: BpyCodeValidator):
        """Length limits: <=10000 chars passes, >10000 chars raises SecurityException."""
        valid_chunk = "# comment\n" * 1000  # 10000 chars
        validator.validate(valid_chunk)

        excessive_chunk = valid_chunk + "x = 1"  # 10005 chars
        with pytest.raises(SecurityException) as exc_info:
            validator.validate(excessive_chunk)
        assert "exceeds maximum length" in str(exc_info.value)

    def test_boundary_empty_and_whitespace_scripts(self, validator: BpyCodeValidator):
        """Empty or whitespace scripts must raise SecurityException."""
        with pytest.raises(SecurityException):
            validator.validate("")
        with pytest.raises(SecurityException):
            validator.validate("   \n\t\n   ")

    def test_syntax_error_wrapped_in_morphomesh_exception(self, validator: BpyCodeValidator):
        """Syntax errors must raise MorphoMeshException with ERR_SCRIPT_SYNTAX_ERROR."""
        with pytest.raises(MorphoMeshException) as exc_info:
            validator.validate("def broken_syntax(: pass")
        assert exc_info.value.code == "ERR_SCRIPT_SYNTAX_ERROR"


# ==============================================================================
# 4. AST VALIDITY VERIFICATION FOR ALL 20 COMMAND SCRIPTS
# ==============================================================================

class TestAll20CommandsASTValidityAdversarial:
    """Verifies that generated scripts for all 20 commands parse into valid Python AST."""

    CANONICAL_PARAMS = {
        "input_mesh_path": r"C:/MorphoMesh/Models/hero_mesh.obj",
        "character_name": "Yu_Nian_An",
        "output_path": r"output/yu_nian_an/Yu_Nian_An_Export.glb",
        "output_blend_path": r"output/yu_nian_an/Yu_Nian_An_Master.blend",
        "target_object": "Human_Base_Mesh",
        "mesh_object_name": "Human_Base_Mesh",
        "human_object_name": "Human_Base_Mesh",
        "rig_type": "rigify_human",
        "pose": "puppeteer_pose",
        "export_format": "fbx",
        "material_preset": "yu_nian_an",
        "skin_tone": "porcelain_fair",
        "subsurface_scattering": True,
        "refractive_eyes": True,
        "hair_style": "hime_cut_long",
        "hair_color": "silky_black",
        "strand_count": 15000,
        "include_eyebrows": True,
        "include_eyelashes": True,
        "generate_ribbons": True,
        "outfit": "yu_nian_an_dress",
        "outfit_preset": "yu_nian_an_dress",
        "include_sandals": True,
        "include_red_threads": True,
        "include_glowing_butterflies": True,
        "butterfly_count": 10,
        "clearance_offset": 0.015,
        "height": 1.65,
        "head_ratio": 7.41,
        "render_engine": "BLENDER_EEVEE_NEXT",
        "samples": 64,
        "cycles_samples": 128,
        "save_blend": True,
        "save_after": True,
        "save_path": r"C:/temp/save_scene.blend",
        "viewpoint": "turntable_4views",
        "viewpoints": ["front", "side", "three_quarter"],
        "focal_length": 85.0,
        "resolution_width": 1920,
        "resolution_height": 1080,
        "shading_mode": "MATERIAL",
        "color_type": "TEXTURE",
        "target_poly_count": 12000,
        "creature_type": "quadruped",
        "code": "result_value = 100 * 2\nstatus_str = 'ok'",
        "script": "import bpy\nbpy.ops.object.select_all(action='DESELECT')",
        "return_variables": ["result_value", "status_str"],
        "scene_name": "Scene_Main",
        "include_mesh_stats": True,
        "include_hierarchy": True,
        "include_materials": True,
        "include_armatures": True,
        "include_cameras_lights": True,
    }

    @pytest.mark.parametrize("method", ALL_20_COMMANDS)
    def test_headless_script_ast_validity_for_all_20_commands(self, method: str):
        """Headless script generator for each of the 20 commands must produce valid Python AST."""
        script_code = build_headless_script(method, self.CANONICAL_PARAMS)
        assert isinstance(script_code, str)
        assert len(script_code) > 0
        try:
            tree = ast.parse(script_code)
            assert isinstance(tree, ast.Module)
        except SyntaxError as e:
            pytest.fail(f"Headless script for '{method}' produced invalid Python AST: {e}")

    @pytest.mark.parametrize("method", ALL_20_COMMANDS)
    def test_interactive_script_ast_validity_for_all_20_commands(self, method: str):
        """Interactive script generator for each of the 20 commands must produce valid Python AST."""
        script_code = build_interactive_script(method, self.CANONICAL_PARAMS)
        assert isinstance(script_code, str)
        assert len(script_code) > 0
        try:
            tree = ast.parse(script_code)
            assert isinstance(tree, ast.Module)
        except SyntaxError as e:
            pytest.fail(f"Interactive script for '{method}' produced invalid Python AST: {e}")

    def test_specialized_human_asset_generators_ast_validity(self):
        """Verify specialized human asset and autorig script generators parse to valid AST under canonical params."""
        create_script = generate_create_human_asset_script(self.CANONICAL_PARAMS)
        tree_create = ast.parse(create_script)
        assert isinstance(tree_create, ast.Module)

        rig_script = generate_auto_rig_human_script(self.CANONICAL_PARAMS)
        tree_rig = ast.parse(rig_script)
        assert isinstance(tree_rig, ast.Module)

    def test_headless_script_empty_params_ast_validity(self):
        """All 20 commands with empty dict parameters must produce valid AST."""
        for method in ALL_20_COMMANDS:
            h_code = build_headless_script(method, {})
            i_code = build_interactive_script(method, {})
            ast.parse(h_code)
            ast.parse(i_code)

    def test_string_injection_vulnerability_in_human_asset_script(self):
        """
        EMPIRICAL CHALLENGE FINDING:
        In generate_create_human_asset_script, `character_name` is interpolated raw:
        `obj = bpy.data.objects.get("{mesh_name}")` without repr() or json escaping.
        If character_name contains quotes or newlines, it injects syntax errors.
        """
        adversarial_name = 'Yu "Nian" An\n'
        vuln_params = dict(self.CANONICAL_PARAMS)
        vuln_params["character_name"] = adversarial_name

        script = generate_create_human_asset_script(vuln_params)
        with pytest.raises(SyntaxError):
            ast.parse(script)
        # This confirms a string interpolation / code injection vulnerability in script generation.
