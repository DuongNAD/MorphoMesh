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
6. Client Inspection Methods & Fallback Fix: No false fallback on image_path/defects/camera_name, typed client methods.
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
    """Creates a hermetic mock Blender Python environment for listener testing."""
    mock_bpy = MagicMock()
    mock_bpy.app.version = (4, 5, 0)
    mock_bpy.app.timers.is_registered.return_value = False
    mock_bpy.app.background = False

    scene = MagicMock()
    scene.name = "Scene_MorphoMesh_QA"

    # Mesh Object
    mesh_obj = MagicMock()
    mesh_obj.name = "Hero_Body_Mesh"
    mesh_obj.type = "MESH"
    mesh_obj.location = MockVector([0.0, 0.0, 1.0])
    mesh_obj.rotation_euler = MockVector([0.0, 0.0, 0.0])
    mesh_obj.scale = MockVector([1.0, 1.0, 1.0])
    mesh_obj.parent = None
    mesh_obj.children = []
    mesh_obj.modifiers = []
    mat = MagicMock()
    mat.name = "Mat_Skin_SSS"
    mesh_obj.data.materials = [mat]
    mesh_obj.data.vertices = [MagicMock(co=MockVector([0.0, 0.0, float(i) * 0.001])) for i in range(2400)]
    mesh_obj.data.polygons = [MagicMock(vertices=[0, 1, 2, 3]) for _ in range(2380)]
    mesh_obj.bound_box = [
        [-0.5, -0.2, 0.0],
        [0.5, -0.2, 0.0],
        [0.5, 0.2, 0.0],
        [-0.5, 0.2, 0.0],
        [-0.5, -0.2, 1.7],
        [0.5, -0.2, 1.7],
        [0.5, 0.2, 1.7],
        [-0.5, 0.2, 1.7],
    ]
    mesh_obj.matrix_world = MagicMock()
    mesh_obj.matrix_world.__matmul__ = lambda self, vec: vec

    # Camera Object
    cam_obj = MagicMock()
    cam_obj.name = "Camera_Inspector"
    cam_obj.type = "CAMERA"
    cam_obj.location = MockVector([0.0, -3.2, 1.6])
    cam_obj.rotation_euler = MockVector([1.48, 0.0, 0.0])
    cam_obj.scale = MockVector([1.0, 1.0, 1.0])
    cam_obj.parent = None
    cam_obj.children = []
    cam_obj.modifiers = []
    cam_obj.data.lens = 50.0

    # Light Object
    light_obj = MagicMock()
    light_obj.name = "Light_Studio_Key"
    light_obj.type = "LIGHT"
    light_obj.location = MockVector([2.0, -2.5, 3.0])
    light_obj.rotation_euler = MockVector([0.0, 0.0, 0.0])
    light_obj.scale = MockVector([1.0, 1.0, 1.0])
    light_obj.parent = None
    light_obj.children = []
    light_obj.modifiers = []
    light_obj.data.type = "AREA"
    light_obj.data.energy = 500.0
    light_obj.data.color = (1.0, 1.0, 1.0)

    # Armature Object
    arm_obj = MagicMock()
    arm_obj.name = "Armature_Rigify_Human"
    arm_obj.type = "ARMATURE"
    arm_obj.location = MockVector([0.0, 0.0, 0.0])
    arm_obj.rotation_euler = MockVector([0.0, 0.0, 0.0])
    arm_obj.scale = MockVector([1.0, 1.0, 1.0])
    arm_obj.parent = None
    arm_obj.children = [mesh_obj]
    mesh_obj.parent = arm_obj
    arm_obj.modifiers = []
    bone_mocks = []
    for i in range(163):
        b = MagicMock()
        b.name = f"DEF-bone_{i}"
        bone_mocks.append(b)
    arm_obj.data.bones = bone_mocks

    scene.objects = [mesh_obj, cam_obj, light_obj, arm_obj]
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
            time.sleep(0.05)
            assert len(server._clients) >= 1

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

    def test_graceful_timer_deregistration_on_stop(self, socket_server_factory):
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


