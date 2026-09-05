"""
MorphoMesh: Blender Bridge and AST Security Validator Test Suite.

Thoroughly tests:
1. Two-Tier AST Static Analysis Security Engine (BpyCodeValidator):
   - Whitelist module imports vs. forbidden imports (os, sys, subprocess, shutil, socket, etc.)
   - Forbidden built-in calls (eval, exec, open, __import__, getattr, setattr, etc.)
   - Dunder reflection escapes (__subclasses__, __globals__, __code__, __class__, etc.)
   - Forbidden identifiers and variable assignments (__builtins__, os, eval, etc.)
   - Script length limits and Python syntax errors.
2. IPC command serialization & response framing:
   - JSON-RPC socket payload serialization.
   - Headless script generation and sentinel framing (MORPHOMESH_START_JSON / MORPHOMESH_END_JSON).
   - Subprocess timeout and exit code handling.
   - Socket error response handling.
3. Blender 5.2.1 LTS engine normalization (BLENDER_EEVEE_NEXT -> BLENDER_EEVEE).
4. High-level dispatcher methods (ping, get_scene_status, optimize_topology, create_armature, render_preview).
"""

from __future__ import annotations

import ast
import json
import socket
import subprocess
from unittest.mock import MagicMock

import pytest

from morphomesh.blender_bridge import (
    SENTINEL_END,
    SENTINEL_START,
    BlenderBridge,
    BlenderExecutionError,
    BpyCodeValidator,
    SecurityException,
)
from morphomesh.models import (
    AutoRigOutput,
    BlenderExecuteOutput,
    MorphoMeshException,
    OptimizeTopologyOutput,
    SceneStatusOutput,
)

# ==============================================================================
# 1. AST STATIC ANALYSIS SECURITY VALIDATOR (BpyCodeValidator)
# ==============================================================================

class TestBpyCodeValidatorPermittedScripts:
    """Verify BpyCodeValidator permits legitimate, safe DCC automation scripts."""

    @pytest.fixture
    def validator(self) -> BpyCodeValidator:
        return BpyCodeValidator()

    def test_pure_python_math_and_logic(self, validator: BpyCodeValidator):
        script = """
x = 10
y = 20
z = [i * 2 for i in range(x)]
total = sum(z) + y
"""
        validator.validate(script)

    def test_allowed_modules_imports(self, validator: BpyCodeValidator):
        script = """
import bpy
import math
import mathutils
import bmesh
import numpy
import random
import json
import collections
import itertools
import time
"""
        validator.validate(script)

    def test_allowed_from_imports(self, validator: BpyCodeValidator):
        script = """
from math import sin, cos, pi, sqrt
from mathutils import Vector, Matrix, Euler, Quaternion
from collections import defaultdict, deque
from itertools import chain, combinations
"""
        validator.validate(script)

    def test_typical_bpy_scene_manipulation(self, validator: BpyCodeValidator):
        script = """
import bpy
import mathutils

scene = bpy.context.scene
mesh_objs = [o for o in scene.objects if o.type == 'MESH']
for obj in mesh_objs:
    obj.location.z += 1.0
    obj.scale = mathutils.Vector((1.2, 1.2, 1.2))

result_count = len(mesh_objs)
"""
        validator.validate(script)


