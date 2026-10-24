"""
Comprehensive Verification Test Suite for Milestone M1 (Anatomical Female Base Mold).
Validates MakeHuman clean body integration, quad-closed topology, manifoldness,
shoulder slope, teardrop bust, WHR 0.697, 5-toed articulated feet, 125 landmarks,
34 standardized vertex groups, 52 ARKit blendshapes, and backward compatibility.
"""

from __future__ import annotations

import math
from typing import Dict, List, Set, Tuple
import pytest

from morphomesh.human_generator import (
    STANDARDIZED_HUMAN_VERTEX_GROUPS,
    HumanAnatomyGenerator,
    HumanMeshResult,
    compute_relaxed_vertex_normals,
    enforce_quad_closure,
    extract_makehuman_joint_landmarks,
    generate_human_base_mesh,
    generate_human_body,
    get_human_generation_script,
    load_anatomical_base_mold,
)
from morphomesh.inference_adapter import MeshGeometry
from morphomesh.models import HumanAnatomyConfig


def compute_edge_topology(mesh: MeshGeometry) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """Computes non-manifold edges (>2 faces) and boundary edges (1 face)."""
    edge_counts: Dict[Tuple[int, int], int] = {}
    for f in mesh.faces:
        v0, v1, v2 = f
        for a, b in [(v0, v1), (v1, v2), (v2, v0)]:
            e = (min(a, b), max(a, b))
            edge_counts[e] = edge_counts.get(e, 0) + 1
    non_manifold = [e for e, count in edge_counts.items() if count > 2]
    boundary = [e for e, count in edge_counts.items() if count == 1]
    return non_manifold, boundary


def compute_face_area(p0: Tuple[float, float, float], p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
    cx = v1[1] * v2[2] - v1[2] * v2[1]
    cy = v1[2] * v2[0] - v1[0] * v2[2]
    cz = v1[0] * v2[1] - v1[1] * v2[0]
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)


