"""
MorphoMesh: Milestone 5 Adversarial Socket and Multi-View Concurrency Fuzzer.

Target: tests/test_adversarial_m5_socket_camera_fuzzer.py
Milestone: Milestone 5 (Adversarial Coverage Hardening and Verification)

Empirically stress-tests:
1. Multi-Angle Camera Math Fuzzing:
   - Extreme bounding boxes:
     * Microscopic mesh (R = 10^-5 m)
     * Colossal mesh (R = 10^5 m)
     * Extremely tall mesh (Z = 100m, X = 1m, Y = 1m)
     * Flat 2D mesh (Z = 0m)
     * Random fuzzed aspect ratios and scales (100 randomized trials)
   - Verifies:
     * Camera distance d > 0 is strictly finite
     * Camera location contains no NaNs or Infs
     * Camera rotation contains no NaNs or Infs
     * Look-at vector points directly towards target center (cos_sim == 1.0)
     * Bounding sphere containment (d > R)
2. Bridge Concurrency and Rapid Switching:
   - Rapid sequential camera viewpoint switching across all 8 canonical viewpoints in sequence
   - High-throughput multi-threaded concurrent switching (8 threads x 5 rounds)
   - Zero socket deadlocks, zero dropped connections, correct framing metadata
3. Headless Blender 4.5 Runtime Verification:
   - Real bpy and mathutils execution on microscopic, colossal, tall, and flat geometry
"""

from __future__ import annotations

import concurrent.futures
import importlib.util
import json
import math
import os
import random
import socket
import subprocess
import threading
import time
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from morphomesh.blender_bridge import BlenderBridge
from morphomesh.camera_rig import (
    CANONICAL_VIEWPOINTS,
    calculate_character_bounds,
    calculate_optical_framing_distance,
    calculate_spherical_camera_position,
    get_anatomical_subregion_center,
    setup_inspector_camera,
)

CANONICAL_8_VIEWPOINTS: List[str] = [
    "front",
    "three_quarter",
    "side",
    "back",
    "top",
    "bottom",
    "close_up_head",
    "close_up_hands",
]


def blender_euler_to_rotation_matrix(rx: float, ry: float, rz: float) -> np.ndarray:
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    Rx = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]])
    Ry = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]])
    Rz = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]])
    return Rz @ Ry @ Rx


def verify_camera_lookat(
    camera_pos: Tuple[float, float, float] | List[float] | np.ndarray,
    camera_rot_euler: Tuple[float, float, float] | List[float] | np.ndarray,
    target_center: Tuple[float, float, float] | List[float] | np.ndarray,
    tol: float = 1e-3,
) -> float:
    rot_mat = blender_euler_to_rotation_matrix(*camera_rot_euler)
    cam_forward = -rot_mat[:, 2]  # -Z axis

    to_target = np.array(target_center, dtype=float) - np.array(camera_pos, dtype=float)
    dist = np.linalg.norm(to_target)
    assert dist > 1e-12, "Camera is coincident with target center!"

    unit_to_target = to_target / dist
    cos_sim = float(np.dot(cam_forward, unit_to_target))
    return cos_sim


class MockFuzzMesh:
    def __init__(self, name: str, min_pt: Tuple[float, float, float], max_pt: Tuple[float, float, float]):
        self.name = name
        self.type = 'MESH'
        mx, my, mz = min_pt
        Mx, My, Mz = max_pt
        self.bound_box = [
            (mx, my, mz), (mx, my, Mz), (mx, My, Mz), (mx, My, mz),
            (Mx, my, mz), (Mx, My, Mz), (Mx, My, Mz), (Mx, My, mz),
        ]
        self.matrix_world = np.eye(4)


# ==============================================================================
# 1. MULTI-ANGLE CAMERA MATH FUZZING
# ==============================================================================

