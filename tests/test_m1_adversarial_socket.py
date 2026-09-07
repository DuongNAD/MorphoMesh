"""
MorphoMesh: Milestone 1 Adversarial Socket Challenger Test Suite.
Target: tests/test_m1_adversarial_socket.py
Challenger: Challenger M1_1 (Protocol & Stream Fuzzing)
Milestone: M1 - Interactive Socket Bridge Parity & Reliability (R3)

Adversarial Stress Test Categories:
1. High-Frequency Burst Requests:
   - 10, 25, 50, 100 rapid sequential requests over single persistent socket.
   - Pipelined requests in contiguous single-buffer transmission.
   - Multi-threaded concurrent client bursts (5 clients x 20 requests = 100 concurrent requests).
   - Strict FIFO ordering, ID matching, zero dropped frames.
2. Fragmented Byte Streaming:
   - Deterministic 1-byte, 2-byte, 3-byte, 4-byte, 5-byte chunked streaming.
   - Randomized 1-to-5 byte chunk streaming.
   - Multi-request continuous streaming across newline delimiter boundaries.
3. Garbage & Malformed Data Injection & Recovery:
   - Non-UTF8 binary garbage injection followed immediately by valid requests.
   - Syntax-corrupted JSON lines followed immediately by valid requests.
   - Truncated unclosed JSON lines followed immediately by valid requests.
   - Non-dict JSON primitives (string, int, array, boolean) followed immediately by valid requests.
   - Chaos interleaving (alternating garbage and valid requests).
   - Recovery verification: code -32700 parse error or -32600 invalid request, subsequent valid requests succeed.
4. Large Payload Handling (>500KB JSON Payloads):
   - Inbound request with >600KB JSON payload.
   - Outbound response with >700KB JSON payload.
   - Bidirectional round-trip with >800KB payloads.
   - 1MB high-stress payload transmission.
   - Verification through BlenderBridge.send_socket_request() client API.
5. Deadlock, Hang & Lifecycle Resilience:
   - Immediate client disconnect mid-packet.
   - TCP half-close (SHUT_WR) request handling.
   - Rapid client churn descriptor leak prevention.
   - Timer immortality under deliberate dispatch exceptions.
"""

from __future__ import annotations

import importlib.util
import json
import os
import queue
import random
import socket
import sys
import threading
import time
from typing import Any, Dict, Generator, List, Tuple
from unittest.mock import MagicMock, patch

import pytest

from morphomesh.blender_bridge import BlenderBridge, BlenderExecutionError


# ==============================================================================
# MOCK ENVIRONMENT & SERVER FACTORY
# ==============================================================================

class MockVector(list):
    """Lightweight 3D Vector for mathutils simulation."""
    def __init__(self, co=(0.0, 0.0, 0.0)):
        super().__init__([float(c) for c in co])

    @property
    def x(self) -> float:
        return self[0]

    @x.setter
    def x(self, val: float):
        self[0] = float(val)

    @property
    def y(self) -> float:
        return self[1]

    @y.setter
    def y(self, val: float):
        self[1] = float(val)

    @property
    def z(self) -> float:
        return self[2]

    @z.setter
    def z(self, val: float):
        self[2] = float(val)

    def __add__(self, other):
        return MockVector([a + b for a, b in zip(self, other)])

    def __sub__(self, other):
        return MockVector([a - b for a, b in zip(self, other)])

    def __mul__(self, scalar):
        return MockVector([a * scalar for a in self])

    def __rmul__(self, scalar):
        return MockVector([a * scalar for a in self])

    def dot(self, other) -> float:
        return sum(a * b for a, b in zip(self, other))

    def to_track_quat(self, track="-Z", up="Y"):
        m = MagicMock()
        m.to_euler.return_value = MockVector([1.48, 0.0, 0.0])
        return m


