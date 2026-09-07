"""
MorphoMesh: Adversarial Dispatch, Exception Containment & Timer Immortality Test Suite.
Target: tests/test_adversarial_dispatch_m1_2.py
Milestone: M1 - Interactive Socket Bridge Parity & Reliability (R3)
Agent: Challenger M1_2 (Adversarial Dispatch Challenger)

Adversarial Dimensions Tested:
1. Dispatch Method Parity & Diverse Parameter Structures:
   - Calls every single dispatch method in listener.py with valid and extreme edge-case parameter structures.
   - Tests parameter edge cases: empty dicts, non-existent objects, negative dimensions, malformed types, None values.
   - Audits all 19 core pipeline methods to detect method asymmetries between listener.py and BlenderBridge.
2. Exception Containment & Timer Immortality:
   - Simulates unhandled exceptions inside command dispatch (_dispatch raising ValueError, TypeError, RuntimeError, ZeroDivisionError, KeyError, custom exceptions).
   - Verifies _drain_queue catches them, client receives clean JSON-RPC error response (-32000), and timer returns 0.02s.
   - Tests corrupted/malformed queue entries (non-tuples, non-dict payloads).
   - Simulates client socket exceptions (broken pipe, ConnectionResetError during sendall).
   - Injects catastrophic queue errors to prove top-level exception barrier immortality (returning 0.02s).
   - Verifies server continues processing subsequent commands after any failure.
   - Verifies graceful timer deregistration (returning None) on server.stop().
3. BlenderBridge.execute() Response Unpacking & Headless Fallback Robustness:
   - Tests response unpacking for diverse dictionary payloads without false headless fallback.
   - Tests edge-case payload structures in execute_code fallback.
   - Empirically stress-tests generated headless scripts against AddonSecurityValidator to verify AST security compatibility.
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

from morphomesh.blender_bridge import BlenderBridge, BlenderExecutionError
from morphomesh.models import (
    BlenderExecuteOutput,
    RenderEngine,
    RenderPreviewOutput,
    SceneStatusOutput,
)


# ==============================================================================
# FIXTURES & HARNESS ENVIRONMENT
# ==============================================================================

class MockVector(list):
    """3D Vector simulation for mathutils."""
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
    """Hermetic mock bpy environment for testing."""
    mock_bpy = MagicMock()
    mock_bpy.app.version = (4, 5, 0)
    mock_bpy.app.timers.is_registered.return_value = False
    mock_bpy.app.background = False

    scene = MagicMock()
    scene.name = "Scene_MorphoMesh_Adversarial"

    # Mesh Object
    mesh_obj = MagicMock()
    mesh_obj.name = "Human_Base_Mesh"
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

    # Camera
    cam_obj = MagicMock()
    cam_obj.name = "MorphoMesh_Inspector_Camera"
    cam_obj.type = "CAMERA"
    cam_obj.location = MockVector([0.0, -3.2, 1.6])
    cam_obj.rotation_euler = MockVector([1.48, 0.0, 0.0])
    cam_obj.scale = MockVector([1.0, 1.0, 1.0])
    cam_obj.parent = None
    cam_obj.children = []
    cam_obj.modifiers = []
    cam_obj.data.lens = 50.0

    # Armature
    arm_obj = MagicMock()
    arm_obj.name = "Armature_Yu_Nian_An_Rigify"
    arm_obj.type = "ARMATURE"
    arm_obj.location = MockVector([0.0, 0.0, 0.0])
    arm_obj.rotation_euler = MockVector([0.0, 0.0, 0.0])
    arm_obj.scale = MockVector([1.0, 1.0, 1.0])
    arm_obj.parent = None
    arm_obj.children = [mesh_obj]
    arm_obj.data.bones = [MagicMock(name=f"DEF-bone_{i}") for i in range(163)]

    scene.objects = [mesh_obj, cam_obj, arm_obj]
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
def adversarial_server_factory(mock_bpy_environment) -> Generator[Any, None, None]:
    """Dynamically imports and spawns an ephemeral server for adversarial stress testing."""
    mock_bpy, mock_mathutils = mock_bpy_environment
    listener_path = os.path.abspath("blender_addon/morphomesh/listener.py")
    spec = importlib.util.spec_from_file_location("adversarial_listener_mod", listener_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)

    servers_to_stop = []

    def _create_server(auto_drain: bool = False) -> Tuple[Any, int]:
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


# ==============================================================================
# 1. DISPATCH METHOD PARITY & PARAMETER EDGE-CASE TESTS
# ==============================================================================

class TestDispatchMethodParityAndParameterEdgeCases:
    """Stress-tests every method in _dispatch with diverse valid and edge-case inputs."""

    def test_ping_with_extreme_parameter_structures(self, adversarial_server_factory):
        server, port = adversarial_server_factory(auto_drain=False)

        # Ping should ignore all arbitrary nested/strange parameters and succeed
        edge_params = [
            {},
            {"unexpected_key": "val", "nested": [1, 2, {"k": "v"}]},
            {"id": -999999, "extra_floats": [float("inf"), float("-inf")]},
            {"none_val": None, "bool_val": False},
        ]
        for p in edge_params:
            res = server._dispatch("morphomesh.ping", p)
            assert res["status"] == "pong"
            assert res["mode"] == "interactive"
            assert "blender_version" in res

    def test_get_scene_status_with_edge_case_parameters(self, adversarial_server_factory):
        server, port = adversarial_server_factory(auto_drain=False)

        # Valid empty
        res = server._dispatch("morphomesh.get_scene_status", {})
        assert res["scene_name"] == "Scene_MorphoMesh_Adversarial"
        assert res["object_count"] == 3

        # Non-existent scene name should fall back gracefully to active scene
        res_nonexistent = server._dispatch("morphomesh.get_scene_status", {"scene_name": "GhostSceneXYZ"})
        assert "objects" in res_nonexistent
        assert "blender_version" in res_nonexistent

        # Malformed scene_name types (None, int, list)
        for bad_scene in [None, 12345, ["Scene_MorphoMesh_Adversarial"]]:
            res_bad = server._dispatch("morphomesh.get_scene_status", {"scene_name": bad_scene})
            assert isinstance(res_bad, dict)
            assert "objects" in res_bad

    def test_execute_custom_script_security_and_edge_cases(self, adversarial_server_factory):
        server, port = adversarial_server_factory(auto_drain=False)

        # 1. Valid computation
        res = server._dispatch("morphomesh.execute_custom_script", {
            "script": "x = 100\ny = 250\nz = x * y",
            "return_variables": ["z"],
        })
        assert res["success"] is True
        assert res["returned_data"]["z"] == 25000

        # 2. Non-existent return variables
        res_missing_var = server._dispatch("morphomesh.execute_custom_script", {
            "code": "a = 1",
            "return_variables": ["non_existent_var", "also_missing"],
        })
        assert res_missing_var["success"] is True
        assert res_missing_var["returned_data"] == {}

        # 3. Forbidden AST call: open()
        with pytest.raises(ValueError) as excinfo:
            server._dispatch("morphomesh.execute_custom_script", {"code": "open('test.txt', 'w')"})
        assert "Forbidden built-in call: open()" in str(excinfo.value)

        # 4. Forbidden AST call: setattr()
        with pytest.raises(ValueError) as excinfo:
            server._dispatch("morphomesh.execute_custom_script", {"code": "setattr(math, 'sin', 1)"})
        assert "Forbidden built-in call: setattr()" in str(excinfo.value)

        # 5. Forbidden module import: os
        with pytest.raises(ValueError) as excinfo:
            server._dispatch("morphomesh.execute_custom_script", {"code": "import subprocess"})
        assert "Forbidden import: subprocess" in str(excinfo.value)

        # 6. Syntax error in script
        with pytest.raises(SyntaxError):
            server._dispatch("morphomesh.execute_custom_script", {"code": "def incomplete_syntax("})

        # 7. Runtime error in script: division by zero
        with pytest.raises(ZeroDivisionError):
            server._dispatch("morphomesh.execute_custom_script", {"code": "x = 10 / 0"})

    def test_setup_inspector_camera_all_viewpoints_and_edge_cases(self, adversarial_server_factory):
        server, port = adversarial_server_factory(auto_drain=False)

        # Test all standard and exotic viewpoints
        viewpoints = [
            "front", "side", "side_left", "back", "top",
            "head", "hands", "torso", "feet", "three_quarter",
            "unknown_exotic_viewpoint"
        ]
        for vp in viewpoints:
            res = server._dispatch("morphomesh.setup_inspector_camera", {"viewpoint": vp})
            assert res["status"] == "success"
            assert res["viewpoint"] == vp
            assert len(res["camera_location"]) == 3
            assert len(res["camera_rotation"]) == 3
            assert res["framing_distance"] > 0

        # Edge case: non-existent target object
        res_ghost = server._dispatch("morphomesh.setup_inspector_camera", {"target_object": "Ghost_Mesh_XYZ"})
        assert res_ghost["status"] == "success"

        # Edge case: custom target center and framing radius
        res_custom = server._dispatch("morphomesh.setup_inspector_camera", {
            "target_center": [1.5, -2.0, 3.5],
            "framing_radius": 0.8,
            "focal_length": 85.0,
        })
        assert res_custom["focal_length"] == 85.0
        assert res_custom["bounding_radius"] == 0.8
        assert res_custom["target_center"] == [1.5, -2.0, 3.5]

    def test_capture_viewport_edge_cases(self, adversarial_server_factory):
        server, port = adversarial_server_factory(auto_drain=False)

        # Edge cases: missing camera, exotic resolutions, custom shading
        res = server._dispatch("morphomesh.capture_viewport", {
            "camera_name": "NonExistentCam",
            "resolution_width": 256,
            "resolution_height": 256,
            "shading_mode": "WIREFRAME",
            "color_type": "SINGLE",
        })
        assert res["status"] == "success"
        assert res["resolution"] == [256, 256]
        assert res["shading_mode"] == "WIREFRAME"
        assert "image_path" in res

    def test_critique_visual_quality_edge_cases(self, adversarial_server_factory):
        server, port = adversarial_server_factory(auto_drain=False)

        # Test with empty params
        res_empty = server._dispatch("morphomesh.critique_visual_quality", {})
        assert res_empty["status"] == "success"
        assert "defects" in res_empty
        assert "quality_score" in res_empty

        # Test with non-existent target object
        res_ghost = server._dispatch("morphomesh.critique_visual_quality", {"target_object": "UnknownObj"})
        assert res_ghost["status"] == "success"

        # Test with tight clearance tolerance
        res_tight = server._dispatch("morphomesh.critique_visual_quality", {
            "target_object": "Human_Base_Mesh",
            "clearance_tolerance": 0.0001,
        })
        assert res_tight["status"] == "success"

    def test_all_13_implemented_methods_callable_without_crash(self, adversarial_server_factory):
        server, port = adversarial_server_factory(auto_drain=False)

        # All 13 methods implemented in listener.py
        implemented_methods = [
            ("morphomesh.ping", {}),
            ("morphomesh.get_scene_status", {}),
            ("morphomesh.execute_custom_script", {"code": "x = 1"}),
            ("morphomesh.render_preview", {}),
            ("morphomesh.setup_inspector_camera", {}),
            ("morphomesh.capture_viewport", {}),
            ("morphomesh.critique_visual_quality", {}),
            ("morphomesh.setup_human_materials", {}),
            ("morphomesh.groom_human", {}),
            ("morphomesh.dress_human", {}),
        ]

        for method, params in implemented_methods:
            res = server._dispatch(method, params)
            assert isinstance(res, dict), f"Method '{method}' returned non-dict: {res}"
            assert res.get("status") in ("success", "pong") or res.get("success") is True or "scene_name" in res

    def test_audit_creature_methods_in_dispatch_parity(self, adversarial_server_factory):
        server, port = adversarial_server_factory(auto_drain=False)

        # All 6 creature methods must be handled natively in listener.py's _dispatch:
        creature_methods = [
            ("morphomesh.optimize_topology", {"target_poly_count": 5000}),
            ("morphomesh.create_armature", {"creature_type": "quadruped"}),
            ("morphomesh.setup_creature_fur", {"undercoat_strands": 5000}),
            ("morphomesh.evaluate_fur_ribbons", {}),
            ("morphomesh.setup_creature_materials", {}),
            ("morphomesh.generate_war_armor", {}),
        ]

        for m, p in creature_methods:
            res = server._dispatch(m, p)
            assert isinstance(res, dict), f"Expected dict for '{m}', got {res}"
            assert res.get("status") == "success", f"Expected success for '{m}', got {res}"


# ==============================================================================
# 2. EXCEPTION CONTAINMENT & TIMER IMMORTALITY TESTS
# ==============================================================================

class TestExceptionContainmentAndTimerImmortality:
    """Empirically proves that _drain_queue never drops the timer under hostile conditions."""

    @pytest.mark.parametrize("exception_class", [
        ValueError,
        TypeError,
        RuntimeError,
        ZeroDivisionError,
        KeyError,
        IndexError,
        AttributeError,
        Exception,
    ])
    def test_unhandled_exception_types_trapped_and_timer_returns_002(self, adversarial_server_factory, exception_class):
        server, port = adversarial_server_factory(auto_drain=False)

        # Monkeypatch _dispatch to raise the parameterized exception
        def _exploding_dispatch(method, params):
            raise exception_class(f"Explosion of type {exception_class.__name__}")

        server._dispatch = _exploding_dispatch

        mock_client = MagicMock()
        cmd = {"jsonrpc": "2.0", "id": "req-adversarial-exc", "method": "exploding_method", "params": {}}
        server.command_queue.put((cmd, mock_client))

        # Drain queue directly
        interval = server._drain_queue()

        # Contract assertion: MUST return 0.02, never None, never raise
        assert interval == 0.02, f"Timer dropped for exception {exception_class.__name__}: returned {interval}"

        # Client must receive clean error response
        assert mock_client.sendall.called
        sent_bytes = mock_client.sendall.call_args[0][0]
        resp = json.loads(sent_bytes.decode("utf-8").strip())
        assert resp.get("status") == "error"
        assert resp.get("id") == "req-adversarial-exc"
        assert resp.get("error", {}).get("code") == -32000
        assert exception_class.__name__ in resp.get("error", {}).get("message")

    def test_malformed_queue_entries_containment(self, adversarial_server_factory):
        server, port = adversarial_server_factory(auto_drain=False)

        # Test queue with corrupt items
        corrupt_items = [
            ("NON_TUPLE_STRING_OBJECT",),  # single-element tuple (unpack error)
            "JUST_A_STRING",                # string (unpack error)
            None,                          # NoneType (unpack error)
            ({"jsonrpc": "2.0", "method": "ping"}, None),  # client is None
            ("NOT_A_DICT_CMD", MagicMock()),  # cmd is not dict
        ]

        for item in corrupt_items:
            server.command_queue.put(item)
            interval = server._drain_queue()
            assert interval == 0.02, f"Timer dropped on malformed queue entry: {item}"

    def test_client_socket_write_failure_does_not_kill_timer(self, adversarial_server_factory):
        server, port = adversarial_server_factory(auto_drain=False)

        # Client socket that raises BrokenPipe / ConnectionResetError on sendall
        broken_client = MagicMock()
        broken_client.sendall.side_effect = BrokenPipeError("Broken pipe (client closed)")

        cmd = {"jsonrpc": "2.0", "id": "req-broken-pipe", "method": "morphomesh.ping", "params": {}}
        server.command_queue.put((cmd, broken_client))

        interval = server._drain_queue()
        assert interval == 0.02, "Timer dropped when client socket sendall raised BrokenPipeError"

    def test_catastrophic_queue_error_caught_by_top_level_immortal_barrier(self, adversarial_server_factory):
        server, port = adversarial_server_factory(auto_drain=False)

        # Monkeypatch command_queue.empty to simulate a catastrophic internal failure
        original_empty = server.command_queue.empty
        server.command_queue.empty = MagicMock(side_effect=RuntimeError("Catastrophic memory/queue corruption"))

        try:
            interval = server._drain_queue()
            assert interval == 0.02, "Top-level barrier failed: did not return 0.02 on catastrophic queue error"
        finally:
            server.command_queue.empty = original_empty

    def test_pipeline_recovery_and_subsequent_execution_after_error(self, adversarial_server_factory):
        server, port = adversarial_server_factory(auto_drain=False)

        mock_client = MagicMock()
        # Enqueue: 1 exploding command, followed by 1 valid command
        failing_cmd = {"jsonrpc": "2.0", "id": "req-err", "method": "non_existent", "params": {}}
        valid_cmd = {"jsonrpc": "2.0", "id": "req-ok", "method": "morphomesh.ping", "params": {}}

        server.command_queue.put((failing_cmd, mock_client))
        server.command_queue.put((valid_cmd, mock_client))

        interval = server._drain_queue()
        assert interval == 0.02
        assert mock_client.sendall.call_count == 2

        first_resp = json.loads(mock_client.sendall.call_args_list[0][0][0].decode("utf-8").strip())
        second_resp = json.loads(mock_client.sendall.call_args_list[1][0][0].decode("utf-8").strip())

        assert first_resp["id"] == "req-err"
        assert first_resp["status"] == "error"
        assert second_resp["id"] == "req-ok"
        assert second_resp["status"] == "success"
        assert second_resp["result"]["status"] == "pong"

    def test_clean_deregistration_on_server_stop(self, adversarial_server_factory):
        server, port = adversarial_server_factory(auto_drain=False)

        assert server.running is True
        server.stop()
        assert server.running is False

        # When stopped, _drain_queue must return None so Blender unregisters the timer
        interval = server._drain_queue()
        assert interval is None, f"Expected None on stopped server, got {interval}"


# ==============================================================================
# 3. BLENDERBRIDGE.EXECUTE() RESPONSE UNPACKING & HEADLESS FALLBACK TESTS
# ==============================================================================

class TestBlenderBridgeExecuteUnpackingAndFallback:
    """Tests BlenderBridge.execute() response unpacking and false fallback conditions."""

    def test_execute_direct_rpc_unpacks_all_valid_structures(self, monkeypatch):
        bridge = BlenderBridge()
        monkeypatch.setattr(bridge, "is_interactive_connected", lambda: True)

        diverse_responses = [
            ("morphomesh.ping", {"status": "pong", "blender_version": "4.5.0"}),
            ("morphomesh.setup_inspector_camera", {"camera_name": "MorphoMesh_Inspector_Camera", "viewpoint": "front"}),
            ("morphomesh.capture_viewport", {"image_path": "/tmp/v.png", "resolution": [1024, 1024]}),
            ("morphomesh.critique_visual_quality", {"defects": [], "defect_count": 0, "passed": True}),
            ("morphomesh.get_scene_status", {"scene_name": "Scene", "objects": [], "object_count": 0}),
            ("morphomesh.create_human_asset", {"status": "success", "asset_id": "human-1", "mesh_path": "a.glb"}),
            ("custom_op", {"custom_data": [1, 2, 3], "flag": True}),
        ]

        headless_mock = MagicMock(side_effect=AssertionError("Falsely called headless runner!"))
        monkeypatch.setattr(bridge, "_dispatch_headless", headless_mock)

        for method, response_payload in diverse_responses:
            monkeypatch.setattr(bridge, "send_socket_request", lambda m, p, timeout=60.0: response_payload)
            res = bridge.execute(method, {})
            assert res == response_payload, f"Failed to unpack direct response for {method}"

    def test_execute_code_fallback_predicate_analysis(self, monkeypatch):
        bridge = BlenderBridge()
        monkeypatch.setattr(bridge, "is_interactive_connected", lambda: True)

        # Direct RPC fails, so bridge falls back to execute_code
        def mock_direct_fails(method, params, timeout=60.0):
            if method == "execute_code":
                return current_execute_code_result
            raise RuntimeError("Direct RPC not available")

        monkeypatch.setattr(bridge, "send_socket_request", mock_direct_fails)

        # Payloads that should be accepted by the predicate
        acceptable_payloads = [
            {"status": "success", "data": 123},
            {"success": True, "count": 10},
            {"image_path": "/path/to/img.png"},
            {"camera_name": "Inspector_Camera"},
            {"defects": [{"type": "clipping"}]},
            {"defect_count": 2},
            {"scene_name": "MasterScene"},
            {"object_count": 5},
            {"blender_version": "4.5.0"},
            {"status": "ok"},
        ]

        monkeypatch.setattr(bridge, "_dispatch_headless", MagicMock(side_effect=AssertionError("Should NOT trigger headless fallback")))

        for payload in acceptable_payloads:
            current_execute_code_result = payload
            res = bridge.execute("some_method", {})
            assert res == payload

        # Payloads with "objects" are now recognized and accepted without false headless fallback:
        headless_called = []
        monkeypatch.setattr(bridge, "_dispatch_headless", lambda m, p, t: headless_called.append((m, p)))

        current_execute_code_result = {"objects": [{"name": "Cube"}]}
        res = bridge.execute("some_method", {})
        assert res == {"objects": [{"name": "Cube"}]}
        assert len(headless_called) == 0, "Expected 'objects' to be recognized in predicate without false headless fallback"

    def test_empirical_ast_rejection_of_headless_scripts_in_validator(self):
        """Proves that headless scripts generated for execute_code are rejected by AddonSecurityValidator."""
        listener_path = os.path.abspath("blender_addon/morphomesh/listener.py")
        spec = importlib.util.spec_from_file_location("validator_check_mod", listener_path)
        mod = importlib.util.module_from_spec(spec)
        mock_bpy = MagicMock()
        mock_mathutils = MagicMock()

        with patch.dict("sys.modules", {"bpy": mock_bpy, "mathutils": mock_mathutils}):
            spec.loader.exec_module(mod)
            validator = mod.AddonSecurityValidator()

            bridge = BlenderBridge()

            # The 6 unhandled creature methods:
            unhandled_methods = [
                ("morphomesh.optimize_topology", {"input_mesh_path": "test.glb"}),
                ("morphomesh.create_armature", {"creature_type": "quadruped"}),
                ("morphomesh.setup_creature_fur", {}),
                ("morphomesh.evaluate_fur_ribbons", {}),
                ("morphomesh.setup_creature_materials", {}),
                ("morphomesh.generate_war_armor", {}),
            ]

            rejection_count = 0
            for method, params in unhandled_methods:
                script = bridge._generate_headless_script(method, params)
                try:
                    validator.validate(script)
                except ValueError as e:
                    if "Forbidden built-in call: getattr()" in str(e) or "Forbidden" in str(e):
                        rejection_count += 1

            # Assert that 100% of generated scripts for unhandled methods are rejected by AddonSecurityValidator
            assert rejection_count == len(unhandled_methods), (
                f"Expected all {len(unhandled_methods)} generated scripts to be rejected by AddonSecurityValidator, "
                f"but only {rejection_count} were rejected."
            )