class TestMultiAngleCameraMathFuzzing:
    @pytest.mark.parametrize("viewpoint", CANONICAL_8_VIEWPOINTS)
    def test_fuzz_microscopic_mesh(self, viewpoint: str):
        R = 1e-5
        obj = MockFuzzMesh("Microscopic", (-R, -R, -R), (R, R, R))
        center, radius, min_pt, max_pt = calculate_character_bounds(mesh_objects=[obj])
        assert radius >= 0.01

        raw_dist = calculate_optical_framing_distance(radius=R, focal_length=50.0, margin=0.15)
        assert raw_dist > 0.0 and math.isfinite(raw_dist)
        assert raw_dist > R

        cam_pos, cam_rot = calculate_spherical_camera_position(
            center=center,
            distance=raw_dist,
            azimuth_deg=CANONICAL_VIEWPOINTS[viewpoint]["azimuth"],
            elevation_deg=CANONICAL_VIEWPOINTS[viewpoint]["elevation"],
        )

        assert all(math.isfinite(c) for c in cam_pos)
        assert all(math.isfinite(r) for r in cam_rot)

        cos_sim = verify_camera_lookat(cam_pos, cam_rot, center)
        assert math.isclose(cos_sim, 1.0, abs_tol=1e-3), f"Microscopic lookat failed ({viewpoint}): {cos_sim}"

    @pytest.mark.parametrize("viewpoint", CANONICAL_8_VIEWPOINTS)
    def test_fuzz_colossal_mesh(self, viewpoint: str):
        R = 1e5
        obj = MockFuzzMesh("Colossal", (-R, -R, -R), (R, R, R))
        center, radius, min_pt, max_pt = calculate_character_bounds(mesh_objects=[obj])

        assert math.isclose(radius, math.sqrt(3) * R, rel_tol=1e-5)
        assert math.isfinite(radius)

        dist = calculate_optical_framing_distance(radius=radius, focal_length=50.0, margin=0.15)
        assert dist > radius and math.isfinite(dist)

        cam_pos, cam_rot = calculate_spherical_camera_position(
            center=center,
            distance=dist,
            azimuth_deg=CANONICAL_VIEWPOINTS[viewpoint]["azimuth"],
            elevation_deg=CANONICAL_VIEWPOINTS[viewpoint]["elevation"],
        )

        assert all(math.isfinite(c) for c in cam_pos)
        assert all(math.isfinite(r) for r in cam_rot)

        cos_sim = verify_camera_lookat(cam_pos, cam_rot, center)
        assert math.isclose(cos_sim, 1.0, abs_tol=1e-4), f"Colossal lookat failed ({viewpoint}): {cos_sim}"

    @pytest.mark.parametrize("viewpoint", CANONICAL_8_VIEWPOINTS)
    def test_fuzz_extremely_tall_mesh(self, viewpoint: str):
        obj = MockFuzzMesh("TallMesh", (-0.5, -0.5, 0.0), (0.5, 0.5, 100.0))
        center, radius, min_pt, max_pt = calculate_character_bounds(mesh_objects=[obj])

        assert math.isclose(center[2], 50.0, abs_tol=1e-4)
        assert radius >= 50.0

        spec = CANONICAL_VIEWPOINTS[viewpoint]
        sub_c, sub_r, sub_f = get_anatomical_subregion_center(
            spec["subregion"], center, radius, min_pt, max_pt
        )

        assert all(math.isfinite(c) for c in sub_c)
        assert sub_r > 0.0 and math.isfinite(sub_r)

        dist = calculate_optical_framing_distance(radius=sub_r, focal_length=sub_f, margin=spec.get("margin", 0.15))
        assert dist > 0.0 and math.isfinite(dist)

        cam_pos, cam_rot = calculate_spherical_camera_position(
            center=sub_c,
            distance=dist,
            azimuth_deg=spec["azimuth"],
            elevation_deg=spec["elevation"],
        )

        assert all(math.isfinite(c) for c in cam_pos)
        assert all(math.isfinite(r) for r in cam_rot)

        cos_sim = verify_camera_lookat(cam_pos, cam_rot, sub_c)
        assert math.isclose(cos_sim, 1.0, abs_tol=1e-4), f"Tall mesh lookat failed ({viewpoint}): {cos_sim}"

    @pytest.mark.parametrize("viewpoint", CANONICAL_8_VIEWPOINTS)
    def test_fuzz_flat_2d_mesh(self, viewpoint: str):
        obj = MockFuzzMesh("FlatMesh", (-5.0, -5.0, 0.0), (5.0, 5.0, 0.0))
        center, radius, min_pt, max_pt = calculate_character_bounds(mesh_objects=[obj])

        assert math.isclose(center[2], 0.0, abs_tol=1e-5)
        expected_r = math.sqrt(50.0)
        assert math.isclose(radius, expected_r, rel_tol=1e-4)

        for sub in ["head", "torso", "hands", "feet", "full_body"]:
            sc, sr, sf = get_anatomical_subregion_center(sub, center, radius, min_pt, max_pt)
            assert sr > 0.0 and math.isfinite(sr)
            assert all(math.isfinite(c) for c in sc)

        spec = CANONICAL_VIEWPOINTS[viewpoint]
        dist = calculate_optical_framing_distance(radius, focal_length=spec.get("default_focal", 50.0))
        cam_pos, cam_rot = calculate_spherical_camera_position(
            center=center,
            distance=dist,
            azimuth_deg=spec["azimuth"],
            elevation_deg=spec["elevation"],
        )

        assert all(math.isfinite(c) for c in cam_pos)
        assert all(math.isfinite(r) for r in cam_rot)

        cos_sim = verify_camera_lookat(cam_pos, cam_rot, center)
        assert math.isclose(cos_sim, 1.0, abs_tol=1e-4), f"Flat mesh lookat failed ({viewpoint}): {cos_sim}"

    def test_randomized_fuzzing_100_extreme_bounding_boxes(self):
        rng = random.Random(42)

        for trial in range(100):
            log_scale = rng.uniform(-5.0, 5.0)
            base_scale = 10.0 ** log_scale

            ax = rng.uniform(0.01, 10.0) * base_scale
            ay = rng.uniform(0.01, 10.0) * base_scale
            az = rng.uniform(0.01, 10.0) * base_scale

            cx = rng.uniform(-1000.0, 1000.0)
            cy = rng.uniform(-1000.0, 1000.0)
            cz = rng.uniform(-1000.0, 1000.0)

            min_pt = (cx - ax / 2.0, cy - ay / 2.0, cz - az / 2.0)
            max_pt = (cx + ax / 2.0, cy + ay / 2.0, cz + az / 2.0)

            obj = MockFuzzMesh(f"Fuzz_{trial}", min_pt, max_pt)
            c, r, _, _ = calculate_character_bounds(mesh_objects=[obj])

            vp = rng.choice(CANONICAL_8_VIEWPOINTS)
            spec = CANONICAL_VIEWPOINTS[vp]
            focal = rng.uniform(15.0, 200.0)

            dist = calculate_optical_framing_distance(radius=r, focal_length=focal)
            assert dist > 0.0 and math.isfinite(dist)

            pos, rot = calculate_spherical_camera_position(
                center=c,
                distance=dist,
                azimuth_deg=spec["azimuth"],
                elevation_deg=spec["elevation"],
            )

            assert all(math.isfinite(x) for x in pos), f"NaN/Inf pos in trial {trial}"
            assert all(math.isfinite(x) for x in rot), f"NaN/Inf rot in trial {trial}"

            cos_sim = verify_camera_lookat(pos, rot, c)
            assert math.isclose(cos_sim, 1.0, abs_tol=1e-3), f"Trial {trial} failed lookat: {cos_sim}"


