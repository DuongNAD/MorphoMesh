"""
MorphoMesh: Empirical Challenger 2 Stress Test Suite for Milestone M1 (Base Mold).
Adversarially audits mathematical integrity across:
1. Scale variations: heights 1.40m to 1.95m, proportion presets ('stylized_heroine', 'realistic_female', 'petite').
2. Quad topology & manifoldness: 13,380 vertices, 13,378 quads (100% quads), 0 non-manifold edges, 0 boundary edges.
3. Normal vectors: outward orientation, min dot product > -0.05, zero inverted faces across all 26,756 faces.
4. Minimal face area: min face area > 10^-7 m^2 across entire mesh including oral commissures and medial canthi.
5. Interface contract: generate_human_body(height, gender, proportion_preset) compliance with PROJECT.md.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple
import pytest

from morphomesh.human_generator import (
    HumanAnatomyGenerator,
    generate_human_base_mesh,
    generate_human_body,
    load_anatomical_base_mold,
)
from morphomesh.inference_adapter import MeshGeometry
from morphomesh.models import HumanAnatomyConfig


# ==============================================================================
# GEOMETRIC & TOPOLOGICAL ORACLES
# ==============================================================================

def compute_edge_topology(mesh: MeshGeometry) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """Computes non-manifold edges (>2 incident faces) and open boundary edges (1 incident face)."""
    edge_counts: Dict[Tuple[int, int], int] = {}
    for f in mesh.faces:
        for a, b in [(f[0], f[1]), (f[1], f[2]), (f[2], f[0])]:
            e = (min(a, b), max(a, b))
            edge_counts[e] = edge_counts.get(e, 0) + 1
    non_manifold = [e for e, count in edge_counts.items() if count > 2]
    boundary = [e for e, count in edge_counts.items() if count == 1]
    return non_manifold, boundary


def compute_quad_metrics_exact(mesh: MeshGeometry) -> Tuple[int, int, float]:
    """Reconstructs quads from adjacent triangle pairs to compute exact quad ratio."""
    faces = mesh.faces
    total_tris = len(faces)
    quad_count = 0
    tri_count = 0
    i = 0
    while i < total_tris:
        if i + 1 < total_tris:
            f1 = faces[i]
            f2 = faces[i + 1]
            if f1[0] == f2[0] and f1[2] == f2[1]:
                quad_count += 1
                i += 2
                continue
        tri_count += 1
        i += 1
    total_polys = quad_count + tri_count
    ratio = quad_count / total_polys if total_polys > 0 else 0.0
    return quad_count, tri_count, ratio


def compute_face_area_oracle(p0: Tuple[float, float, float], p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    """Calculates Euclidean surface area of triangular face."""
    v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
    cx = v1[1] * v2[2] - v1[2] * v2[1]
    cy = v1[2] * v2[0] - v1[0] * v2[2]
    cz = v1[0] * v2[1] - v1[1] * v2[0]
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)


def compute_normal_alignment_oracle(mesh: MeshGeometry) -> Tuple[int, float, List[Tuple[int, Tuple[int, int, int], float]]]:
    """
    Audits face normal orientation against interpolated vertex normals.
    Returns (inverted_face_count, min_dot_product, list_of_inverted_faces).
    """
    verts = mesh.vertices
    normals = mesh.normals
    min_dot = 1.0
    inverted_faces: List[Tuple[int, Tuple[int, int, int], float]] = []

    for fi, f in enumerate(mesh.faces):
        p0, p1, p2 = verts[f[0]], verts[f[1]], verts[f[2]]
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        fn = (
            v1[1] * v2[2] - v1[2] * v2[1],
            v1[2] * v2[0] - v1[0] * v2[2],
            v1[0] * v2[1] - v1[1] * v2[0],
        )
        l = math.sqrt(fn[0] ** 2 + fn[1] ** 2 + fn[2] ** 2) or 1.0
        fn_u = (fn[0] / l, fn[1] / l, fn[2] / l)

        # Average vertex normal for face
        vn_avg = [
            (normals[f[0]][k] + normals[f[1]][k] + normals[f[2]][k]) / 3.0
            for k in range(3)
        ]
        vl = math.sqrt(sum(k * k for k in vn_avg)) or 1.0
        vn_u = (vn_avg[0] / vl, vn_avg[1] / vl, vn_avg[2] / vl)

        dot = fn_u[0] * vn_u[0] + fn_u[1] * vn_u[1] + fn_u[2] * vn_u[2]
        if dot < min_dot:
            min_dot = dot
        if dot < -0.05:
            inverted_faces.append((fi, f, dot))

    return len(inverted_faces), min_dot, inverted_faces


# ==============================================================================
# TEST SUITE
# ==============================================================================

class TestM1Challenger2Stress:
    """Adversarial stress harness by Challenger 2 for M1 Base Mold."""

    # --------------------------------------------------------------------------
    # 1. SCALE VARIATIONS & TOPOLOGY INTEGRITY (1.40m to 1.95m)
    # --------------------------------------------------------------------------
    @pytest.mark.parametrize("height", [1.40, 1.50, 1.65, 1.80, 1.95])
    def test_quad_topology_and_manifoldness_across_scale(self, height: float):
        """
        Verify: 13,380 vertices, 13,378 quads (100% quads, 0 isolated triangles),
        0 non-manifold edges, 0 boundary edges across heights 1.40m to 1.95m.
        """
        cfg = HumanAnatomyConfig(height=height)
        res = generate_human_base_mesh(cfg)
        mesh = res.mesh

        assert len(mesh.vertices) == 13380, f"Expected 13,380 vertices at h={height}m, got {len(mesh.vertices)}"
        assert len(mesh.faces) == 26756, f"Expected 26,756 triangles at h={height}m, got {len(mesh.faces)}"

        quad_count, tri_count, ratio = compute_quad_metrics_exact(mesh)
        assert quad_count == 13378, f"Expected 13,378 quads at h={height}m, got {quad_count}"
        assert tri_count == 0, f"Expected 0 isolated triangles at h={height}m, got {tri_count}"
        assert ratio == 1.0, f"Expected 100% quad ratio at h={height}m, got {ratio}"

        non_manifold, boundary = compute_edge_topology(mesh)
        assert len(non_manifold) == 0, f"Found {len(non_manifold)} non-manifold edges at h={height}m"
        assert len(boundary) == 0, f"Found {len(boundary)} open boundary edges at h={height}m"

    # --------------------------------------------------------------------------
    # 2. NORMAL VECTOR OUTWARD ORIENTATION & INVERSION AUDIT
    # --------------------------------------------------------------------------
    def test_torso_transverse_outward_normals(self):
        """
        Verify outward orientation (cx*nx + cy*ny > 0) on cylindrical trunk/torso faces.
        """
        res = generate_human_base_mesh(HumanAnatomyConfig(height=1.65))
        mesh = res.mesh
        verts = mesh.vertices

        torso_total = 0
        torso_outward = 0
        for f in mesh.faces:
            p0, p1, p2 = verts[f[0]], verts[f[1]], verts[f[2]]
            cx = (p0[0] + p1[0] + p2[0]) / 3.0
            cy = (p0[1] + p1[1] + p2[1]) / 3.0
            cz = (p0[2] + p1[2] + p2[2]) / 3.0

            # Inspect cylindrical trunk sections excluding cleavage/groin creases
            if 0.90 <= cz <= 1.35 and abs(cx) < 0.16 and cy > -0.05:
                v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
                v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
                fn = (v1[1] * v2[2] - v1[2] * v2[1], v1[2] * v2[0] - v1[0] * v2[2], v1[0] * v2[1] - v1[1] * v2[0])
                l = math.sqrt(fn[0] ** 2 + fn[1] ** 2 + fn[2] ** 2) or 1.0
                dot = cx * (fn[0] / l) + cy * (fn[1] / l)
                torso_total += 1
                if dot > 0:
                    torso_outward += 1

        assert torso_total > 500
        outward_pct = (torso_outward / torso_total) * 100.0
        assert outward_pct >= 99.5, f"Torso outward normal percentage {outward_pct:.2f}% < 99.5%"

    @pytest.mark.parametrize("preset_name,cfg", [
        ("stylized_heroine_1.65m", HumanAnatomyConfig(height=1.65, head_ratio=7.41, chest_girth=0.82, waist_girth=0.58, hip_girth=0.86, shoulder_width=0.36)),
        ("stylized_heroine_1.40m", HumanAnatomyConfig(height=1.40, head_ratio=7.41, chest_girth=0.82, waist_girth=0.58, hip_girth=0.86, shoulder_width=0.36)),
        ("stylized_heroine_1.95m", HumanAnatomyConfig(height=1.95, head_ratio=7.41, chest_girth=0.82, waist_girth=0.58, hip_girth=0.86, shoulder_width=0.36)),
        ("petite_1.40m", HumanAnatomyConfig(height=1.40, head_ratio=6.50, chest_girth=0.76, waist_girth=0.54, hip_girth=0.80, shoulder_width=0.32)),
        ("realistic_female_1.68m", HumanAnatomyConfig(height=1.68, head_ratio=7.50, chest_girth=0.88, waist_girth=0.66, hip_girth=0.94, shoulder_width=0.38)),
    ])
    def test_normals_min_dot_and_zero_inversions(self, preset_name: str, cfg: HumanAnatomyConfig):
        """
        Verify: min dot product > -0.05, exactly 0 inverted faces across all 26,756 triangulated faces.
        ADVERSARIAL CHALLENGE: Exposes inverted face 20360 (10449, 10450, 10512) on realistic_female_1.68m.
        """
        res = generate_human_base_mesh(cfg)
        inverted_count, min_dot, inverted_faces = compute_normal_alignment_oracle(res.mesh)

        assert inverted_count == 0, (
            f"Preset '{preset_name}' has {inverted_count} inverted faces! "
            f"Inverted sample: {inverted_faces[:3]}"
        )
        assert min_dot > -0.05, f"Preset '{preset_name}' has min normal alignment dot {min_dot:.4f} <= -0.05"

    # --------------------------------------------------------------------------
    # 3. MINIMAL FACE AREA STRESS TEST (> 10^-7 m^2)
    # --------------------------------------------------------------------------
    @pytest.mark.parametrize("preset_name,cfg", [
        ("stylized_heroine_1.65m", HumanAnatomyConfig(height=1.65, head_ratio=7.41, chest_girth=0.82, waist_girth=0.58, hip_girth=0.86, shoulder_width=0.36)),
        ("stylized_heroine_1.40m", HumanAnatomyConfig(height=1.40, head_ratio=7.41, chest_girth=0.82, waist_girth=0.58, hip_girth=0.86, shoulder_width=0.36)),
        ("stylized_heroine_1.95m", HumanAnatomyConfig(height=1.95, head_ratio=7.41, chest_girth=0.82, waist_girth=0.58, hip_girth=0.86, shoulder_width=0.36)),
        ("petite_1.40m", HumanAnatomyConfig(height=1.40, head_ratio=6.50, chest_girth=0.76, waist_girth=0.54, hip_girth=0.80, shoulder_width=0.32)),
        ("realistic_female_1.40m", HumanAnatomyConfig(height=1.40, head_ratio=7.50, chest_girth=0.88, waist_girth=0.66, hip_girth=0.94, shoulder_width=0.38)),
    ])
    def test_minimal_face_area_across_entire_mesh(self, preset_name: str, cfg: HumanAnatomyConfig):
        """
        Verify: min face area > 10^-7 m^2 across entire mesh including oral commissures and medial canthi.
        ADVERSARIAL CHALLENGE: Exposes face 6702 area collapse to 9.84e-8 m^2 on realistic_female_1.40m.
        """
        res = generate_human_base_mesh(cfg)
        mesh = res.mesh
        verts = mesh.vertices

        min_area = float("inf")
        min_face_info = None

        for fi, f in enumerate(mesh.faces):
            area = compute_face_area_oracle(verts[f[0]], verts[f[1]], verts[f[2]])
            if area < min_area:
                min_area = area
                min_face_info = (fi, f)

        assert min_area > 1.0e-7, (
            f"Preset '{preset_name}' violated minimum face area threshold! "
            f"min_area={min_area:.4e} m^2 <= 1.0e-7 m^2 at face {min_face_info}"
        )

    def test_oral_commissures_and_medial_canthi_face_areas(self):
        """
        Targeted audit of oral commissure and medial canthi vertex zones (422, 423, 425, 426, 428, 429, etc.).
        """
        target_verts = {30, 422, 423, 425, 426, 428, 429, 431, 432, 500, 501, 3735}
        for h in [1.40, 1.65, 1.95]:
            cfg = HumanAnatomyConfig(height=h)
            res = generate_human_base_mesh(cfg)
            mesh = res.mesh
            verts = mesh.vertices

            commissure_min_area = float("inf")
            for f in mesh.faces:
                if any(v in target_verts for v in f):
                    area = compute_face_area_oracle(verts[f[0]], verts[f[1]], verts[f[2]])
                    if area < commissure_min_area:
                        commissure_min_area = area

            assert commissure_min_area > 1.0e-7, (
                f"Oral commissure / medial canthus face area {commissure_min_area:.4e} <= 1.0e-7 at height {h}m"
            )

    # --------------------------------------------------------------------------
    # 4. INTERFACE CONTRACT & PRESET ACCEPTANCE AUDIT
    # --------------------------------------------------------------------------
    def test_interface_contract_generate_human_body_signature(self):
        """
        Verify interface contract specified in PROJECT.md line 69:
        HumanAnatomyGenerator.generate_human_body(height=1.65, gender='female', proportion_preset='stylized_heroine')
        ADVERSARIAL CHALLENGE: Exposes TypeError if generate_human_body rejects kwargs (gender, proportion_preset).
        """
        try:
            mesh, landmarks = generate_human_body(
                height=1.65,
                gender="female",
                proportion_preset="stylized_heroine",
            )
            assert isinstance(mesh, MeshGeometry)
            assert isinstance(landmarks, dict)
            assert len(mesh.vertices) == 13380
        except TypeError as e:
            pytest.fail(f"Interface contract violation: generate_human_body rejected specification kwargs: {e}")