class TestBpyCodeValidatorForbiddenImports:
    """Verify BpyCodeValidator rejects unauthorized and dangerous module imports."""

    @pytest.fixture
    def validator(self) -> BpyCodeValidator:
        return BpyCodeValidator()

    @pytest.mark.parametrize(
        "module_name",
        [
            "os",
            "sys",
            "subprocess",
            "shutil",
            "socket",
            "http",
            "urllib",
            "requests",
            "ctypes",
            "multiprocessing",
            "threading",
            "signal",
            "pty",
            "importlib",
            "builtins",
            "posix",
            "antigravity",
            "random_third_party_package",
        ],
    )
    def test_reject_forbidden_import(self, validator: BpyCodeValidator, module_name: str):
        script = f"import {module_name}"
        with pytest.raises(SecurityException) as exc_info:
            validator.validate(script)
        assert f"Forbidden module import: '{module_name}'" in str(exc_info.value)

    @pytest.mark.parametrize(
        "stmt,expected_module",
        [
            ("from os import path", "os"),
            ("from os.path import exists", "os"),
            ("from sys import exit", "sys"),
            ("from subprocess import Popen, PIPE", "subprocess"),
            ("from shutil import rmtree", "shutil"),
            ("from socket import socket", "socket"),
            ("from importlib import import_module", "importlib"),
        ],
    )
    def test_reject_forbidden_from_import(self, validator: BpyCodeValidator, stmt: str, expected_module: str):
        with pytest.raises(SecurityException) as exc_info:
            validator.validate(stmt)
        assert "Forbidden from-import:" in str(exc_info.value)
        assert expected_module in str(exc_info.value)


class TestBpyCodeValidatorForbiddenCalls:
    """Verify BpyCodeValidator rejects dangerous built-in functions."""

    @pytest.fixture
    def validator(self) -> BpyCodeValidator:
        return BpyCodeValidator()

    @pytest.mark.parametrize(
        "call_snippet,func_name",
        [
            ("eval('1 + 1')", "eval"),
            ("exec('a = 1')", "exec"),
            ("open('/etc/passwd', 'r')", "open"),
            ("__import__('os')", "__import__"),
            ("compile('1+1', '', 'eval')", "compile"),
            ("input('prompt')", "input"),
            ("breakpoint()", "breakpoint"),
            ("globals()", "globals"),
            ("locals()", "locals"),
            ("getattr(x, 'y')", "getattr"),
            ("setattr(x, 'y', 1)", "setattr"),
            ("delattr(x, 'y')", "delattr"),
        ],
    )
    def test_reject_forbidden_calls(self, validator: BpyCodeValidator, call_snippet: str, func_name: str):
        script = f"x = None\n{call_snippet}"
        with pytest.raises(SecurityException) as exc_info:
            validator.validate(script)
        assert "Forbidden" in str(exc_info.value)
        assert func_name in str(exc_info.value)


class TestBpyCodeValidatorReflectionAndDunderEscapes:
    """Verify BpyCodeValidator blocks Python reflection escapes and dunder introspection."""

    @pytest.fixture
    def validator(self) -> BpyCodeValidator:
        return BpyCodeValidator()

    def test_reject_subclasses_traversal(self, validator: BpyCodeValidator):
        exploit = "classes = ().__class__.__bases__[0].__subclasses__()"
        with pytest.raises(SecurityException) as exc_info:
            validator.validate(exploit)
        assert "Forbidden" in str(exc_info.value)

    @pytest.mark.parametrize(
        "dunder_attr",
        [
            "__subclasses__",
            "__globals__",
            "__code__",
            "__dict__",
            "__bases__",
            "__mro__",
            "__class__",
            "__annotations__",
            "__custom_attribute__",
        ],
    )
    def test_reject_dunder_attributes(self, validator: BpyCodeValidator, dunder_attr: str):
        script = f"val = obj.{dunder_attr}"
        with pytest.raises(SecurityException) as exc_info:
            validator.validate(script)
        assert "Forbidden" in str(exc_info.value)
        assert dunder_attr in str(exc_info.value)

    @pytest.mark.parametrize(
        "forbidden_name",
        [
            "__builtins__",
            "os",
            "sys",
            "subprocess",
            "shutil",
            "socket",
            "eval",
            "exec",
            "open",
            "globals",
            "locals",
        ],
    )
    def test_reject_forbidden_name_access_and_assignment(self, validator: BpyCodeValidator, forbidden_name: str):
        script1 = f"{forbidden_name} = 123"
        with pytest.raises(SecurityException) as exc1:
            validator.validate(script1)
        assert "Forbidden" in str(exc1.value)

        script2 = f"x = {forbidden_name}"
        with pytest.raises(SecurityException) as exc2:
            validator.validate(script2)
        assert "Forbidden" in str(exc2.value)