# ==============================================================================
# 6. CLIENT INSPECTION METHODS & FALLBACK FIX TESTS
# ==============================================================================

class TestBridgeClientInspectionMethodsAndFallbackFix:
    """Verifies typed client inspection methods and that execute() doesn't falsely fall back."""

    def test_execute_does_not_fallback_on_image_path(self, monkeypatch):
        bridge = BlenderBridge()
        monkeypatch.setattr(bridge, "is_interactive_connected", lambda: True)

        def mock_send(method, params, timeout=60.0):
            if method == "execute_code":
                return {"image_path": "/tmp/test.png", "resolution": [1024, 1024]}
            raise RuntimeError("Direct RPC not implemented")

        monkeypatch.setattr(bridge, "send_socket_request", mock_send)
        monkeypatch.setattr(
            bridge,
            "_dispatch_headless",
            MagicMock(side_effect=AssertionError("Should NOT call headless fallback")),
        )
        res = bridge.execute("morphomesh.render_preview", {})
        assert res["image_path"] == "/tmp/test.png"

    def test_execute_does_not_fallback_on_camera_or_defects(self, monkeypatch):
        bridge = BlenderBridge()
        monkeypatch.setattr(bridge, "is_interactive_connected", lambda: True)

        def mock_send(method, params, timeout=60.0):
            if method == "execute_code":
                code = params.get("code", "")
                if "method = 'morphomesh.setup_inspector_camera'" in code or 'method = "morphomesh.setup_inspector_camera"' in code:
                    return {"camera_name": "MorphoMesh_Inspector_Camera", "viewpoint": "front"}
                return {"defects": [], "defect_count": 0, "status": "success"}
            raise RuntimeError("Direct RPC not implemented")

        monkeypatch.setattr(bridge, "send_socket_request", mock_send)
        monkeypatch.setattr(
            bridge,
            "_dispatch_headless",
            MagicMock(side_effect=AssertionError("Should NOT call headless fallback")),
        )

        res_cam = bridge.execute("morphomesh.setup_inspector_camera", {})
        assert res_cam["camera_name"] == "MorphoMesh_Inspector_Camera"

        res_crit = bridge.execute("morphomesh.critique_visual_quality", {})
        assert res_crit["defects"] == []

    def test_client_inspection_methods_exist_and_callable(self, monkeypatch):
        bridge = BlenderBridge()
        assert hasattr(bridge, "capture_viewport")
        assert hasattr(bridge, "setup_inspector_camera")
        assert hasattr(bridge, "critique_visual_quality")

        monkeypatch.setattr(
            bridge,
            "execute",
            lambda method, params, timeout=30.0: {"method": method, "params": params, "status": "success"},
        )

        res_cap = bridge.capture_viewport(resolution=(512, 512), shading_mode="SOLID")
        assert res_cap["method"] == "morphomesh.capture_viewport"
        assert res_cap["params"]["resolution"] == [512, 512]

        res_cam = bridge.setup_inspector_camera(viewpoint="head", focal_length=85.0)
        assert res_cam["method"] == "morphomesh.setup_inspector_camera"
        assert res_cam["params"]["viewpoint"] == "head"
        assert res_cam["params"]["focal_length"] == 85.0

        res_crit = bridge.critique_visual_quality(character_name="TestChar")
        assert res_crit["method"] == "morphomesh.critique_visual_quality"
        assert res_crit["params"]["character_name"] == "TestChar"

    def test_ndjson_trailing_newline_sent(self, monkeypatch):
        bridge = BlenderBridge()
        sent_payloads = []
        mock_sock = MagicMock()
        mock_sock.sendall.side_effect = lambda data: sent_payloads.append(data)
        mock_sock.recv.side_effect = [b'{"jsonrpc":"2.0","result":{"status":"pong"}}\n', b'']
        monkeypatch.setattr(socket, "create_connection", MagicMock(return_value=mock_sock))

        res = bridge.send_socket_request("ping", {})
        assert res == {"status": "pong"}
        assert sent_payloads[0].endswith(b"\n")

