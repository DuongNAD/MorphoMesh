"""
MorphoMesh: Rig Skinning Deformation & Volume Preservation Engine.

Evaluates mesh signed volume conservation, joint collapse (candy-wrapper twisting),
extreme acute dihedral creases, and skinning pinch defects under pose deformation.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import numpy as np

from morphomesh.models import (
    ActionableRecommendation,
    DefectCategory,
    DefectItem,
    DefectSeverity,
)
from .bvh import HAS_BLENDER, bpy
from .geometry_math import (
    _cross_product,
    _dot_product,
    _norm_vec,
    _sub_vec,
    _vec_len,
)

@dataclass
class JointDeformationMetrics:
    joint_name: str
    rest_volume: float
    posed_volume: float
    volume_ratio: float
    min_dihedral_cos: float
    min_fold_angle_deg: float
    pinched_edge_count: int
    is_volume_conserved: bool = True
    is_crease_free: bool = True


def compute_mesh_signed_volume(
    vertices: List[Tuple[float, float, float]],
    faces: List[Tuple[int, ...]],
) -> float:
    """
    Computes exact volume of watertight polygonal/triangle mesh via divergence theorem.
    Automatically decomposes quads (len(f) == 4) and planar n-gons into triangles via fan triangulation.
    """
    vol = 0.0
    for f in faces:
        n = len(f)
        if n < 3:
            continue
        for i in range(1, n - 1):
            v1 = vertices[f[0]]
            v2 = vertices[f[i]]
            v3 = vertices[f[i + 1]]
            cx = v2[1] * v3[2] - v2[2] * v3[1]
            cy = v2[2] * v3[0] - v2[0] * v3[2]
            cz = v2[0] * v3[1] - v2[1] * v3[0]
            vol += v1[0] * cx + v1[1] * cy + v1[2] * cz
    return abs(vol) / 6.0


def compute_bounding_slice_volume(
    vertices: List[Tuple[float, float, float]],
    faces: List[Tuple[int, ...]],
    axis_point: Tuple[float, float, float],
    axis_direction: Tuple[float, float, float],
    span_min: float = -0.05,
    span_max: float = 0.05,
    num_slices: int = 15,
) -> float:
    """Computes volume of local joint segment via planar cross-section integration (Shoelace)."""
    u_len = math.sqrt(sum(x * x for x in axis_direction)) or 1.0
    u_dir = (axis_direction[0] / u_len, axis_direction[1] / u_len, axis_direction[2] / u_len)

    # 2D basis (e1, e2) in slicing plane
    if abs(u_dir[0]) < 0.9:
        e1_raw = (0.0, -u_dir[2], u_dir[1])
    else:
        e1_raw = (-u_dir[1], u_dir[0], 0.0)
    e1_len = math.sqrt(sum(x * x for x in e1_raw)) or 1.0
    e1 = (e1_raw[0] / e1_len, e1_raw[1] / e1_len, e1_raw[2] / e1_len)
    e2 = _cross_product(u_dir, e1)

    dz = (span_max - span_min) / max(1, num_slices - 1)
    areas: List[float] = []

    for s_idx in range(num_slices):
        s_val = span_min + s_idx * dz
        p_plane = (
            axis_point[0] + s_val * u_dir[0],
            axis_point[1] + s_val * u_dir[1],
            axis_point[2] + s_val * u_dir[2],
        )

        pts_2d: List[Tuple[float, float]] = []
        for f in faces:
            # triangulate if quad
            triangles = [[f[0], f[1], f[2]]]
            if len(f) >= 4:
                triangles.append([f[0], f[2], f[3]])

            for tri_idxs in triangles:
                tri = [vertices[tri_idxs[0]], vertices[tri_idxs[1]], vertices[tri_idxs[2]]]
                dists = [sum((tri[i][c] - p_plane[c]) * u_dir[c] for c in range(3)) for i in range(3)]

                for i in range(3):
                    j = (i + 1) % 3
                    if (dists[i] < 0.0 and dists[j] > 0.0) or (dists[i] > 0.0 and dists[j] < 0.0):
                        t = dists[i] / (dists[i] - dists[j])
                        q_3d = tuple(tri[i][c] + t * (tri[j][c] - tri[i][c]) for c in range(3))
                        rel_q = _sub_vec(q_3d, p_plane)
                        pts_2d.append((
                            _dot_product(rel_q, e1),
                            _dot_product(rel_q, e2),
                        ))

        # Filter duplicates
        u_pts: List[Tuple[float, float]] = []
        for p in pts_2d:
            if not any(math.hypot(p[0] - up[0], p[1] - up[1]) < 1e-4 for up in u_pts):
                u_pts.append(p)

        if len(u_pts) >= 3:
            cx = sum(p[0] for p in u_pts) / len(u_pts)
            cy = sum(p[1] for p in u_pts) / len(u_pts)
            s_pts = sorted(u_pts, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
            n = len(s_pts)
            area = abs(sum(s_pts[i][0] * s_pts[(i + 1) % n][1] - s_pts[(i + 1) % n][0] * s_pts[i][1] for i in range(n))) * 0.5
            areas.append(area)
        else:
            areas.append(0.0)

    vol = dz * (0.5 * areas[0] + sum(areas[1:-1]) + 0.5 * areas[-1])
    return vol


def compute_mesh_dihedral_creases(
    vertices: List[Tuple[float, float, float]],
    faces: List[Tuple[int, ...]],
    cos_threshold: float = -0.85,
) -> List[Dict[str, Any]]:
    """
    Detects acute dihedral creases where adjacent manifold faces fold sharply (cos theta < -0.85).
    cos theta < -0.85 corresponds to fold angle < 31.8 degrees.
    """
    # 1. Face unit normals
    face_normals: List[Tuple[float, float, float]] = []
    for f in faces:
        v1 = vertices[f[0]]
        v2 = vertices[f[1]]
        v3 = vertices[f[2]]
        e1 = _sub_vec(v2, v1)
        e2 = _sub_vec(v3, v1)
        n = _norm_vec(_cross_product(e1, e2))
        face_normals.append(n)

    # 2. Edge to face adjacency
    edge_faces: Dict[Tuple[int, int], List[int]] = {}
    for fi, f in enumerate(faces):
        m = len(f)
        for i in range(m):
            j = (i + 1) % m
            edge = (min(f[i], f[j]), max(f[i], f[j]))
            if edge not in edge_faces:
                edge_faces[edge] = []
            edge_faces[edge].append(fi)

    # 3. Manifold edge angle audit
    creases: List[Dict[str, Any]] = []
    for (v_a, v_b), f_list in edge_faces.items():
        if len(f_list) == 2:
            n1 = face_normals[f_list[0]]
            n2 = face_normals[f_list[1]]
            dot_val = max(-1.0, min(1.0, _dot_product(n1, n2)))
            if dot_val < cos_threshold:
                fold_angle = 180.0 - math.degrees(math.acos(dot_val))
                midpoint = (
                    0.5 * (vertices[v_a][0] + vertices[v_b][0]),
                    0.5 * (vertices[v_a][1] + vertices[v_b][1]),
                    0.5 * (vertices[v_a][2] + vertices[v_b][2]),
                )
                creases.append({
                    "edge": (v_a, v_b),
                    "faces": (f_list[0], f_list[1]),
                    "cos_theta": dot_val,
                    "fold_angle_deg": fold_angle,
                    "location": list(midpoint),
                })
    return creases


def evaluate_rig_skinning_deformation(
    rest_vertices: List[Tuple[float, float, float]],
    posed_vertices: List[Tuple[float, float, float]],
    faces: List[Tuple[int, ...]],
    joint_specs: List[Dict[str, Any]],
    object_name: str = "Character_Mesh",
) -> Tuple[List[JointDeformationMetrics], List[DefectItem]]:
    """
    Evaluates joint volume conservation rho_V = V_posed / V_rest and acute dihedral creasing
    for active bending joints.
    """
    joint_results: List[JointDeformationMetrics] = []
    defects: List[DefectItem] = []

    # 1. Global acute dihedral creases on deformed mesh
    creases = compute_mesh_dihedral_creases(posed_vertices, faces, cos_threshold=-0.85)
    for c in creases:
        cos_th = c["cos_theta"]
        sev = DefectSeverity.CRITICAL if cos_th < -0.95 else DefectSeverity.MAJOR
        defects.append(DefectItem(
            defect_id=f"SKIN_CREASE_{uuid.uuid4().hex[:4]}",
            category=DefectCategory.SKINNING_PINCH,
            defect_type="SKINNING_ACUTE_CREASE",
            severity=sev,
            affected_objects=[object_name],
            object_name=object_name,
            description=f"Acute dihedral crease on '{object_name}': cos theta = {cos_th:.3f} (fold angle = {c['fold_angle_deg']:.1f} deg < 30 deg).",
            location=c["location"],
            affected_vertices=list(c["edge"]),
            affected_faces=list(c["faces"]),
            metrics={"cos_theta": cos_th, "fold_angle_deg": c["fold_angle_deg"]},
            recommendation=ActionableRecommendation(
                action="SMOOTH_SKINNING_WEIGHTS",
                category=DefectCategory.SKINNING_PINCH,
                target_objects=[object_name],
                parameters={"crease_edge": list(c["edge"])},
                guidance="Apply Laplacian smoothing to skin weights across adjacent vertex loops to eliminate pinched creasing.",
            ),
        ))

    # 2. Joint Volume Conservation
    for j_spec in joint_specs:
        j_name = j_spec["name"]
        p_center = j_spec["center"]
        axis_dir = j_spec.get("axis", (0.0, 0.0, 1.0))
        span = j_spec.get("span", 0.05)
        method = j_spec.get("method", "slice")

        if method in ("divergence", "watertight"):
            v_rest = compute_mesh_signed_volume(rest_vertices, faces)
            v_posed = compute_mesh_signed_volume(posed_vertices, faces)
        else:
            v_rest = compute_bounding_slice_volume(rest_vertices, faces, p_center, axis_dir, span_min=-span, span_max=span)
            v_posed = compute_bounding_slice_volume(posed_vertices, faces, p_center, axis_dir, span_min=-span, span_max=span)

        rho_v = float(round(v_posed / max(1e-6, v_rest), 3)) if v_rest > 0 else 1.0
        is_conserved = bool(0.80 <= rho_v <= 1.25)

        if rho_v < 0.80:
            sev = DefectSeverity.CRITICAL if rho_v < 0.65 else DefectSeverity.MAJOR
            defects.append(DefectItem(
                defect_id=f"SKIN_COLLAPSE_{j_name}_{uuid.uuid4().hex[:4]}",
                category=DefectCategory.SKINNING_PINCH,
                defect_type="SKINNING_VOLUME_COLLAPSE",
                severity=sev,
                affected_objects=[object_name],
                object_name=object_name,
                description=f"Candy-wrapper collapse at joint '{j_name}': volume retention ratio rho_V = {rho_v:.3f} < 0.80 (volume loss > 20%).",
                location=list(p_center),
                metrics={"joint": j_name, "volume_retention_ratio": rho_v, "v_rest": v_rest, "v_posed": v_posed},
                recommendation=ActionableRecommendation(
                    action="ACTIVATE_DUAL_BONE_TWIST_SKINNING",
                    category=DefectCategory.SKINNING_PINCH,
                    target_objects=[object_name],
                    parameters={"joint": j_name, "volume_ratio": rho_v},
                    guidance=f"Decompose {j_name} into dual-bone twist chains or use dual-quaternion skinning to eliminate candy-wrapper pinching.",
                ),
            ))
        elif rho_v > 1.25:
            defects.append(DefectItem(
                defect_id=f"SKIN_BULGE_{j_name}_{uuid.uuid4().hex[:4]}",
                category=DefectCategory.SKINNING_PINCH,
                defect_type="SKINNING_ABNORMAL_BULGE",
                severity=DefectSeverity.MAJOR,
                affected_objects=[object_name],
                object_name=object_name,
                description=f"Abnormal joint bulging at '{j_name}': volume ratio rho_V = {rho_v:.3f} > 1.25 (expansion > 25%).",
                location=list(p_center),
                metrics={"joint": j_name, "volume_retention_ratio": rho_v},
            ))

        joint_results.append(JointDeformationMetrics(
            joint_name=j_name,
            rest_volume=v_rest,
            posed_volume=v_posed,
            volume_ratio=rho_v,
            min_dihedral_cos=min([c["cos_theta"] for c in creases] or [1.0]),
            min_fold_angle_deg=min([c["fold_angle_deg"] for c in creases] or [180.0]),
            pinched_edge_count=len(creases),
            is_volume_conserved=is_conserved,
            is_crease_free=(len(creases) == 0),
        ))

    return joint_results, defects


def evaluate_rig_skinning_pinch(
    armature_obj_name: str,
    mesh_obj_name: str,
) -> List[DefectItem]:
    """Compatibility wrapper evaluating skinning deformation from Blender objects."""
    if not HAS_BLENDER or not bpy or not bpy.data.objects.get(mesh_obj_name):
        return []
    mesh_obj = bpy.data.objects[mesh_obj_name]
    verts = [tuple(v.co) for v in mesh_obj.data.vertices]
    faces = [tuple(p.vertices) for p in mesh_obj.data.polygons]
    creases = compute_mesh_dihedral_creases(verts, faces, cos_threshold=-0.85)
    defects = []
    for c in creases:
        defects.append(DefectItem(
            defect_id=f"SKIN_PINCH_{uuid.uuid4().hex[:4]}",
            category=DefectCategory.SKINNING_PINCH,
            severity=DefectSeverity.MAJOR,
            affected_objects=[mesh_obj_name],
            description=f"Dihedral creasing on {mesh_obj_name}: cos theta = {c['cos_theta']:.2f}.",
            location=c["location"],
        ))
    return defects

__all__ = [
    "JointDeformationMetrics",
    "compute_mesh_signed_volume",
    "compute_bounding_slice_volume",
    "compute_mesh_dihedral_creases",
    "evaluate_rig_skinning_deformation",
    "evaluate_rig_skinning_pinch",
]