class TestBpyCodeValidatorScriptBoundaries:
    """Verify edge conditions such as empty scripts, excessive length, and syntax errors."""

    @pytest.fixture
    def validator(self) -> BpyCodeValidator:
        return BpyCodeValidator()

    def test_empty_or_whitespace_script(self, validator: BpyCodeValidator):
        with pytest.raises(SecurityException, match="Script is empty"):
            validator.validate("")
        with pytest.raises(SecurityException, match="Script is empty"):
            validator.validate("   \n\t  ")

    def test_excessive_script_length(self, validator: BpyCodeValidator):
        long_script = "x = 1\n" * 2500  # > 10000 characters
        with pytest.raises(SecurityException, match="Script exceeds maximum length"):
            validator.validate(long_script)

    def test_syntax_error_handling(self, validator: BpyCodeValidator):
        invalid_script = "def invalid_syntax(:"
        with pytest.raises(MorphoMeshException) as exc_info:
            validator.validate(invalid_script)
        assert exc_info.value.code == "ERR_SCRIPT_SYNTAX_ERROR"
        assert "Script contains Python syntax error" in exc_info.value.message


# ==============================================================================
# 2. IPC SERIALIZATION & HEADLESS RESPONSE FRAMING
# ==============================================================================

class TestBlenderBridgeIPC:
    """Verify IPC serialization, sentinel JSON framing, and socket communication."""

    def test_headless_script_generator_valid_ast(self):
        bridge = BlenderBridge()
        params = {
            "target_poly_count": 5000,
            "input_mesh_path": "/tmp/creature.glb",
            "output_format": "glb",
        }
        script_code = bridge._generate_headless_script("morphomesh.optimize_topology", params)
        # Verify script compiles without syntax errors
        tree = ast.parse(script_code)
        assert isinstance(tree, ast.Module)
        assert "morphomesh.optimize_topology" in script_code
        assert SENTINEL_START in script_code
        assert SENTINEL_END in script_code

    def test_run_headless_script_sentinel_extraction(self, monkeypatch: pytest.MonkeyPatch):
        bridge = BlenderBridge(blender_bin_path="/mock/blender")

        mock_payload = {
            "status": "pong",
            "blender_version": "5.2.1",
            "mode": "headless",
        }
        mock_stdout = (
            f"Blender 5.2.1 LTS (hash abcdef) Initializing\n"
            f"{SENTINEL_START}\n"
            f"{json.dumps(mock_payload)}\n"
            f"{SENTINEL_END}\n"
            f"Blender quit\n"
        )

        mock_proc = MagicMock()
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = ""
        mock_proc.returncode = 0

        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=mock_proc))

        result = bridge.run_headless_script("print('test')", timeout_seconds=10)
        assert result == mock_payload

    def test_run_headless_script_missing_sentinel_raises_error(self, monkeypatch: pytest.MonkeyPatch):
        bridge = BlenderBridge(blender_bin_path="/mock/blender")
        mock_proc = MagicMock(stdout="Garbage output without sentinel", stderr="Some warning", returncode=0)
        monkeypatch.setattr(subprocess, "run", MagicMock(return_value=mock_proc))

        with pytest.raises(BlenderExecutionError) as exc_info:
            bridge.run_headless_script("pass")
        assert "Sentinel JSON not found" in str(exc_info.value)

    def test_run_headless_script_timeout(self, monkeypatch: pytest.MonkeyPatch):
        bridge = BlenderBridge(blender_bin_path="/mock/blender")

        def mock_timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="blender", timeout=5)

        monkeypatch.setattr(subprocess, "run", mock_timeout)

        with pytest.raises(MorphoMeshException) as exc_info:
            bridge.run_headless_script("pass", timeout_seconds=5)
        assert exc_info.value.code == "ERR_SCRIPT_EXECUTION_TIMEOUT"

    def test_run_headless_script_missing_binary_raises_error(self, monkeypatch: pytest.MonkeyPatch):
        bridge = BlenderBridge(blender_bin_path=None)
        monkeypatch.setattr(bridge, "blender_bin_path", None)

        with pytest.raises(MorphoMeshException) as exc_info:
            bridge.run_headless_script("pass")
        assert exc_info.value.code == "ERR_BLENDER_UNAVAILABLE"

    def test_socket_send_and_receive_success(self, monkeypatch: pytest.MonkeyPatch):
        bridge = BlenderBridge(host="127.0.0.1", port=9876)

        mock_response = {
            "jsonrpc": "2.0",
            "id": "req-123",
            "result": {"status": "pong", "blender_version": "5.2.1"},
        }
        encoded_resp = json.dumps(mock_response).encode("utf-8")

        mock_sock = MagicMock()
        mock_sock.recv.side_effect = [encoded_resp, b""]
        mock_sock.__enter__.return_value = mock_sock

        monkeypatch.setattr(socket, "create_connection", MagicMock(return_value=mock_sock))

        result = bridge.send_socket_request("morphomesh.ping", {})
        assert result == {"status": "pong", "blender_version": "5.2.1"}

    def test_socket_error_response_handling(self, monkeypatch: pytest.MonkeyPatch):
        bridge = BlenderBridge(host="127.0.0.1", port=9876)

        mock_response = {
            "jsonrpc": "2.0",
            "id": "req-123",
            "error": {"code": -32000, "message": "Failed to open scene"},
        }
        encoded_resp = json.dumps(mock_response).encode("utf-8")

        mock_sock = MagicMock()
        mock_sock.recv.side_effect = [encoded_resp, b""]
        mock_sock.__enter__.return_value = mock_sock

        monkeypatch.setattr(socket, "create_connection", MagicMock(return_value=mock_sock))

        with pytest.raises(BlenderExecutionError) as exc_info:
            bridge.send_socket_request("morphomesh.bad_call", {})
        assert "Failed to open scene" in str(exc_info.value)