# ==============================================================================
# 2. BRIDGE CONCURRENCY & RAPID SWITCHING
# ==============================================================================

class TestBridgeConcurrencyAndRapidSwitching:
    @pytest.fixture(scope="function")
    def ephemeral_bridge_server(self):
        listener_path = os.path.abspath("blender_addon/morphomesh/listener.py")
        spec = importlib.util.spec_from_file_location("morphomesh_listener_fuzz_mod", listener_path)
        mod = importlib.util.module_from_spec(spec)

        mock_bpy = MagicMock()
        mock_bpy.app.version = (4, 5, 0)
        mock_bpy.app.timers.is_registered.return_value = False
        mock_bpy.app.background = False

        scene = MagicMock()
        scene.name = "Scene_Fuzz"
        scene.objects = []
        scene.camera = None
        mock_bpy.context.scene = scene

        mock_mathutils = MagicMock()

        with patch.dict("sys.modules", {"bpy": mock_bpy, "mathutils": mock_mathutils}):
            spec.loader.exec_module(mod)
            server = mod.MorphoMeshSocketServer(host="127.0.0.1", port=0)
            server.start()
            port = server.socket.getsockname()[1]

            stop_drain = threading.Event()

            def _drain_loop():
                while not stop_drain.is_set() and server.running:
                    server._drain_queue()
                    time.sleep(0.005)

            drain_thread = threading.Thread(target=_drain_loop, daemon=True)
            drain_thread.start()

            yield server, port

            stop_drain.set()
            server.stop()

    def test_rapid_sequential_switching_all_8_viewpoints_single_socket(self, ephemeral_bridge_server):
        server, port = ephemeral_bridge_server

        with socket.create_connection(("127.0.0.1", port), timeout=5.0) as client:
            client.settimeout(5.0)

            requests = [
                {
                    "jsonrpc": "2.0",
                    "id": f"switch-{vp}",
                    "method": "morphomesh.setup_inspector_camera",
                    "params": {"viewpoint": vp, "camera_name": "MorphoMesh_Inspector_Camera"},
                }
                for vp in CANONICAL_8_VIEWPOINTS
            ]

            payload = b"".join(json.dumps(r).encode("utf-8") + b"\n" for r in requests)
            client.sendall(payload)

            responses = []
            buf = b""
            start_time = time.time()

            while len(responses) < 8 and time.time() - start_time < 5.0:
                chunk = client.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip()
                    if line:
                        responses.append(json.loads(line.decode("utf-8")))

            assert len(responses) == 8, f"Expected 8 responses, received {len(responses)}"

            for i, resp in enumerate(responses):
                vp = CANONICAL_8_VIEWPOINTS[i]
                assert resp.get("id") == f"switch-{vp}"
                assert resp.get("status") == "success"
                result = resp.get("result", {})
                assert result.get("viewpoint") == vp
                loc = result.get("camera_location") or result.get("location")
                rot = result.get("camera_rotation") or result.get("rotation_euler")
                assert len(loc) == 3 and all(math.isfinite(x) for x in loc)
                assert len(rot) == 3 and all(math.isfinite(x) for x in rot)
                assert result.get("framing_distance", 0) > 0

    def test_rapid_sequential_switching_multiple_sessions(self, ephemeral_bridge_server):
        server, port = ephemeral_bridge_server

        for vp in CANONICAL_8_VIEWPOINTS:
            with socket.create_connection(("127.0.0.1", port), timeout=3.0) as client:
                req = {
                    "jsonrpc": "2.0",
                    "id": f"sess-{vp}",
                    "method": "morphomesh.setup_inspector_camera",
                    "params": {"viewpoint": vp},
                }
                client.sendall(json.dumps(req).encode("utf-8") + b"\n")
                raw = client.recv(4096)
                resp = json.loads(raw.decode("utf-8").strip())
                assert resp.get("id") == f"sess-{vp}"
                assert resp.get("status") == "success"
                assert resp.get("result", {}).get("viewpoint") == vp

    def test_concurrent_multi_threaded_switching_stress(self, ephemeral_bridge_server):
        server, port = ephemeral_bridge_server
        num_threads = 8
        rounds_per_thread = 5

        def _worker(thread_id: int) -> List[bool]:
            results = []
            for r in range(rounds_per_thread):
                vp = CANONICAL_8_VIEWPOINTS[(thread_id + r) % len(CANONICAL_8_VIEWPOINTS)]
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=4.0) as client:
                        req = {
                            "jsonrpc": "2.0",
                            "id": f"th-{thread_id}-r-{r}",
                            "method": "morphomesh.setup_inspector_camera",
                            "params": {"viewpoint": vp},
                        }
                        client.sendall(json.dumps(req).encode("utf-8") + b"\n")
                        raw = client.recv(4096)
                        resp = json.loads(raw.decode("utf-8").strip())
                        success = (
                            resp.get("status") == "success"
                            and resp.get("result", {}).get("viewpoint") == vp
                        )
                        results.append(success)
                except Exception:
                    results.append(False)
            return results

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(_worker, i) for i in range(num_threads)]
            all_results = [f.result() for f in concurrent.futures.as_completed(futures)]

        flat = [r for sublist in all_results for r in sublist]
        assert len(flat) == num_threads * rounds_per_thread
        assert all(flat), f"Some concurrent requests failed: {flat.count(False)} failures"