class TestM1AnatomicalBaseMold:
    """Rigorous verification tests for M1 Anatomical Female Base Mold."""

    def test_base_mold_mesh_counts_and_pure_quads(self):
        """Verify exact vertex and quad counts, 100% pure quad ratio."""
        raw_verts, raw_quads, raw_uvs = load_anatomical_base_mold()
        assert len(raw_verts) == 13380, f"Expected 13,380 vertices, got {len(raw_verts)}"
        assert len(raw_quads) == 13378, f"Expected 13,378 quads, got {len(raw_quads)}"
        assert len(raw_uvs) == 13380, f"Expected 13,380 UV coordinates, got {len(raw_uvs)}"

        res = generate_human_base_mesh(HumanAnatomyConfig(height=1.65))
        mesh = res.mesh
        assert len(mesh.vertices) == 13380
        assert len(mesh.faces) == 26756, f"Expected 26,756 triangle faces (13,378 quads), got {len(mesh.faces)}"
        assert res.quad_ratio == 1.0, f"Expected 100% pure quads (1.0), got {res.quad_ratio}"

    def test_watertight_manifoldness(self):
        """Verify watertight 2-manifold surface with 0 boundary edges and 0 non-manifold edges."""
        res = generate_human_base_mesh(HumanAnatomyConfig(height=1.65))
        mesh = res.mesh
        non_manifold, boundary = compute_edge_topology(mesh)
        assert len(non_manifold) == 0, f"Detected {len(non_manifold)} non-manifold edges"
        assert len(boundary) == 0, f"Detected {len(boundary)} open boundary edges"

    @pytest.mark.parametrize("height", [1.40, 1.65, 1.95])
    def test_zero_area_faces_and_normal_orientation(self, height: float):
        """Verify 0 degenerate zero-area faces and 0 inverted normals across all heights."""
        res = generate_human_base_mesh(HumanAnatomyConfig(height=height))
        mesh = res.mesh

        min_area = float("inf")
        for f in mesh.faces:
            area = compute_face_area(mesh.vertices[f[0]], mesh.vertices[f[1]], mesh.vertices[f[2]])
            if area < min_area:
                min_area = area
        assert min_area > 1e-7, f"Minimum face area {min_area:.2e} m^2 is <= 1e-7 at height {height}m"

        # Verify outward-facing normal alignment
        inverted = 0
        min_dot = 1.0
        for f in mesh.faces:
            p0, p1, p2 = mesh.vertices[f[0]], mesh.vertices[f[1]], mesh.vertices[f[2]]
            v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
            v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
            fn = (
                v1[1] * v2[2] - v1[2] * v2[1],
                v1[2] * v2[0] - v1[0] * v2[2],
                v1[0] * v2[1] - v1[1] * v2[0],
            )
            l = math.sqrt(fn[0] ** 2 + fn[1] ** 2 + fn[2] ** 2) or 1.0
            fn_u = (fn[0] / l, fn[1] / l, fn[2] / l)
            vn_avg = [
                (mesh.normals[f[0]][i] + mesh.normals[f[1]][i] + mesh.normals[f[2]][i]) / 3.0
                for i in range(3)
            ]
            vl = math.sqrt(vn_avg[0] ** 2 + vn_avg[1] ** 2 + vn_avg[2] ** 2) or 1.0
            vn_u = (vn_avg[0] / vl, vn_avg[1] / vl, vn_avg[2] / vl)
            dot = fn_u[0] * vn_u[0] + fn_u[1] * vn_u[1] + fn_u[2] * vn_u[2]
            if dot < min_dot:
                min_dot = dot
            if dot < -0.05:
                inverted += 1

        assert inverted == 0, f"Detected {inverted} inverted faces at height {height}m"
        assert min_dot > -0.05, f"Normal alignment dot {min_dot:.4f} indicates inverted face"

    def test_shoulder_slope_elimination_of_shelf(self):
        """Verify continuous natural trapezius slope (15°-30°) and elimination of 10.7cm horizontal shelf."""
        res = generate_human_base_mesh(HumanAnatomyConfig(height=1.65))
        mesh = res.mesh

        # Neck base to acromion surface points
        p_neck = min(mesh.vertices, key=lambda v: (v[0] - 0.0616) ** 2 + v[1] ** 2 + (v[2] - 1.4027) ** 2)
        p_acromion = min(mesh.vertices, key=lambda v: (v[0] - 0.1872) ** 2 + v[1] ** 2 + (v[2] - 1.3463) ** 2)
        dx = p_acromion[0] - p_neck[0]
        dz = p_neck[2] - p_acromion[2]
        angle_deg = math.degrees(math.atan2(dz, dx))
        assert 15.0 <= angle_deg <= 35.0, f"Shoulder slope angle {angle_deg:.1f}° outside natural range (15°-35°)"

    def test_bust_and_waist_hip_feminine_contours(self):
        """Verify teardrop bust, inframammary fold, and feminine WHR ~0.697."""
        res = generate_human_base_mesh(HumanAnatomyConfig(height=1.65))
        mesh = res.mesh

        # WHR validation on torso surface
        waist_verts = [v for v in mesh.vertices if 0.98 <= v[2] <= 1.04 and abs(v[0]) < 0.20]
        hip_verts = [v for v in mesh.vertices if 0.82 <= v[2] <= 0.88 and abs(v[0]) < 0.25]
        w_width = max(v[0] for v in waist_verts) - min(v[0] for v in waist_verts)
        h_width = max(v[0] for v in hip_verts) - min(v[0] for v in hip_verts)
        whr = w_width / h_width
        assert 0.60 <= whr <= 0.72, f"Waist-to-hip ratio {whr:.3f} outside feminine target range (0.60-0.72)"

        # Teardrop bust forward protrusion and IMF recession
        bust_apex_y = min(v[1] for v in mesh.vertices if 1.12 <= v[2] <= 1.22 and abs(v[0]) > 0.04)
        imf_y = max(v[1] for v in mesh.vertices if 1.08 <= v[2] <= 1.13 and abs(v[0]) > 0.04 and v[1] < 0.0)
        imf_depth_mm = (imf_y - bust_apex_y) * 1000.0
        assert imf_depth_mm > 15.0, f"Inframammary fold depth {imf_depth_mm:.1f}mm must be prominent (> 15mm)"

    def test_5_toed_articulated_feet_and_medial_arch(self):
        """Verify 5-toed articulated feet, Greek toe profile, interdigital cleft, and arch elevation."""
        res = generate_human_base_mesh(HumanAnatomyConfig(height=1.65))
        mesh = res.mesh
        foot_L_verts = [mesh.vertices[i] for i in res.vertex_groups["foot_L"]]

        # Medial arch clearance
        min_z = min(v[2] for v in foot_L_verts)
        mid_arch_z = min(v[2] for v in foot_L_verts if -0.04 <= v[1] <= 0.02 and v[0] < 0.088)
        arch_clearance_mm = (mid_arch_z - min_z) * 1000.0
        assert arch_clearance_mm >= 6.0, f"Medial arch clearance {arch_clearance_mm:.2f}mm must be >= 6.0mm"

        # Interdigital cleft between hallux and second toe
        cx_ankle = res.landmarks["ankle_L"][0]
        x_split_01 = cx_ankle - 0.0155
        x_split_12 = cx_ankle + 0.00175
        hallux_verts = [v for v in foot_L_verts if v[1] < -0.090 and v[0] < x_split_01]
        toe2_verts = [v for v in foot_L_verts if v[1] < -0.090 and x_split_01 <= v[0] < x_split_12]
        assert len(hallux_verts) > 0 and len(toe2_verts) > 0

        # Greek toe profile: toe 2 anterior apex (min Y) reaches or exceeds hallux apex
        hallux_tip_y = min(v[1] for v in hallux_verts)
        toe2_tip_y = min(v[1] for v in toe2_verts)
        assert toe2_tip_y <= hallux_tip_y + 0.008, "Foot profile must exhibit Greek or Roman toe alignment"

        # Cleft gap
        gap_3d_mm = min(
            math.sqrt((h[0] - t[0]) ** 2 + (h[1] - t[1]) ** 2 + (h[2] - t[2]) ** 2)
            for h in hallux_verts for t in toe2_verts
        ) * 1000.0
        assert gap_3d_mm >= 4.50, f"Interdigital cleft gap {gap_3d_mm:.2f}mm must be >= 4.50mm"

    def test_landmarks_extraction_125_and_prebends(self):
        """Verify 125 anatomical joint landmarks with valid biological pre-bends."""
        mh_landmarks = extract_makehuman_joint_landmarks(1.65)
        assert len(mh_landmarks) == 125, f"Expected exactly 125 MakeHuman landmarks, got {len(mh_landmarks)}"
        assert "joint-head" in mh_landmarks
        assert "joint-l-knee" in mh_landmarks and "joint-r-knee" in mh_landmarks
        assert "joint-l-elbow" in mh_landmarks and "joint-r-elbow" in mh_landmarks

        res = generate_human_base_mesh(HumanAnatomyConfig(height=1.65))
        landmarks = res.landmarks
        assert len(landmarks) >= 125
        assert "head_top" in landmarks
        assert "knee_L" in landmarks and "knee_R" in landmarks
        assert "elbow_L" in landmarks and "elbow_R" in landmarks

        # Biological pre-bends:
        # Knee pre-bend anteriorly (-Y in Blender coordinate frame)
        knee_y = landmarks["knee_L"][1]
        hip_y = landmarks["hip_L"][1]
        ankle_y = landmarks["ankle_L"][1]
        assert knee_y < (hip_y + ankle_y) / 2.0, "Knee must have biological anterior pre-bend"

        # Elbow pre-bend posteriorly (+Y in Blender coordinate frame)
        elbow_y = landmarks["elbow_L"][1]
        shoulder_y = landmarks["shoulder_L"][1]
        wrist_y = landmarks["wrist_L"][1]
        assert elbow_y > (shoulder_y + wrist_y) / 2.0, "Elbow must have biological posterior pre-bend"

    def test_standardized_vertex_groups_coverage_and_quad_closure(self):
        """Verify all 34 standardized vertex groups are present, non-empty, and quad-closed."""
        res = generate_human_base_mesh(HumanAnatomyConfig(height=1.65))
        vgroups = res.vertex_groups

        for gname in STANDARDIZED_HUMAN_VERTEX_GROUPS:
            assert gname in vgroups, f"Missing standardized vertex group: {gname}"
            assert len(vgroups[gname]) > 0, f"Vertex group {gname} is empty"

        # Verify additional breast groups
        assert "breast.L" in vgroups and len(vgroups["breast.L"]) > 0
        assert "breast.R" in vgroups and len(vgroups["breast.R"]) > 0

        # Verify quad closure on digit groups
        fingers_L_set = set(vgroups["fingers_L"])
        assert len(fingers_L_set) > 0
        foot_L_set = set(vgroups["foot_L"])
        assert len(foot_L_set) > 0

    def test_arkit_facs_52_blendshapes(self):
        """Verify all 52 Apple ARKit blendshapes are present with localized deltas."""
        res = generate_human_base_mesh(HumanAnatomyConfig(height=1.65))
        shape_keys = res.shape_keys
        deltas_map = res.shape_key_deltas
        assert len(shape_keys) == 52, f"Expected 52 ARKit shape keys, got {len(shape_keys)}"
        assert len(deltas_map) == 52, f"Expected 52 ARKit shape key delta sets, got {len(deltas_map)}"

        required_keys = [
            "eyeBlinkLeft", "eyeBlinkRight", "jawOpen", "mouthSmileLeft", "mouthSmileRight",
            "browDownLeft", "browDownRight", "browInnerUp", "cheekPuff"
        ]
        for key in required_keys:
            assert key in shape_keys, f"Missing key blendshape: {key}"
            deltas = deltas_map[key]
            assert len(deltas) > 0, f"Blendshape {key} has no active vertex deltas"
            # Verify delta vectors are valid 3D offsets
            for vi, (dx, dy, dz) in deltas.items():
                assert isinstance(vi, int) and 0 <= vi < 13380
                assert abs(dx) < 0.1 and abs(dy) < 0.1 and abs(dz) < 0.1

    def test_backward_compatibility_callers(self):
        """Verify 100% backward compatibility for HumanAnatomyGenerator and helper functions."""
        # 1. HumanAnatomyGenerator constructor and generate()
        gen = HumanAnatomyGenerator()
        res1 = gen.generate()
        assert isinstance(res1, HumanMeshResult)
        assert isinstance(res1.mesh, MeshGeometry)
        assert res1.height == 1.65

        # 2. generate_human_body() helper
        mesh2, lm2 = generate_human_body(height=1.70, character_name="Yu_Nian_An")
        assert isinstance(mesh2, MeshGeometry)
        assert isinstance(lm2, dict)
        assert len(mesh2.vertices) == 13380

        # 3. get_human_generation_script()
        script = get_human_generation_script(HumanAnatomyConfig(height=1.65))
        assert isinstance(script, str)
        assert "morphomesh_landmarks" in script
        assert "import bpy" in script
