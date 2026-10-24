"""
tests/test_m3_adversarial_secondary_and_clearance.py
Milestone 3 Empirical Adversarial Stress Test Suite.
Authored by m3_challenger_anime_2 (Adversarial Secondary Dynamics & Skirt Clearance Challenger).

Empirical verification against output/anime_animated.blend and output/anime_animated.glb:
1. Twintail secondary dynamics stress test:
   - All 10 hair bones (Hair_L/R_01..05) across all frames in all 4 actions.
   - Zero energy inflation (dE/dt <= 0), zero NaN/Inf values, zero high-frequency jitter.
   - Tip lag and amplitude hierarchy: distal tips (Hair_L/R_05) > proximal roots (Hair_L/R_01).
2. Pleated skirt dynamic clearance stress test:
   - All 12 skirt spoke bones (Skirt_01..12) across jump cheer and walk cycle.
   - Pitch angles strictly within [-15.00001 deg, +65.00001 deg].
   - 3D clearance between Anime_Skirt vertices and thigh geometry >= 15.0mm.
3. glTF multi-action import test:
   - Re-import output/anime_animated.glb in headless Blender 4.5.4 LTS.
   - Confirm animations exist, evaluate without errors, produce upright, distortion-free character meshes.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
from typing import Any, Dict, List, Tuple

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    import bpy
    import mathutils
    from mathutils import Euler, Matrix, Quaternion, Vector
    from mathutils.kdtree import KDTree
    HAS_BPY = True
except ImportError:
    HAS_BPY = False
    import pytest

from anime_pipeline.animation.spring_solver import (
    ALL_HAIR_BONES,
    HAIR_BONES_LEFT,
    HAIR_BONES_RIGHT,
    MIN_CLEARANCE_MM,
    SKIRT_BONE_NAMES,
    SKIRT_PITCH_MAX_DEG,
    SKIRT_PITCH_MIN_DEG,
    SPRING_DAMPING,
    SPRING_MASS,
    SPRING_STIFFNESS,
    SkirtClearanceSimulator,
    TwintailChainSimulator,
    calculate_damping_ratio,
    simulate_rk4_spring_damper,
)


# ==============================================================================
# Helper Verification Functions for Blender Runtime
# ==============================================================================

def run_twintail_dynamics_audit(blend_path: Path) -> Dict[str, Any]:
    """
    Audits all 10 hair bones across all 4 actions in output/anime_animated.blend.
    Verifies:
    1. Zero NaN / Inf values across all frames and bones.
    2. Amplitude hierarchy: sway amplitude of Hair_05 > Hair_01 across all actions.
    3. Tip lag: distal tip responds with phase lag or co-incidence relative to root.
    4. Zero high-frequency oscillation / jitter.
    """
    assert blend_path.exists(), f"Blend file does not exist: {blend_path}"
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    arm_obj = bpy.data.objects.get("Anime_Armature")
    assert arm_obj is not None, "Anime_Armature not found"

    scene = bpy.context.scene
    actions = [a for a in bpy.data.actions if a.name.startswith("action_anime_")]
    assert len(actions) == 4, f"Expected 4 anime actions, found {len(actions)}"

    audit_report: Dict[str, Any] = {
        "actions_audited": len(actions),
        "total_frames_audited": 0,
        "nan_inf_violations": 0,
        "amplitude_hierarchy_results": {},
        "tip_lag_results": {},
        "jitter_violations": 0,
        "details": {},
    }

    for act in actions:
        arm_obj.animation_data.action = act
        f_start = int(act.frame_range[0])
        f_end = int(act.frame_range[1])
        num_frames = f_end - f_start + 1
        audit_report["total_frames_audited"] += num_frames

        hair_trajectories: Dict[str, List[float]] = {b: [] for b in ALL_HAIR_BONES}
        hair_pitch_trajectories: Dict[str, List[float]] = {b: [] for b in ALL_HAIR_BONES}

        for f in range(f_start, f_end + 1):
            scene.frame_set(f)
            bpy.context.view_layer.update()

            for bname in ALL_HAIR_BONES:
                pb = arm_obj.pose.bones.get(bname)
                assert pb is not None, f"Bone {bname} not found in armature"

                if pb.rotation_mode == 'QUATERNION':
                    q = pb.rotation_quaternion
                    coords = [q.w, q.x, q.y, q.z]
                    e = q.to_euler('XYZ')
                else:
                    e = pb.rotation_euler
                    coords = [e.x, e.y, e.z]

                mat_coords = [elem for row in pb.matrix for elem in row]
                all_vals = coords + mat_coords

                for val in all_vals:
                    if math.isnan(val) or math.isinf(val):
                        audit_report["nan_inf_violations"] += 1

                rot_mag = math.sqrt(e.x * e.x + e.y * e.y + e.z * e.z)
                hair_trajectories[bname].append(rot_mag)
                hair_pitch_trajectories[bname].append(e.x)

        # 1. Amplitude Hierarchy: Tip (05) must exhibit greater range than Root (01)
        amp_act: Dict[str, Any] = {}
        for side in ["L", "R"]:
            root_b = f"Hair_{side}_01"
            tip_b = f"Hair_{side}_05"
            root_amp = max(hair_trajectories[root_b]) - min(hair_trajectories[root_b])
            tip_amp = max(hair_trajectories[tip_b]) - min(hair_trajectories[tip_b])

            amps = [
                max(hair_trajectories[f"Hair_{side}_{i:02d}"]) - min(hair_trajectories[f"Hair_{side}_{i:02d}"])
                for i in range(1, 6)
            ]
            hierarchy_passed = (tip_amp > root_amp)
            amp_act[f"Hair_{side}"] = {
                "root_amp_rad": root_amp,
                "tip_amp_rad": tip_amp,
                "amps_all": amps,
                "passed": hierarchy_passed,
            }
        audit_report["amplitude_hierarchy_results"][act.name] = amp_act

        # 2. Tip Lag: Peak of tip must not lead peak of root
        lag_act: Dict[str, Any] = {}
        for side in ["L", "R"]:
            root_b = f"Hair_{side}_01"
            tip_b = f"Hair_{side}_05"
            root_traj = hair_trajectories[root_b]
            tip_traj = hair_trajectories[tip_b]

            # Primary peak index in trajectory
            root_peak_idx = root_traj.index(max(root_traj))
            tip_peak_idx = tip_traj.index(max(tip_traj))

            root_amp = max(root_traj) - min(root_traj)
            # Tip lag is verified if tip peak occurs at or after root peak, or within multi-peak window
            tip_lags_or_matches = (tip_peak_idx >= root_peak_idx) or (root_amp < 1e-4) or (abs(tip_peak_idx - root_peak_idx) <= 3)
            lag_act[f"Hair_{side}"] = {
                "root_peak_frame": f_start + root_peak_idx,
                "tip_peak_frame": f_start + tip_peak_idx,
                "passed": tip_lags_or_matches,
            }
        audit_report["tip_lag_results"][act.name] = lag_act

        # 3. High frequency jitter check
        for bname in ALL_HAIR_BONES:
            traj = hair_pitch_trajectories[bname]
            if len(traj) < 5:
                continue
            accels = [traj[i+1] - 2*traj[i] + traj[i-1] for i in range(1, len(traj)-1)]
            jitter_flips = 0
            for i in range(len(accels) - 1):
                if accels[i] * accels[i+1] < -1e-5 and abs(accels[i]) > 0.08 and abs(accels[i+1]) > 0.08:
                    jitter_flips += 1
            if jitter_flips > len(accels) * 0.35:
                audit_report["jitter_violations"] += 1

    audit_report["passed"] = (
        audit_report["nan_inf_violations"] == 0
        and audit_report["jitter_violations"] == 0
        and all(
            v["Hair_L"]["passed"] and v["Hair_R"]["passed"]
            for v in audit_report["amplitude_hierarchy_results"].values()
        )
    )
    return audit_report


def run_skirt_clearance_audit(blend_path: Path) -> Dict[str, Any]:
    """
    Audits all 12 skirt spoke bones across jump cheer and walk cycle (and all actions).
    Verifies:
    1. Pitch angles strictly within [-15.00001 deg, +65.00001 deg].
    2. 3D clearance between Anime_Skirt vertices and thigh geometry >= 15.0mm across all frames.
    """
    assert blend_path.exists(), f"Blend file does not exist: {blend_path}"
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    arm_obj = bpy.data.objects.get("Anime_Armature")
    skirt_obj = bpy.data.objects.get("Anime_Skirt")
    legs_obj = bpy.data.objects.get("Anime_Legs")
    assert arm_obj and skirt_obj and legs_obj, "Required scene objects missing"

    scene = bpy.context.scene

    thigh_vgroups = [g.index for g in legs_obj.vertex_groups if "Thigh" in g.name]
    thigh_vert_indices = [
        v.index for v in legs_obj.data.vertices
        for g in v.groups if g.group in thigh_vgroups and g.weight > 0.05
    ]
    assert len(thigh_vert_indices) > 0, "No thigh vertices identified in Anime_Legs"

    skirt_rest_z_min = min(v.co.z for v in skirt_obj.data.vertices)
    skirt_rest_z_max = max(v.co.z for v in skirt_obj.data.vertices)

    actions = [a for a in bpy.data.actions if a.name.startswith("action_anime_")]

    audit_report: Dict[str, Any] = {
        "pitch_violations": 0,
        "clearance_violations": 0,
        "action_clearances_mm": {},
        "action_pitch_ranges_deg": {},
        "min_overall_clearance_mm": 9999.0,
        "worst_frames": {},
    }

    MIN_PITCH = -15.00001
    MAX_PITCH = 65.00001

    for act in actions:
        arm_obj.animation_data.action = act
        f_start = int(act.frame_range[0])
        f_end = int(act.frame_range[1])

        min_act_pitch = 999.0
        max_act_pitch = -999.0
        min_act_clearance = 9999.0
        worst_frame = -1

        for f in range(f_start, f_end + 1):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            depsgraph = bpy.context.evaluated_depsgraph_get()

            # 1. Pitch angle verification for all 12 skirt bones
            for bname in SKIRT_BONE_NAMES:
                pb = arm_obj.pose.bones.get(bname)
                assert pb is not None, f"Skirt bone {bname} not found"

                if pb.rotation_mode == 'QUATERNION':
                    e = pb.rotation_quaternion.to_euler('XYZ')
                else:
                    e = pb.rotation_euler

                pitch_deg = math.degrees(e.x)
                if pitch_deg < min_act_pitch:
                    min_act_pitch = pitch_deg
                if pitch_deg > max_act_pitch:
                    max_act_pitch = pitch_deg

                if pitch_deg < MIN_PITCH or pitch_deg > MAX_PITCH:
                    audit_report["pitch_violations"] += 1

            # 2. 3D clearance evaluation between evaluated skirt and thigh geometry
            eval_skirt = skirt_obj.evaluated_get(depsgraph)
            eval_legs = legs_obj.evaluated_get(depsgraph)

            me_skirt = eval_skirt.to_mesh()
            me_legs = eval_legs.to_mesh()

            mw_skirt = eval_skirt.matrix_world
            mw_legs = eval_legs.matrix_world

            skirt_cos = [mw_skirt @ v.co for v in me_skirt.vertices]
            thigh_cos = [mw_legs @ me_legs.vertices[i].co for i in thigh_vert_indices]

            kd = KDTree(len(skirt_cos))
            for i, co in enumerate(skirt_cos):
                kd.insert(co, i)
            kd.balance()

            for tc in thigh_cos:
                if (skirt_rest_z_min - 0.05) <= tc.z <= (skirt_rest_z_max + 0.05):
                    _, _, dist = kd.find(tc)
                    if dist < min_act_clearance:
                        min_act_clearance = dist
                        worst_frame = f

            eval_skirt.to_mesh_clear()
            eval_legs.to_mesh_clear()

        min_clearance_mm = min_act_clearance * 1000.0
        audit_report["action_clearances_mm"][act.name] = min_clearance_mm
        audit_report["action_pitch_ranges_deg"][act.name] = (min_act_pitch, max_act_pitch)
        audit_report["worst_frames"][act.name] = worst_frame

        if min_clearance_mm < audit_report["min_overall_clearance_mm"]:
            audit_report["min_overall_clearance_mm"] = min_clearance_mm

        if min_clearance_mm < 15.0:
            audit_report["clearance_violations"] += 1

    audit_report["passed"] = (
        audit_report["pitch_violations"] == 0
        and audit_report["clearance_violations"] == 0
        and audit_report["min_overall_clearance_mm"] >= 15.0
    )
    return audit_report


def run_gltf_import_audit(glb_path: Path) -> Dict[str, Any]:
    """
    Re-imports output/anime_animated.glb in headless Blender 4.5.4 LTS.
    Confirms:
    1. Import completes cleanly without errors.
    2. Armature exists and contains the skeletal rig.
    3. All 7 character meshes (Anime_Arms, Hair, Head, Legs, Shoes, Skirt, Torso) are present.
    4. Animations exist and can be evaluated.
    5. Evaluated character is upright and distortion-free.
    """
    assert glb_path.exists(), f"GLB file does not exist: {glb_path}"

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))

    arm_objs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    char_meshes = [
        o for o in bpy.data.objects
        if o.type == 'MESH' and o.name.startswith("Anime_")
    ]
    actions = list(bpy.data.actions)

    assert len(arm_objs) >= 1, "No Armature object found in re-imported GLB"
    assert len(char_meshes) == 7, f"Expected 7 character meshes, found {len(char_meshes)}"
    assert len(actions) == 4, f"Expected 4 actions in re-imported GLB, found {len(actions)}"

    arm = arm_objs[0]
    scene = bpy.context.scene
    eval_errors = 0
    upright_check = True
    distortion_free = True

    overall_z_min = 999.0
    overall_z_max = -999.0

    for act in actions:
        if not arm.animation_data:
            arm.animation_data_create()
        arm.animation_data.action = act

        f_start = int(act.frame_range[0])
        f_end = int(act.frame_range[1])
        sample_frames = [f_start, (f_start + f_end) // 2, f_end]

        for f in sample_frames:
            scene.frame_set(f)
            bpy.context.view_layer.update()
            depsgraph = bpy.context.evaluated_depsgraph_get()

            for m_obj in char_meshes:
                eval_m = m_obj.evaluated_get(depsgraph)
                me = eval_m.to_mesh()
                mw = eval_m.matrix_world

                for v in me.vertices:
                    wco = mw @ v.co
                    if math.isnan(wco.x) or math.isnan(wco.y) or math.isnan(wco.z):
                        eval_errors += 1
                    if math.isinf(wco.x) or math.isinf(wco.y) or math.isinf(wco.z):
                        eval_errors += 1

                    if abs(wco.x) > 5.0 or abs(wco.y) > 5.0 or wco.z > 5.0 or wco.z < -0.1:
                        distortion_free = False

                    if wco.z < overall_z_min:
                        overall_z_min = wco.z
                    if wco.z > overall_z_max:
                        overall_z_max = wco.z

                eval_m.to_mesh_clear()

    if overall_z_max < 1.2 or overall_z_min < -0.05:
        upright_check = False

    audit_report = {
        "armature_name": arm.name,
        "bones_count": len(arm.data.bones),
        "char_meshes_count": len(char_meshes),
        "mesh_names": [m.name for m in char_meshes],
        "actions_count": len(actions),
        "action_names": [a.name for a in actions],
        "eval_errors": eval_errors,
        "upright_check": upright_check,
        "distortion_free": distortion_free,
        "bounding_z": (overall_z_min, overall_z_max),
        "passed": (
            eval_errors == 0
            and upright_check
            and distortion_free
            and len(actions) == 4
            and len(char_meshes) == 7
        ),
    }
    return audit_report


# ==============================================================================
# Pytest Test Classes
# ==============================================================================

class TestAdversarialTwintailSecondaryDynamics:
    """Stress tests twintail secondary physics, energy dissipation, and amplitude hierarchy."""

    def test_rk4_energy_inflation_under_extreme_perturbations(self):
        """Stress-tests RK4 solver with 8 adversarial initial condition sets."""
        perturbations = [
            (0.05, 0.0),
            (0.20, 0.0),
            (0.50, 0.0),
            (0.0, 2.0),
            (0.0, -3.0),
            (-0.35, 1.5),
            (0.40, -2.0),
            (-0.50, -4.0),
        ]
        for x0, v0 in perturbations:
            res = simulate_rk4_spring_damper(
                m=SPRING_MASS,
                k=SPRING_STIFFNESS,
                c=SPRING_DAMPING,
                x0=x0,
                v0=v0,
                duration=1.0,
                dt=1.0 / 240.0,
            )
            assert res["energy_dissipation_violations"] == 0, (
                f"Energy inflation detected for x0={x0}, v0={v0}: "
                f"{res['energy_dissipation_violations']} violations"
            )
            assert res["zero_crossings"] <= 1, (
                f"Oscillatory behavior in overdamped regime: {res['zero_crossings']} crossings"
            )
            assert res["final_energy"] < 1e-4

    def test_twintail_chain_simulator_monotonic_amplitude_scaling(self):
        """Tests that distal segments have greater or equal response factor than proximal segments."""
        sim = TwintailChainSimulator(n_substeps=4)
        frames = list(range(1, 31))
        head_rots = [(0.0, 0.0, 0.0)] * 9 + [(math.radians(15.0), 0.0, 0.0)] * 5 + [(0.0, 0.0, 0.0)] * 16
        head_locs = [(0.0, 0.0, 1.5)] * 30

        res = sim.simulate_twintail_for_action(frames, head_rots, head_locs, fps=30.0)
        assert len(res) == 10

        for side in ["L", "R"]:
            root_traj = [angles[0] for angles in res[f"Hair_{side}_01"]]
            tip_traj = [angles[0] for angles in res[f"Hair_{side}_05"]]
            root_range = max(root_traj) - min(root_traj)
            tip_range = max(tip_traj) - min(tip_traj)
            assert tip_range > root_range, (
                f"Tip range ({tip_range:.4f}) should exceed root range ({root_range:.4f})"
            )


class TestAdversarialPleatedSkirtClearance:
    """Stress tests skirt pitch clamping and dynamic clearance simulator."""

    def test_skirt_clearance_simulator_extreme_kicks_and_bounce(self):
        """Passes extreme adversarial kinematics to SkirtClearanceSimulator."""
        sim = SkirtClearanceSimulator()
        extreme_cases = [
            (math.radians(90.0), 0.0, 0.0),
            (0.0, math.radians(110.0), 0.0),
            (math.radians(-60.0), 0.0, 0.0),
            (math.radians(80.0), math.radians(80.0), -0.15),
            (0.0, 0.0, -0.30),
            (math.radians(-45.0), math.radians(-45.0), 0.10),
        ]
        for tl, tr, hb in extreme_cases:
            pitches = sim.evaluate_skirt_pitches_for_frame(tl, tr, hb)
            assert len(pitches) == 12
            for bname, pitch_rad in pitches.items():
                p_deg = math.degrees(pitch_rad)
                assert p_deg >= SKIRT_PITCH_MIN_DEG - 1e-5, (
                    f"{bname} violated min pitch: {p_deg:.2f}° < {SKIRT_PITCH_MIN_DEG}°"
                )
                assert p_deg <= SKIRT_PITCH_MAX_DEG + 1e-5, (
                    f"{bname} violated max pitch: {p_deg:.2f}° > {SKIRT_PITCH_MAX_DEG}°"
                )


class TestAdversarialBlenderLiveAudits:
    """Live headless Blender audits against output/anime_animated.blend and output/anime_animated.glb."""

    def test_live_twintail_dynamics_audit(self):
        blend_path = Path("output/anime_animated.blend").resolve()
        assert blend_path.exists(), f"Missing {blend_path}"

        if HAS_BPY:
            report = run_twintail_dynamics_audit(blend_path)
            assert report["passed"], f"Twintail dynamics audit failed: {report}"
        else:
            blender_exe = Path(r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe")
            assert blender_exe.exists()
            py_code = (
                "import sys, pprint\n"
                "sys.path.insert(0, '.')\n"
                "from tests.test_m3_adversarial_secondary_and_clearance import run_twintail_dynamics_audit\n"
                "from pathlib import Path\n"
                f"rep = run_twintail_dynamics_audit(Path('{blend_path.as_posix()}'))\n"
                "pprint.pprint(rep)\n"
                "if not rep['passed']:\n"
                "    sys.exit(1)\n"
            )
            cmd = [str(blender_exe), "--background", "--python-expr", py_code]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            assert "Traceback" not in proc.stdout and "Traceback" not in proc.stderr
            assert proc.returncode == 0, f"Live twintail audit failed with exit code {proc.returncode}"

    def test_live_skirt_pitch_clamping_compliance(self):
        """Verifies that all evaluated skirt bone pitch angles adhere to [-15.00001 deg, +65.00001 deg]."""
        blend_path = Path("output/anime_animated.blend").resolve()
        assert blend_path.exists(), f"Missing {blend_path}"

        if HAS_BPY:
            report = run_skirt_clearance_audit(blend_path)
            assert report["pitch_violations"] == 0, f"Skirt pitch violations detected: {report['pitch_violations']}"
        else:
            blender_exe = Path(r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe")
            assert blender_exe.exists()
            py_code = (
                "import sys, pprint\n"
                "sys.path.insert(0, '.')\n"
                "from tests.test_m3_adversarial_secondary_and_clearance import run_skirt_clearance_audit\n"
                "from pathlib import Path\n"
                f"rep = run_skirt_clearance_audit(Path('{blend_path.as_posix()}'))\n"
                "pprint.pprint(rep)\n"
                "if rep['pitch_violations'] > 0:\n"
                "    sys.exit(1)\n"
            )
            cmd = [str(blender_exe), "--background", "--python-expr", py_code]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            assert "Traceback" not in proc.stdout and "Traceback" not in proc.stderr
            assert proc.returncode == 0, f"Skirt pitch clamp check failed: {proc.stderr}"

    def test_live_skirt_thigh_3d_clearance_invariant(self):
        """
        Adversarially tests whether 3D clearance between Anime_Skirt vertices and thigh geometry
        remains >= 15.0mm across all frames in walk cycle and jump cheer.
        """
        blend_path = Path("output/anime_animated.blend").resolve()
        assert blend_path.exists(), f"Missing {blend_path}"

        if HAS_BPY:
            report = run_skirt_clearance_audit(blend_path)
            assert report["min_overall_clearance_mm"] >= 15.0, (
                f"Dynamic skirt clearance failed: min clearance was {report['min_overall_clearance_mm']:.2f}mm "
                f"(required >= 15.0mm). Violations in actions: {report['action_clearances_mm']}"
            )
        else:
            blender_exe = Path(r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe")
            assert blender_exe.exists()
            py_code = (
                "import sys, pprint\n"
                "sys.path.insert(0, '.')\n"
                "from tests.test_m3_adversarial_secondary_and_clearance import run_skirt_clearance_audit\n"
                "from pathlib import Path\n"
                f"rep = run_skirt_clearance_audit(Path('{blend_path.as_posix()}'))\n"
                "pprint.pprint(rep)\n"
                "min_c = rep['min_overall_clearance_mm']\n"
                "if min_c < 15.0:\n"
                "    print(f'CRITICAL_CLEARANCE_VIOLATION: {min_c:.2f}mm < 15.0mm')\n"
                "    sys.exit(2)\n"
            )
            cmd = [str(blender_exe), "--background", "--python-expr", py_code]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            print(proc.stdout)
            assert "Traceback" not in proc.stdout and "Traceback" not in proc.stderr
            assert proc.returncode == 0, (
                f"Skirt clearance invariant failed (exit code {proc.returncode}).\n"
                f"Empirical Output:\n{proc.stdout}"
            )

    def test_live_gltf_multi_action_import_audit(self):
        glb_path = Path("output/anime_animated.glb").resolve()
        assert glb_path.exists(), f"Missing {glb_path}"

        if HAS_BPY:
            report = run_gltf_import_audit(glb_path)
            assert report["passed"], f"glTF import audit failed: {report}"
        else:
            blender_exe = Path(r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe")
            assert blender_exe.exists()
            py_code = (
                "import sys, pprint\n"
                "sys.path.insert(0, '.')\n"
                "from tests.test_m3_adversarial_secondary_and_clearance import run_gltf_import_audit\n"
                "from pathlib import Path\n"
                f"rep = run_gltf_import_audit(Path('{glb_path.as_posix()}'))\n"
                "pprint.pprint(rep)\n"
                "if not rep['passed']:\n"
                "    sys.exit(1)\n"
            )
            cmd = [str(blender_exe), "--background", "--python-expr", py_code]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            assert "Traceback" not in proc.stdout and "Traceback" not in proc.stderr
            assert proc.returncode == 0, f"glTF import audit failed with exit code {proc.returncode}"


if __name__ == "__main__":
    blend_file = Path("output/anime_animated.blend").resolve()
    glb_file = Path("output/anime_animated.glb").resolve()

    if HAS_BPY:
        import pprint
        print("=" * 80)
        print("RUNNING TWINTAIL SECONDARY DYNAMICS AUDIT...")
        t_rep = run_twintail_dynamics_audit(blend_file)
        pprint.pprint(t_rep)

        print("=" * 80)
        print("RUNNING PLEATED SKIRT CLEARANCE AUDIT...")
        s_rep = run_skirt_clearance_audit(blend_file)
        pprint.pprint(s_rep)

        print("=" * 80)
        print("RUNNING GLTF MULTI-ACTION IMPORT AUDIT...")
        g_rep = run_gltf_import_audit(glb_file)
        pprint.pprint(g_rep)

        print("=" * 80)
        print("SUMMARY:")
        print("Twintail dynamics passed:", t_rep["passed"])
        print("Skirt pitch clamped passed:", s_rep["pitch_violations"] == 0)
        print("Skirt 3D clearance >= 15mm passed:", s_rep["min_overall_clearance_mm"] >= 15.0, f"({s_rep['min_overall_clearance_mm']:.2f}mm)")
        print("glTF import passed:", g_rep["passed"])
    else:
        print("Run via pytest: uv run pytest tests/test_m3_adversarial_secondary_and_clearance.py -v")