@pytest.fixture(scope="function")
def mock_bpy_environment() -> Tuple[MagicMock, MagicMock]:
    """Hermetic mock Blender environment for socket server testing."""
    mock_bpy = MagicMock()
    mock_bpy.app.version = (4, 5, 0)
    mock_bpy.app.timers.is_registered.return_value = False
    mock_bpy.app.background = False

    scene = MagicMock()
    scene.name = "Scene_Adversarial_QA"

    mesh_obj = MagicMock()
    mesh_obj.name = "Adversarial_Test_Mesh"
    mesh_obj.type = "MESH"
    mesh_obj.location = MockVector([0.0, 0.0, 1.0])
    mesh_obj.rotation_euler = MockVector([0.0, 0.0, 0.0])
    mesh_obj.scale = MockVector([1.0, 1.0, 1.0])
    mesh_obj.parent = None
    mesh_obj.children = []
    mesh_obj.modifiers = []
    mesh_obj.data.materials = [MagicMock(name="Test_Mat")]
    mesh_obj.data.vertices = [MagicMock(co=MockVector([0.0, 0.0, float(i) * 0.01])) for i in range(500)]
    mesh_obj.data.polygons = [MagicMock(vertices=[0, 1, 2, 3]) for _ in range(480)]
    mesh_obj.bound_box = [
        [-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [1.0, 1.0, 0.0], [-1.0, 1.0, 0.0],
        [-1.0, -1.0, 2.0], [1.0, -1.0, 2.0], [1.0, 1.0, 2.0], [-1.0, 1.0, 2.0],
    ]
    mesh_obj.matrix_world = MagicMock()
    mesh_obj.matrix_world.__matmul__ = lambda self, vec: vec

    cam_obj = MagicMock()
    cam_obj.name = "Test_Camera"
    cam_obj.type = "CAMERA"
    cam_obj.location = MockVector([0.0, -3.0, 1.5])
    cam_obj.rotation_euler = MockVector([1.48, 0.0, 0.0])
    cam_obj.scale = MockVector([1.0, 1.0, 1.0])
    cam_obj.parent = None
    cam_obj.children = []
    cam_obj.modifiers = []
    cam_obj.data.lens = 50.0

    scene.objects = [mesh_obj, cam_obj]
    scene.camera = cam_obj
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.engine = "BLENDER_EEVEE"

    mock_bpy.context.scene = scene
    mock_bpy.context.active_object = mesh_obj
    mock_bpy.data.scenes.get = lambda name=None, default=None: scene if (name is None or name == scene.name) else default
    objects_dict = {o.name: o for o in scene.objects}
    mock_objects = MagicMock()
    mock_objects.get.side_effect = lambda name, default=None: objects_dict.get(name, default)
    mock_objects.__getitem__.side_effect = lambda name: objects_dict[name]
    mock_objects.__contains__.side_effect = lambda name: name in objects_dict
    mock_objects.__iter__.side_effect = lambda: iter(scene.objects)
    mock_bpy.data.objects = mock_objects

    mock_mathutils = MagicMock()
    mock_mathutils.Vector = MockVector
    return mock_bpy, mock_mathutils


@pytest.fixture(scope="function")
def socket_server_factory(mock_bpy_environment) -> Generator[Any, None, None]:
    """Spawns an ephemeral MorphoMeshSocketServer instance with automatic timer queue draining."""
    mock_bpy, mock_mathutils = mock_bpy_environment
    listener_path = os.path.abspath("blender_addon/morphomesh/listener.py")
    spec = importlib.util.spec_from_file_location("morphomesh_listener_adv_mod", listener_path)
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
                        time.sleep(0.005)

                th = threading.Thread(target=_drain_loop, daemon=True)
                th.start()
                server._stop_drain = stop_drain

            return server, port

    yield _create_server

    for s in servers_to_stop:
        if hasattr(s, "_stop_drain"):
            s._stop_drain.set()
        s.stop()


def _recv_all_ndjson_responses(client: socket.socket, expected_count: int, timeout: float = 5.0) -> List[Dict[str, Any]]:
    """Helper to read and parse expected_count newline-delimited JSON responses from socket."""
    client.settimeout(timeout)
    responses = []
    buf = b""
    start = time.time()
    while len(responses) < expected_count and time.time() - start < timeout:
        try:
            chunk = client.recv(65536)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            line = line.strip()
            if line:
                try:
                    responses.append(json.loads(line.decode("utf-8")))
                except Exception as e:
                    responses.append({"parse_error": str(e), "raw": line.decode("utf-8", errors="replace")})
    return responses


# ==============================================================================
# CATEGORY 1: HIGH-FREQUENCY BURST STRESS TESTS
# ==============================================================================

class TestAdversarialBurstRequests:
    """Stress-tests high-frequency sequential bursts and concurrent client connections."""

    @pytest.mark.parametrize("burst_size", [10, 25, 50, 100])
    def test_burst_sequential_rapid_requests_single_socket(self, socket_server_factory, burst_size):
        """Sends burst_size rapid sequential requests over a single socket connection."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=5.0) as client:
            client.settimeout(5.0)

            # Generate distinct rapid requests
            requests = [
                {
                    "jsonrpc": "2.0",
                    "id": f"burst-{burst_size}-{i}",
                    "method": "morphomesh.ping",
                    "params": {"seq": i},
                }
                for i in range(burst_size)
            ]

            # Transmit entire batch in rapid single-call or continuous stream
            batch_bytes = b"".join(json.dumps(r).encode("utf-8") + b"\n" for r in requests)
            client.sendall(batch_bytes)

            # Read all responses
            responses = _recv_all_ndjson_responses(client, expected_count=burst_size, timeout=10.0)

            assert len(responses) == burst_size, (
                f"Expected {burst_size} responses for burst size {burst_size}, received {len(responses)}"
            )

            # Assert strict 1-to-1 correspondence and integrity
            for i, resp in enumerate(responses):
                expected_id = f"burst-{burst_size}-{i}"
                assert resp.get("id") == expected_id, f"ID mismatch at index {i}: {resp.get('id')} vs {expected_id}"
                assert resp.get("status") == "success"
                assert resp.get("result", {}).get("status") == "pong"
                assert resp.get("result", {}).get("blender_version") == "4.5.0"

    def test_burst_pipelining_mixed_workloads(self, socket_server_factory):
        """Sends 30 mixed light/heavy/failing requests pipelined in one transmission."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=5.0) as client:
            client.settimeout(5.0)

            requests = []
            for i in range(30):
                mode = i % 4
                if mode == 0:
                    req = {"jsonrpc": "2.0", "id": f"pipe-{i}", "method": "ping", "params": {}}
                elif mode == 1:
                    req = {"jsonrpc": "2.0", "id": f"pipe-{i}", "method": "morphomesh.get_scene_status", "params": {}}
                elif mode == 2:
                    req = {
                        "jsonrpc": "2.0",
                        "id": f"pipe-{i}",
                        "method": "morphomesh.execute_custom_script",
                        "params": {"code": f"val_{i} = {i} * 2", "return_variables": [f"val_{i}"]},
                    }
                else:
                    # Deliberately non-existent method to test error interleaving
                    req = {"jsonrpc": "2.0", "id": f"pipe-{i}", "method": "invalid_method_xyz", "params": {}}
                requests.append(req)

            client.sendall(b"".join(json.dumps(r).encode("utf-8") + b"\n" for r in requests))
            responses = _recv_all_ndjson_responses(client, expected_count=30, timeout=10.0)

            assert len(responses) == 30
            for i, resp in enumerate(responses):
                assert resp.get("id") == f"pipe-{i}"
                mode = i % 4
                if mode in (0, 1, 2):
                    assert resp.get("status") == "success", f"Request {i} unexpectedly failed: {resp}"
                    if mode == 2:
                        assert resp["result"]["returned_data"][f"val_{i}"] == i * 2
                else:
                    assert resp.get("status") == "error"

    def test_burst_concurrent_multi_client_connections(self, socket_server_factory):
        """5 concurrent client threads simultaneously burst 20 requests each (100 total)."""
        server, port = socket_server_factory(auto_drain=True)

        num_clients = 5
        requests_per_client = 20
        results = [None] * num_clients
        errors = [None] * num_clients

        def client_worker(client_idx: int):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=8.0) as sock:
                    sock.settimeout(8.0)
                    reqs = [
                        {
                            "jsonrpc": "2.0",
                            "id": f"c{client_idx}-req-{i}",
                            "method": "ping",
                            "params": {"c": client_idx, "i": i},
                        }
                        for i in range(requests_per_client)
                    ]
                    payload = b"".join(json.dumps(r).encode("utf-8") + b"\n" for r in reqs)
                    sock.sendall(payload)

                    resps = _recv_all_ndjson_responses(sock, expected_count=requests_per_client, timeout=8.0)
                    results[client_idx] = resps
            except Exception as exc:
                errors[client_idx] = exc

        threads = [threading.Thread(target=client_worker, args=(i,)) for i in range(num_clients)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        # Assert zero thread errors
        for i, err in enumerate(errors):
            assert err is None, f"Client {i} encountered error: {err}"

        # Assert every client received exactly its own 20 responses
        for client_idx, resps in enumerate(results):
            assert resps is not None, f"Client {client_idx} received no responses"
            assert len(resps) == requests_per_client, (
                f"Client {client_idx} expected {requests_per_client} responses, got {len(resps)}"
            )
            for i, r in enumerate(resps):
                assert r.get("id") == f"c{client_idx}-req-{i}", f"Client {client_idx} received crossed ID: {r.get('id')}"
                assert r.get("status") == "success"


# ==============================================================================
# CATEGORY 2: FRAGMENTED BYTE STREAMING TESTS (1 TO 5 BYTES)
# ==============================================================================

class TestAdversarialFragmentedStreaming:
    """Stress-tests NDJSON byte fragmentation down to single-byte increments."""

    @pytest.mark.parametrize("chunk_size", [1, 2, 3, 4, 5])
    def test_fragmented_streaming_deterministic_chunk_sizes(self, socket_server_factory, chunk_size):
        """Sends a valid NDJSON request split into fixed chunk sizes (1, 2, 3, 4, 5 bytes)."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=5.0) as client:
            client.settimeout(5.0)
            req = {
                "jsonrpc": "2.0",
                "id": f"frag-chunk-{chunk_size}",
                "method": "morphomesh.ping",
                "params": {"payload": "fragmentation_stress_test"},
            }
            raw = json.dumps(req).encode("utf-8") + b"\n"

            # Stream chunk_size bytes at a time
            for i in range(0, len(raw), chunk_size):
                client.sendall(raw[i : i + chunk_size])
                # Slight micro-sleep for small chunks to force TCP fragmentation
                if chunk_size <= 2:
                    time.sleep(0.0005)

            responses = _recv_all_ndjson_responses(client, expected_count=1, timeout=5.0)
            assert len(responses) == 1, f"Failed to reassemble {chunk_size}-byte fragmented stream"
            assert responses[0].get("id") == f"frag-chunk-{chunk_size}"
            assert responses[0].get("status") == "success"
            assert responses[0].get("result", {}).get("status") == "pong"

    def test_fragmented_streaming_random_1_to_5_bytes(self, socket_server_factory):
        """Sends request in pseudo-random chunk sizes between 1 and 5 bytes."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=5.0) as client:
            client.settimeout(5.0)
            req = {
                "jsonrpc": "2.0",
                "id": "frag-rand-1",
                "method": "morphomesh.get_scene_status",
                "params": {"detail": "high"},
            }
            raw = json.dumps(req).encode("utf-8") + b"\n"

            rng = random.Random(42)
            idx = 0
            while idx < len(raw):
                c_size = rng.randint(1, 5)
                chunk = raw[idx : idx + c_size]
                client.sendall(chunk)
                idx += c_size
                time.sleep(0.0005)

            responses = _recv_all_ndjson_responses(client, expected_count=1, timeout=5.0)
            assert len(responses) == 1
            assert responses[0].get("id") == "frag-rand-1"
            assert responses[0].get("status") == "success"
            assert "objects" in responses[0]["result"]

    def test_fragmented_streaming_multi_request_continuous_boundary_split(self, socket_server_factory):
        """3 back-to-back requests streamed 2 bytes at a time across newline boundaries."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=5.0) as client:
            client.settimeout(5.0)
            reqs = [
                {"jsonrpc": "2.0", "id": "cross-1", "method": "ping", "params": {}},
                {"jsonrpc": "2.0", "id": "cross-2", "method": "morphomesh.ping", "params": {}},
                {"jsonrpc": "2.0", "id": "cross-3", "method": "ping", "params": {}},
            ]
            combined = b"".join(json.dumps(r).encode("utf-8") + b"\n" for r in reqs)

            # Stream strictly 2 bytes at a time
            for i in range(0, len(combined), 2):
                client.sendall(combined[i : i + 2])
                time.sleep(0.0002)

            responses = _recv_all_ndjson_responses(client, expected_count=3, timeout=5.0)
            assert len(responses) == 3
            ids = [r.get("id") for r in responses]
            assert ids == ["cross-1", "cross-2", "cross-3"]


# ==============================================================================
# CATEGORY 3: GARBAGE & MALFORMED DATA INJECTION TESTS
# ==============================================================================

class TestAdversarialMalformedDataResilience:
    """Stress-tests invalid payloads, binary corruption, and connection recovery."""

    def test_malformed_raw_binary_garbage_recovery(self, socket_server_factory):
        """Non-UTF8 binary bytes followed immediately by valid request; verifies code -32700 error and recovery."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=4.0) as client:
            client.settimeout(4.0)

            # Inject illegal binary bytes ending with newline
            garbage = b"\x80\xff\xfe\xca\xfe\x00\x01\x02\n"
            client.sendall(garbage)
            time.sleep(0.05)

            # Follow immediately with valid ping request
            valid_req = {"jsonrpc": "2.0", "id": "valid-after-binary", "method": "morphomesh.ping", "params": {}}
            client.sendall(json.dumps(valid_req).encode("utf-8") + b"\n")

            responses = _recv_all_ndjson_responses(client, expected_count=2, timeout=5.0)
            assert len(responses) >= 2

            # Response 1: Parse error (-32700)
            err_resp = responses[0]
            assert err_resp.get("status") == "error"
            assert err_resp.get("error", {}).get("code") == -32700

            # Response 2: Clean success
            ok_resp = responses[1]
            assert ok_resp.get("id") == "valid-after-binary"
            assert ok_resp.get("status") == "success"
            assert ok_resp.get("result", {}).get("status") == "pong"

    def test_malformed_corrupted_json_syntax_recovery(self, socket_server_factory):
        """Broken JSON syntax followed immediately by valid get_scene_status."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=4.0) as client:
            client.settimeout(4.0)

            broken_json = b'{"jsonrpc": 2.0, "method": unquoted_literal, "params": }\n'
            client.sendall(broken_json)
            time.sleep(0.05)

            valid_req = {"jsonrpc": "2.0", "id": "scene-after-syntax-err", "method": "morphomesh.get_scene_status", "params": {}}
            client.sendall(json.dumps(valid_req).encode("utf-8") + b"\n")

            responses = _recv_all_ndjson_responses(client, expected_count=2, timeout=5.0)
            assert len(responses) == 2
            assert responses[0].get("status") == "error"
            assert responses[0].get("error", {}).get("code") == -32700

            assert responses[1].get("id") == "scene-after-syntax-err"
            assert responses[1].get("status") == "success"
            assert "objects" in responses[1]["result"]

    def test_malformed_truncated_json_followed_by_valid(self, socket_server_factory):
        """Unclosed JSON line followed immediately by valid ping."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=4.0) as client:
            client.settimeout(4.0)

            truncated = b'{"jsonrpc": "2.0", "method": "morphomesh.ping", "params": {\n'
            client.sendall(truncated)
            time.sleep(0.05)

            valid_req = {"jsonrpc": "2.0", "id": "valid-after-trunc", "method": "ping", "params": {}}
            client.sendall(json.dumps(valid_req).encode("utf-8") + b"\n")

            responses = _recv_all_ndjson_responses(client, expected_count=2, timeout=5.0)
            assert len(responses) == 2
            assert responses[0].get("status") == "error"
            assert responses[0].get("error", {}).get("code") == -32700
            assert responses[1].get("id") == "valid-after-trunc"
            assert responses[1].get("status") == "success"

    def test_malformed_non_dict_json_primitives(self, socket_server_factory):
        """Non-dict JSON primitives (string, int, list, bool) return -32600 Invalid Request."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=4.0) as client:
            client.settimeout(4.0)

            primitives = [
                b'"plain_json_string"\n',
                b'999999\n',
                b'[1, 2, 3, "array"]\n',
                b'true\n',
            ]
            for p in primitives:
                client.sendall(p)
                time.sleep(0.02)

            # Follow with valid request
            valid_req = {"jsonrpc": "2.0", "id": "valid-after-primitives", "method": "ping", "params": {}}
            client.sendall(json.dumps(valid_req).encode("utf-8") + b"\n")

            responses = _recv_all_ndjson_responses(client, expected_count=5, timeout=5.0)
            assert len(responses) == 5

            # All 4 primitives should produce -32600 error
            for r in responses[:4]:
                assert r.get("status") == "error"
                assert r.get("error", {}).get("code") == -32600
                assert "Expected JSON object dict" in r.get("error", {}).get("message", "")

            # Valid request succeeds
            assert responses[4].get("id") == "valid-after-primitives"
            assert responses[4].get("status") == "success"

    def test_malformed_chaos_fuzzing_interleaving(self, socket_server_factory):
        """Rapid sequence alternating valid, garbage, broken, whitespace, and valid frames."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=5.0) as client:
            client.settimeout(5.0)

            frames = [
                b'{"jsonrpc": "2.0", "id": "fuzz-1", "method": "ping", "params": {}}\n',
                b'GARBAGE_LINE_12345\n',
                b'{"jsonrpc": "2.0", "id": "fuzz-2", "method": "ping", "params": {}}\n',
                b'{"broken": "missing_bracket"\n',
                b'\n\n  \t  \n',  # whitespace lines should be ignored
                b'{"jsonrpc": "2.0", "id": "fuzz-3", "method": "ping", "params": {}}\n',
                b'42\n',  # primitive non-dict
                b'{"jsonrpc": "2.0", "id": "fuzz-4", "method": "ping", "params": {}}\n',
            ]

            payload = b"".join(frames)
            client.sendall(payload)

            # Expect 6 responses: fuzz-1 (ok), garbage (err), fuzz-2 (ok), broken (err), fuzz-3 (ok), 42 (err), fuzz-4 (ok) -> 7 total
            responses = _recv_all_ndjson_responses(client, expected_count=7, timeout=6.0)
            assert len(responses) == 7

            expected_outcomes = [
                ("fuzz-1", "success"),
                (None, "error"),
                ("fuzz-2", "success"),
                (None, "error"),
                ("fuzz-3", "success"),
                (None, "error"),
                ("fuzz-4", "success"),
            ]

            for i, (exp_id, exp_status) in enumerate(expected_outcomes):
                assert responses[i].get("status") == exp_status, f"Frame {i} status mismatch: {responses[i]}"
                if exp_id is not None:
                    assert responses[i].get("id") == exp_id

    def test_malformed_unclosed_data_without_newline_then_recovered(self, socket_server_factory):
        """Garbage sent without newline, then newline appended, then valid request processed."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=4.0) as client:
            client.settimeout(4.0)

            # Send garbage without newline
            client.sendall(b"CORRUPTED_RAW_STREAM")
            time.sleep(0.05)

            # Send newline to complete the invalid line
            client.sendall(b"\n")
            time.sleep(0.05)

            # Send valid request
            valid_req = {"jsonrpc": "2.0", "id": "clean-recovery", "method": "ping", "params": {}}
            client.sendall(json.dumps(valid_req).encode("utf-8") + b"\n")

            responses = _recv_all_ndjson_responses(client, expected_count=2, timeout=5.0)
            assert len(responses) == 2
            assert responses[0].get("status") == "error"
            assert responses[1].get("id") == "clean-recovery"
            assert responses[1].get("status") == "success"


# ==============================================================================
# CATEGORY 4: LARGE PAYLOAD HANDLING (>500KB JSON PAYLOADS)
# ==============================================================================

class TestAdversarialLargePayloadHandling:
    """Stress-tests large payload streaming (>500KB up to 1MB) without truncation or deadlocks."""

    def test_large_payload_request_client_to_server_600kb(self, socket_server_factory):
        """Sends a >600KB JSON-RPC request to the socket server."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=10.0) as client:
            client.settimeout(10.0)

            # Construct 600,000 character string payload inside params
            large_str = "A" * 600000
            req = {
                "jsonrpc": "2.0",
                "id": "large-req-600k",
                "method": "morphomesh.execute_custom_script",
                "params": {
                    "code": "result = 42",
                    "return_variables": ["result"],
                    "large_data": large_str,
                },
            }
            raw = json.dumps(req).encode("utf-8") + b"\n"
            assert len(raw) > 600000, f"Payload size {len(raw)} is not > 600KB"

            client.sendall(raw)

            responses = _recv_all_ndjson_responses(client, expected_count=1, timeout=10.0)
            assert len(responses) == 1
            assert responses[0].get("id") == "large-req-600k"
            assert responses[0].get("status") == "success"
            assert responses[0]["result"]["returned_data"]["result"] == 42

    def test_large_payload_response_server_to_client_700kb(self, socket_server_factory):
        """Server returns a >700KB JSON-RPC response; verifies multi-chunk assembly without truncation."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=10.0) as client:
            client.settimeout(10.0)

            # Request script to generate a 700KB string in return_variables
            req = {
                "jsonrpc": "2.0",
                "id": "large-resp-700k",
                "method": "morphomesh.execute_custom_script",
                "params": {
                    "code": "big_str = 'X' * 700000",
                    "return_variables": ["big_str"],
                },
            }
            client.sendall(json.dumps(req).encode("utf-8") + b"\n")

            responses = _recv_all_ndjson_responses(client, expected_count=1, timeout=10.0)
            assert len(responses) == 1
            resp = responses[0]
            assert resp.get("id") == "large-resp-700k"
            assert resp.get("status") == "success"

            ret_str = resp["result"]["returned_data"]["big_str"]
            assert len(ret_str) == 700000
            assert ret_str[:10] == "XXXXXXXXXX"

    def test_large_payload_bidirectional_roundtrip_800kb(self, socket_server_factory):
        """Bidirectional roundtrip: client sends 500KB data, server echoes and expands to 800KB."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=12.0) as client:
            client.settimeout(12.0)

            req = {
                "jsonrpc": "2.0",
                "id": "large-bidi-800k",
                "method": "morphomesh.execute_custom_script",
                "params": {
                    "code": "echo_out = 'Y' * 800000",
                    "return_variables": ["echo_out"],
                    "inbound_padding": "Z" * 500000,
                },
            }
            raw = json.dumps(req).encode("utf-8") + b"\n"
            assert len(raw) > 500000

            client.sendall(raw)

            responses = _recv_all_ndjson_responses(client, expected_count=1, timeout=12.0)
            assert len(responses) == 1
            resp = responses[0]
            assert resp.get("id") == "large-bidi-800k"
            assert resp.get("status") == "success"
            assert len(resp["result"]["returned_data"]["echo_out"]) == 800000

    def test_large_payload_1mb_high_stress(self, socket_server_factory):
        """Extreme 1MB payload stress test to assert zero buffer overrun or memory exhaustion."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=15.0) as client:
            client.settimeout(15.0)

            req = {
                "jsonrpc": "2.0",
                "id": "stress-1mb",
                "method": "ping",
                "params": {"padding_1mb": "M" * 1000000},
            }
            raw = json.dumps(req).encode("utf-8") + b"\n"
            assert len(raw) > 1000000

            client.sendall(raw)

            responses = _recv_all_ndjson_responses(client, expected_count=1, timeout=15.0)
            assert len(responses) == 1
            assert responses[0].get("id") == "stress-1mb"
            assert responses[0].get("status") == "success"

    def test_large_payload_via_bridge_client_send_socket_request(self, socket_server_factory):
        """Verifies BlenderBridge.send_socket_request() handles >500KB responses seamlessly."""
        server, port = socket_server_factory(auto_drain=True)
        bridge = BlenderBridge(host="127.0.0.1", port=port, socket_timeout=15.0)

        # Send script returning 650KB data
        res = bridge.send_socket_request(
            method="morphomesh.execute_custom_script",
            params={
                "code": "data_blob = 'W' * 650000",
                "return_variables": ["data_blob"],
            },
            timeout=15.0,
        )

        assert isinstance(res, dict)
        assert res.get("success") is True
        returned = res.get("returned_data", {}).get("data_blob", "")
        assert len(returned) == 650000


# ==============================================================================
# CATEGORY 5: DEADLOCK, HANG & LIFECYCLE RESILIENCE TESTS
# ==============================================================================

class TestAdversarialDeadlockAndLifecycleResilience:
    """Stress-tests disconnect mid-packet, half-close, descriptor management, and timer immortality."""

    def test_immediate_client_disconnect_mid_packet(self, socket_server_factory):
        """Client disconnects immediately after partial packet; server must clean up descriptor and keep running."""
        server, port = socket_server_factory(auto_drain=True)

        # Rapid connect, partial write, immediate close
        with socket.create_connection(("127.0.0.1", port), timeout=2.0) as client:
            client.sendall(b'{"jsonrpc": "2.0", "metho')
            # Socket closes upon exit of with-block

        time.sleep(0.1)
        assert len(server._clients) == 0

        # Server must still be fully responsive to a new client
        with socket.create_connection(("127.0.0.1", port), timeout=2.0) as client2:
            client2.settimeout(2.0)
            req = {"jsonrpc": "2.0", "id": "after-abrupt-close", "method": "ping", "params": {}}
            client2.sendall(json.dumps(req).encode("utf-8") + b"\n")
            raw = client2.recv(4096)
            resp = json.loads(raw.decode("utf-8").strip())
            assert resp.get("id") == "after-abrupt-close"
            assert resp.get("status") == "success"

    def test_client_half_close_shutdown_wr(self, socket_server_factory):
        """Client sends request, shuts down write half of TCP connection, and reads response."""
        server, port = socket_server_factory(auto_drain=True)

        with socket.create_connection(("127.0.0.1", port), timeout=3.0) as client:
            client.settimeout(3.0)
            req = {"jsonrpc": "2.0", "id": "half-close-1", "method": "ping", "params": {}}
            client.sendall(json.dumps(req).encode("utf-8") + b"\n")

            # Half-close write channel: server sees EOF on recv
            client.shutdown(socket.SHUT_WR)

            responses = _recv_all_ndjson_responses(client, expected_count=1, timeout=3.0)
            assert len(responses) == 1
            assert responses[0].get("id") == "half-close-1"
            assert responses[0].get("status") == "success"

    def test_rapid_client_churn_descriptor_leak_prevention(self, socket_server_factory):
        """50 sequential connections opened and closed rapidly; asserts zero leaked socket descriptors."""
        server, port = socket_server_factory(auto_drain=True)

        for i in range(50):
            with socket.create_connection(("127.0.0.1", port), timeout=2.0) as client:
                req = {"jsonrpc": "2.0", "id": f"churn-{i}", "method": "ping", "params": {}}
                client.sendall(json.dumps(req).encode("utf-8") + b"\n")
                raw = client.recv(4096)
                assert b"pong" in raw

        time.sleep(0.15)
        assert len(server._clients) == 0, f"Leaked clients in server set: {len(server._clients)}"

    def test_timer_immortality_under_deliberate_dispatch_crash(self, socket_server_factory):
        """Server _drain_queue guarantees return 0.02 even when _dispatch raises unexpected exception."""
        server, port = socket_server_factory(auto_drain=False)

        # Monkey-patch _dispatch to simulate unhandled internal error
        orig_dispatch = server._dispatch
        server._dispatch = MagicMock(side_effect=RuntimeError("Adversarial disaster in main thread"))

        mock_client = MagicMock()
        bad_cmd = {"jsonrpc": "2.0", "id": "boom", "method": "ping", "params": {}}
        server.command_queue.put((bad_cmd, mock_client))

        # Must NOT raise exception, must return exactly 0.02
        interval = server._drain_queue()
        assert interval == 0.02, f"Timer dropped! Expected 0.02, got {interval}"

        # Client must receive error response
        assert mock_client.sendall.called
        sent = mock_client.sendall.call_args[0][0]
        resp = json.loads(sent.decode("utf-8").strip())
        assert resp.get("status") == "error"
        assert resp.get("id") == "boom"

        # Restore dispatch and verify recovery
        server._dispatch = orig_dispatch
        ok_cmd = {"jsonrpc": "2.0", "id": "recovered", "method": "ping", "params": {}}
        server.command_queue.put((ok_cmd, mock_client))

        interval2 = server._drain_queue()
        assert interval2 == 0.02
        sent2 = mock_client.sendall.call_args[0][0]
        resp2 = json.loads(sent2.decode("utf-8").strip())
        assert resp2.get("id") == "recovered"
        assert resp2.get("status") == "success"