# ==============================================================================
# 3. HEADLESS BLENDER 4.5 RUNTIME VERIFICATION
# ==============================================================================

class TestHeadlessBlenderRuntimeCameraMathAndSwitching:
    def test_blender_runtime_extreme_meshes_camera_setup(self):
        bridge = BlenderBridge()
        blender_bin = bridge.blender_bin_path
        if not blender_bin or not os.path.isfile(blender_bin):
            pytest.skip("Blender executable not installed in this environment")

        blender_script = """
import sys, os
sys.path.insert(0, 'src')
sys.path.insert(0, r'.venv\\Lib\\site-packages')
import bpy, math, mathutils
from morphomesh.camera_rig import setup_inspector_camera, calculate_character_bounds

m_micro = bpy.data.meshes.new('MicroMesh')
m_micro.from_pydata([(-1e-5, -1e-5, -1e-5), (1e-5, 1e-5, 1e-5)], [], [])
o_micro = bpy.data.objects.new('ObjMicro', m_micro)
bpy.context.scene.collection.objects.link(o_micro)

m_colossal = bpy.data.meshes.new('ColossalMesh')
m_colossal.from_pydata([(-1e5, -1e5, -1e5), (1e5, 1e5, 1e5)], [], [])
o_colossal = bpy.data.objects.new('ObjColossal', m_colossal)
bpy.context.scene.collection.objects.link(o_colossal)

m_tall = bpy.data.meshes.new('TallMesh')
m_tall.from_pydata([(-0.5, -0.5, 0.0), (0.5, 0.5, 100.0)], [], [])
o_tall = bpy.data.objects.new('ObjTall', m_tall)
bpy.context.scene.collection.objects.link(o_tall)

m_flat = bpy.data.meshes.new('FlatMesh')
m_flat.from_pydata([(-5.0, -5.0, 0.0), (5.0, 5.0, 0.0)], [], [])
o_flat = bpy.data.objects.new('ObjFlat', m_flat)
bpy.context.scene.collection.objects.link(o_flat)

bpy.context.view_layer.update()

test_targets = [
    ('Micro', o_micro.name),
    ('Colossal', o_colossal.name),
    ('Tall', o_tall.name),
    ('Flat', o_flat.name),
]

viewpoints = ['front', 'three_quarter', 'side', 'back', 'top', 'bottom', 'close_up_head', 'close_up_hands']

for label, obj_name in test_targets:
    for vp in viewpoints:
        res = setup_inspector_camera(viewpoint=vp, target_object=obj_name)
        assert res['status'] == 'success', f'Failed {label} {vp}'
        loc = res['camera_location']
        rot = res['camera_rotation']
        dist = res['framing_distance']
        assert dist > 0.0, f'Distance <= 0 in {label} {vp}'
        assert all(math.isfinite(x) for x in loc), f'Non-finite loc in {label} {vp}'
        assert all(math.isfinite(x) for x in rot), f'Non-finite rot in {label} {vp}'

print('BLENDER_RUNTIME_EXTREMES_SUCCESS')
"""

        cmd = [blender_bin, "--background", "--python-expr", blender_script]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        assert proc.returncode == 0, f"Blender execution failed: {proc.stderr}"
        assert "BLENDER_RUNTIME_EXTREMES_SUCCESS" in proc.stdout