# ==============================================================================
# 3. ENGINE NORMALIZATION & DISPATCHER METHODS
# ==============================================================================

class TestBlenderBridgeDispatcherMethods:
    """Verify high-level bridge methods and engine normalization."""

    def test_render_preview_engine_normalization(self, monkeypatch: pytest.MonkeyPatch):
        bridge = BlenderBridge()

        captured_params = {}
        def mock_execute(method, params, timeout=60.0):
            nonlocal captured_params
            captured_params = params
            return {
                "image_path": "/tmp/preview.png",
                "image_format": "png",
                "resolution": [params.get("resolution_width", 1024), params.get("resolution_height", 1024)],
                "render_engine": params.get("render_engine", "BLENDER_EEVEE"),
                "samples": 64,
                "render_time_seconds": 0.5,
                "view_angle": "three_quarter",
                "lighting_preset": "studio_three_point",
            }

        monkeypatch.setattr(bridge, "execute", mock_execute)

        out = bridge.render_preview(render_engine="BLENDER_EEVEE_NEXT")
        assert captured_params["render_engine"] == "BLENDER_EEVEE"
        assert out.render_engine == "BLENDER_EEVEE"

    def test_execute_custom_script_client_side_ast_validation(self):
        bridge = BlenderBridge()
        dangerous_script = "import os\nos.system('echo dangerous')"

        # Must raise SecurityException on client side without calling Blender
        with pytest.raises(SecurityException) as exc_info:
            bridge.execute_custom_script(dangerous_script)
        assert "Forbidden module import: 'os'" in str(exc_info.value)

    def test_execute_custom_script_safe_execution(self, monkeypatch: pytest.MonkeyPatch):
        bridge = BlenderBridge()
        safe_script = "a = 10\nb = 20\nresult = a + b"

        mock_res = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "returned_data": {"result": 30},
            "blend_file_path": None,
        }
        monkeypatch.setattr(bridge, "execute", MagicMock(return_value=mock_res))

        out = bridge.execute_custom_script(safe_script, return_variables=["result"])
        assert isinstance(out, BlenderExecuteOutput)
        assert out.success is True
        assert out.returned_data == {"result": 30}

    def test_ping_method(self, monkeypatch: pytest.MonkeyPatch):
        bridge = BlenderBridge()
        monkeypatch.setattr(bridge, "execute", MagicMock(return_value={"status": "pong", "blender_version": "5.2.1"}))
        res = bridge.ping()
        assert res["status"] == "pong"
        assert res["blender_version"] == "5.2.1"

    def test_get_scene_status_method(self, monkeypatch: pytest.MonkeyPatch):
        bridge = BlenderBridge()
        mock_status = {
            "scene_name": "Scene",
            "blender_version": "5.2.1",
            "active_object": "Creature_Mesh",
            "object_count": 1,
            "total_vertices": 1200,
            "total_faces": 2300,
            "objects": [
                {
                    "name": "Creature_Mesh",
                    "type": "MESH",
                    "location": [0.0, 0.0, 0.0],
                    "rotation_euler": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0],
                    "parent": None,
                    "children": [],
                    "vertex_count": 1200,
                    "face_count": 2300,
                    "triangle_count": 4600,
                    "materials": ["M_Creature"],
                    "modifiers": [],
                }
            ],
            "armatures": [],
            "cameras": [],
            "lights": [],
        }
        monkeypatch.setattr(bridge, "execute", MagicMock(return_value=mock_status))

        out = bridge.get_scene_status()
        assert isinstance(out, SceneStatusOutput)
        assert out.scene_name == "Scene"
        assert out.object_count == 1
        assert out.total_vertices == 1200

    def test_optimize_topology_method(self, monkeypatch: pytest.MonkeyPatch):
        bridge = BlenderBridge()
        mock_retopo = {
            "optimized_asset_id": "opt-12345678",
            "output_mesh_path": "/tmp/opt.glb",
            "original_vertex_count": 10000,
            "original_face_count": 20000,
            "optimized_vertex_count": 4000,
            "optimized_face_count": 3900,
            "quad_percentage": 96.5,
            "reduction_ratio": 0.195,
            "uv_preserved": True,
            "processing_time_seconds": 1.1,
        }
        monkeypatch.setattr(bridge, "execute", MagicMock(return_value=mock_retopo))

        out = bridge.optimize_topology(input_mesh_path="/tmp/input.glb", target_poly_count=4000)
        assert isinstance(out, OptimizeTopologyOutput)
        assert out.optimized_asset_id == "opt-12345678"
        assert out.quad_percentage == 96.5

    def test_create_armature_method(self, monkeypatch: pytest.MonkeyPatch):
        bridge = BlenderBridge()
        mock_rig = {
            "rigged_asset_id": "rig-87654321",
            "blend_file_path": None,
            "exported_mesh_path": "/tmp/rigged.fbx",
            "armature_name": "Armature_Quadruped",
            "bone_count": 12,
            "bone_hierarchy": ["root", "spine_01", "neck", "head"],
            "creature_type": "quadruped",
            "has_skin_weights": True,
            "test_action_name": "Action_Quadruped_IdlePose",
            "status": "success",
        }
        monkeypatch.setattr(bridge, "execute", MagicMock(return_value=mock_rig))

        out = bridge.create_armature(input_mesh_path="/tmp/mesh.glb", creature_type="quadruped")
        assert isinstance(out, AutoRigOutput)
        assert out.armature_name == "Armature_Quadruped"
        assert out.bone_count == 12
