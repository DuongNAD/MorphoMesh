"""
MorphoMesh: Mesh Penetration & Grooming Collision Evaluation Engine.

Analyzes signed distance clearances between cloth-body, cloth-cloth, and
hair curve guides, identifying garment clipping, skin bursts, and grooming intersections.
"""

from __future__ import annotations

import math
import time
import uuid
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import numpy as np

from morphomesh.models import (
    ActionableRecommendation,
    BoundingBox3D,
    DefectCategory,
    DefectItem,
    DefectSeverity,
)

from .geometry_math import (
    _add_vec,
    _cross_product,
    _dot_product,
    _norm_vec,
    _scale_vec,
    _sub_vec,
    _vec_len,
    point_to_triangle_distance_eberly,
    ray_triangle_intersection_moller_trumbore,
    triangle_triangle_intersection_moller,
)
from .bvh import HAS_BLENDER, PurePythonBVHTree, bpy, get_bvh_tree

def _compute_vertex_normals(
    verts: List[Tuple[float, float, float]],
    polys: List[Tuple[int, ...]],
) -> List[Tuple[float, float, float]]:
    """Computes area-weighted unit vertex normals."""
    v_norms = [[0.0, 0.0, 0.0] for _ in range(len(verts))]
    for poly in polys:
        if len(poly) < 3:
            continue
        v0 = verts[poly[0]]
        for i in range(1, len(poly) - 1):
            v1 = verts[poly[i]]
            v2 = verts[poly[i + 1]]
            e1 = _sub_vec(v1, v0)
            e2 = _sub_vec(v2, v0)
            fn = _cross_product(e1, e2)  # magnitude proportional to 2x triangle area
            for idx in (poly[0], poly[i], poly[i + 1]):
                v_norms[idx][0] += fn[0]
                v_norms[idx][1] += fn[1]
                v_norms[idx][2] += fn[2]

    result = []
    for n in v_norms:
        l = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
        if l > 1e-12:
            result.append((n[0] / l, n[1] / l, n[2] / l))
        else:
            result.append((0.0, 0.0, 1.0))
    return result


def _find_garment_boundary_edges(
    verts: List[Tuple[float, float, float]],
    polys: List[Tuple[int, ...]],
) -> Dict[Tuple[int, int], Tuple[float, float, float]]:
    """
    Finds open boundary edges (belonging to exactly 1 polygon).
    Returns mapping: edge_key (min_idx, max_idx) -> unit in-plane outward normal u_out.
    """
    edge_poly_map: Dict[Tuple[int, int], List[int]] = {}
    for p_idx, poly in enumerate(polys):
        n_p = len(poly)
        for i in range(n_p):
            i1 = poly[i]
            i2 = poly[(i + 1) % n_p]
            ekey = (min(i1, i2), max(i1, i2))
            edge_poly_map.setdefault(ekey, []).append(p_idx)

    boundary_edge_normals: Dict[Tuple[int, int], Tuple[float, float, float]] = {}
    for ekey, p_list in edge_poly_map.items():
        if len(p_list) == 1:
            p_idx = p_list[0]
            poly = polys[p_idx]
            v0 = verts[poly[0]]
            v1 = verts[poly[1]]
            v2 = verts[poly[2]]
            fn = _cross_product(_sub_vec(v1, v0), _sub_vec(v2, v0))
            fn_len = math.sqrt(fn[0] * fn[0] + fn[1] * fn[1] + fn[2] * fn[2])
            if fn_len > 1e-12:
                fn = (fn[0] / fn_len, fn[1] / fn_len, fn[2] / fn_len)
            else:
                fn = (0.0, 0.0, 1.0)

            va = verts[ekey[0]]
            vb = verts[ekey[1]]
            e_vec = _sub_vec(vb, va)
            u = _cross_product(e_vec, fn)
            u_len = math.sqrt(u[0] * u[0] + u[1] * u[1] + u[2] * u[2])
            if u_len > 1e-12:
                u = (u[0] / u_len, u[1] / u_len, u[2] / u_len)
                p_c = [sum(verts[v][k] for v in poly) / len(poly) for k in range(3)]
                mid_e = _scale_vec(_add_vec(va, vb), 0.5)
                to_mid = _sub_vec(mid_e, (p_c[0], p_c[1], p_c[2]))
                if _dot_product(u, to_mid) < 0:
                    u = (-u[0], -u[1], -u[2])
                boundary_edge_normals[ekey] = u

    return boundary_edge_normals


def evaluate_mesh_penetration(
    body_obj_name: str,
    garment_obj_names: List[str],
    clearance_tolerance: float = 0.0005,
    max_search_radius: float = 0.05,
    body_geo: Optional[Tuple[List[Any], List[Any]]] = None,
    garment_geos: Optional[Dict[str, Tuple[List[Any], List[Any]]]] = None,
) -> List[DefectItem]:
    """
    Evaluates signed distance and face overlaps between garments and body mesh.
    Detects:
    1. Garment vertex penetration: s_i = (w_i - p_i) . n_i < -clearance_tolerance
    2. Reverse penetration (Skin burst): Body vertices protruding outward through garment
    3. Triangle-triangle surface piercing via BVHTree overlap
    """
    defects: List[DefectItem] = []

    # 1. Resolve body geometry
    b_verts: List[Tuple[float, float, float]] = []
    b_polys: List[Tuple[int, ...]] = []

    if body_geo is not None:
        b_verts = [(float(v[0]), float(v[1]), float(v[2])) for v in body_geo[0]]
        b_polys = [tuple(int(x) for x in p) for p in body_geo[1]]
    elif HAS_BLENDER and bpy and bpy.data.objects.get(body_obj_name):
        b_obj = bpy.data.objects[body_obj_name]
        depsgraph = bpy.context.evaluated_depsgraph_get() if bpy.context else None
        eval_b = b_obj.evaluated_get(depsgraph) if depsgraph else b_obj
        m = eval_b.to_mesh() if hasattr(eval_b, "to_mesh") else eval_b.data
        mw = b_obj.matrix_world
        b_verts = [tuple(mw @ v.co) for v in m.vertices]
        b_polys = [tuple(p.vertices) for p in m.polygons]
        if hasattr(eval_b, "to_mesh_clear"):
            eval_b.to_mesh_clear()

    if len(b_verts) == 0 or len(b_polys) == 0:
        return defects

    bvh_body = get_bvh_tree(b_verts, b_polys)
    b_v_norms = _compute_vertex_normals(b_verts, b_polys)

    # 2. Iterate through each garment mesh
    for g_name in garment_obj_names:
        g_verts: List[Tuple[float, float, float]] = []
        g_polys: List[Tuple[int, ...]] = []

        if garment_geos is not None and g_name in garment_geos:
            g_verts = [(float(v[0]), float(v[1]), float(v[2])) for v in garment_geos[g_name][0]]
            g_polys = [tuple(int(x) for x in p) for p in garment_geos[g_name][1]]
        elif HAS_BLENDER and bpy and bpy.data.objects.get(g_name):
            g_obj = bpy.data.objects[g_name]
            depsgraph = bpy.context.evaluated_depsgraph_get() if bpy.context else None
            eval_g = g_obj.evaluated_get(depsgraph) if depsgraph else g_obj
            m = eval_g.to_mesh() if hasattr(eval_g, "to_mesh") else eval_g.data
            mw = g_obj.matrix_world
            g_verts = [tuple(mw @ v.co) for v in m.vertices]
            g_polys = [tuple(p.vertices) for p in m.polygons]
            if hasattr(eval_g, "to_mesh_clear"):
                eval_g.to_mesh_clear()

        if len(g_verts) == 0 or len(g_polys) == 0:
            continue

        bvh_garm = get_bvh_tree(g_verts, g_polys)
        g_v_norms = _compute_vertex_normals(g_verts, g_polys)
        boundary_edges = _find_garment_boundary_edges(g_verts, g_polys)

        penetrations: List[Dict[str, Any]] = []
        penetrated_vert_indices: List[int] = []
        max_depth_m = 0.0

        for v_idx, w_i in enumerate(g_verts):
            loc, norm, f_idx, dist = bvh_body.find_nearest(w_i, max_dist=max_search_radius)
            if loc is not None and norm is not None:
                offset = _sub_vec(w_i, loc)
                s_i = _dot_product(offset, norm)
                if s_i < -clearance_tolerance:
                    # Normal alignment filtering: garment normal should point outward in body normal direction
                    norm_align = _dot_product(g_v_norms[v_idx], norm)
                    if norm_align <= 0.3:
                        continue  # Skip grazing contacts and non-opposing faces

                    depth = -s_i
                    if depth > max_depth_m:
                        max_depth_m = depth
                    penetrated_vert_indices.append(v_idx)
                    penetrations.append({
                        "vert_index": v_idx,
                        "location": list(w_i),
                        "depth_m": depth,
                        "face_idx": f_idx,
                    })

        # Reverse penetration (Skin burst): Body vertices piercing out through garment
        skin_bursts: List[Dict[str, Any]] = []
        g_min_z = min(v[2] for v in g_verts)
        g_max_z = max(v[2] for v in g_verts)
        for b_idx, b_j in enumerate(b_verts):
            # Tier 1: Height clamping - geometry past collar or hem is exposed anatomy, not burst
            if g_min_z + 0.002 <= b_j[2] <= g_max_z - 0.002:
                loc_g, norm_g, f_g, dist_g = bvh_garm.find_nearest(b_j, max_dist=max_search_radius)
                if loc_g is not None and norm_g is not None:
                    # Tier 2: Dual-sided surface normal alignment: skin normal must align with burst direction
                    b_norm = b_v_norms[b_idx]
                    if _dot_product(b_norm, norm_g) <= 0.3:
                        continue

                    offset_g = _sub_vec(b_j, loc_g)
                    s_burst = _dot_product(offset_g, norm_g)
                    if s_burst > clearance_tolerance:
                        # Tier 3: Garment boundary edge opening filtering
                        is_open_boundary = False
                        if f_g is not None and f_g < len(g_polys):
                            poly = g_polys[f_g]
                            n_p = len(poly)
                            for ei in range(n_p):
                                i1, i2 = poly[ei], poly[(ei + 1) % n_p]
                                ekey = (min(i1, i2), max(i1, i2))
                                if ekey in boundary_edges:
                                    u_out = boundary_edges[ekey]
                                    disp_out = _dot_product(offset_g, u_out)
                                    if disp_out > 0.001:  # Stepped past open garment boundary
                                        is_open_boundary = True
                                        break
                        if is_open_boundary:
                            continue

                        skin_bursts.append({
                            "vert_index": b_idx,
                            "location": list(b_j),
                            "depth_m": s_burst,
                        })

        # Triangle overlaps
        overlaps = bvh_body.overlap(bvh_garm)

        # Flag Garment Penetration Defect
        if penetrations:
            max_depth_mm = max_depth_m * 1000.0
            sev = DefectSeverity.CRITICAL if max_depth_mm > 5.0 or len(penetrations) > 25 else (
                DefectSeverity.MAJOR if max_depth_mm > 1.0 or len(penetrations) >= 5 else DefectSeverity.MINOR
            )
            centroid = [
                sum(p["location"][0] for p in penetrations) / len(penetrations),
                sum(p["location"][1] for p in penetrations) / len(penetrations),
                sum(p["location"][2] for p in penetrations) / len(penetrations),
            ]
            rec_offset_m = round(1.25 * max_depth_m + 0.001, 4)
            rec_offset_mm = round(1.25 * max_depth_mm + 1.0, 2)
            defects.append(DefectItem(
                defect_id=f"PEN_{g_name}_{uuid.uuid4().hex[:4]}",
                category=DefectCategory.PENETRATION,
                severity=sev,
                affected_objects=[g_name, body_obj_name],
                source_object=g_name,
                target_object=body_obj_name,
                description=f"Garment '{g_name}' penetrates body '{body_obj_name}': {len(penetrations)} vertices submerged, max depth = {max_depth_mm:.2f}mm.",
                location=centroid,
                sample_locations=[p["location"] for p in penetrations[:10]],
                penetration_depth_mm=round(max_depth_mm, 2),
                penetration_count=len(penetrations),
                affected_vertices=penetrated_vert_indices[:50],
                metrics={"penetration_count": len(penetrations), "max_depth_mm": round(max_depth_mm, 2)},
                recommendation=ActionableRecommendation(
                    action="APPLY_SHRINKWRAP_CLEARANCE",
                    category=DefectCategory.PENETRATION,
                    target_objects=[g_name],
                    suggested_modifier="Shrinkwrap",
                    parameters={
                        "target": body_obj_name,
                        "offset": rec_offset_m,
                        "offset_m": rec_offset_m,
                        "offset_mm": rec_offset_mm,
                        "smooth_weights": True,
                        "smoothing_method": "LAPLACIAN",
                    },
                    guidance=(
                        f"Apply Shrinkwrap modifier to '{g_name}' targeting '{body_obj_name}' with offset >= {rec_offset_mm:.1f}mm "
                        f"(d_rec = 1.25 * d_pen + 1mm). Apply vertex weight proximity or Laplacian smoothing to the penetration vertex group."
                    ),
                ),
            ))

        # Flag Skin Burst Defect
        if skin_bursts:
            max_burst_mm = max(b["depth_m"] for b in skin_bursts) * 1000.0
            sev = DefectSeverity.CRITICAL if max_burst_mm > 3.0 else DefectSeverity.MAJOR
            defects.append(DefectItem(
                defect_id=f"BURST_{body_obj_name}_{uuid.uuid4().hex[:4]}",
                category=DefectCategory.PENETRATION,
                defect_type="SKIN_BURST",
                severity=sev,
                affected_objects=[body_obj_name, g_name],
                source_object=body_obj_name,
                target_object=g_name,
                description=f"Body '{body_obj_name}' bursts through garment '{g_name}': {len(skin_bursts)} skin vertices protruding, max burst = {max_burst_mm:.2f}mm.",
                location=skin_bursts[0]["location"],
                penetration_depth_mm=round(max_burst_mm, 2),
                penetration_count=len(skin_bursts),
                metrics={"skin_burst_count": len(skin_bursts), "max_burst_mm": round(max_burst_mm, 2)},
                recommendation=ActionableRecommendation(
                    action="EXPAND_GARMENT_CONTOUR",
                    category=DefectCategory.PENETRATION,
                    target_objects=[g_name],
                    guidance=f"Relax or expand garment '{g_name}' geometry around protruding body vertices.",
                ),
            ))

        # Flag Triangle Overlap Defect
        if overlaps and not penetrations and not skin_bursts:
            defects.append(DefectItem(
                defect_id=f"OVERLAP_{g_name}_{uuid.uuid4().hex[:4]}",
                category=DefectCategory.PENETRATION,
                defect_type="FACE_OVERLAP",
                severity=DefectSeverity.MINOR,
                affected_objects=[g_name, body_obj_name],
                description=f"Surface overlap detected between '{g_name}' and '{body_obj_name}' ({len(overlaps)} intersecting face pairs).",
                location=list(g_verts[0]),
                penetration_count=len(overlaps),
                metrics={"overlap_face_pairs": len(overlaps)},
            ))

    return defects


# ==============================================================================
# SECTION 3: HAIR GROOMING CURVE INTERSECTIONS ENGINE
# ==============================================================================

def evaluate_hair_grooming_intersections(
    hair_obj_names: List[str],
    body_obj_name: str,
    garment_obj_names: Optional[List[str]] = None,
    hair_splines: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    body_geo: Optional[Tuple[List[Any], List[Any]]] = None,
    garment_geos: Optional[Dict[str, Tuple[List[Any], List[Any]]]] = None,
) -> List[DefectItem]:
    """
    Evaluates hair curve collisions with scalp, body, and garments.
    Detects:
    1. Submerged roots (root inside cranium: s_root < -1.0mm)
    2. Detached floating roots (s_root > +4.0mm)
    3. Hair shaft collision through body/neck (s_eff < -0.5mm)
    4. Hair clipping through garments
    """
    defects: List[DefectItem] = []

    # 1. Resolve body geometry
    b_verts: List[Tuple[float, float, float]] = []
    b_polys: List[Tuple[int, ...]] = []

    if body_geo is not None:
        b_verts = [(float(v[0]), float(v[1]), float(v[2])) for v in body_geo[0]]
        b_polys = [tuple(int(x) for x in p) for p in body_geo[1]]
    elif HAS_BLENDER and bpy and bpy.data.objects.get(body_obj_name):
        b_obj = bpy.data.objects[body_obj_name]
        m = b_obj.data
        mw = b_obj.matrix_world
        b_verts = [tuple(mw @ v.co) for v in m.vertices]
        b_polys = [tuple(p.vertices) for p in m.polygons]

    if len(b_verts) == 0 or len(b_polys) == 0:
        return defects

    bvh_body = get_bvh_tree(b_verts, b_polys)

    # 2. Resolve garment BVH trees
    garment_bvhs: Dict[str, Any] = {}
    if garment_obj_names:
        for g_name in garment_obj_names:
            g_verts: List[Tuple[float, float, float]] = []
            g_polys: List[Tuple[int, ...]] = []
            if garment_geos is not None and g_name in garment_geos:
                g_verts = [(float(v[0]), float(v[1]), float(v[2])) for v in garment_geos[g_name][0]]
                g_polys = [tuple(int(x) for x in p) for p in garment_geos[g_name][1]]
            elif HAS_BLENDER and bpy and bpy.data.objects.get(g_name):
                g_obj = bpy.data.objects[g_name]
                m = g_obj.data
                mw = g_obj.matrix_world
                g_verts = [tuple(mw @ v.co) for v in m.vertices]
                g_polys = [tuple(p.vertices) for p in m.polygons]
            if len(g_verts) > 0 and len(g_polys) > 0:
                garment_bvhs[g_name] = get_bvh_tree(g_verts, g_polys)

    # 3. Iterate through hair objects
    for h_name in hair_obj_names:
        splines_to_check: List[Dict[str, Any]] = []

        if hair_splines is not None and h_name in hair_splines:
            splines_to_check = hair_splines[h_name]
        elif HAS_BLENDER and bpy and bpy.data.objects.get(h_name):
            h_obj = bpy.data.objects[h_name]
            mw = h_obj.matrix_world
            if hasattr(h_obj.data, "curves"):
                # Blender 4.5 Curves object
                for c in h_obj.data.curves:
                    pts = [tuple(mw @ p.co) for p in c.points]
                    splines_to_check.append({"points": pts, "radii": [0.001] * len(pts)})
            elif hasattr(h_obj.data, "splines"):
                # Legacy Curve object
                for s in h_obj.data.splines:
                    pts = [tuple(mw @ p.co[:3]) for p in s.points]
                    splines_to_check.append({"points": pts, "radii": [0.001] * len(pts)})

        if not splines_to_check:
            continue

        submerged_roots = []
        detached_roots = []
        shaft_collisions = []
        garment_collisions = []

        for s_idx, spline in enumerate(splines_to_check):
            pts = spline.get("points") or []
            radii = spline.get("radii") or [0.001] * len(pts)
            if len(pts) < 2:
                continue

            # Check Root (p0)
            p0 = pts[0]
            loc, norm, _, dist = bvh_body.find_nearest(p0, max_dist=0.08)
            if loc is not None and norm is not None:
                offset = _sub_vec(p0, loc)
                s_root = _dot_product(offset, norm)
                if s_root < -0.001:  # Submerged deeper than 1mm
                    submerged_roots.append({
                        "strand_idx": s_idx,
                        "location": list(p0),
                        "depth_mm": -s_root * 1000.0,
                    })
                elif s_root > 0.004:  # Detached further than 4mm
                    detached_roots.append({
                        "strand_idx": s_idx,
                        "location": list(p0),
                        "distance_mm": s_root * 1000.0,
                    })

            # Check Shaft (p1..pK-1)
            for k in range(1, len(pts)):
                pk = pts[k]
                rk = radii[k] if k < len(radii) else 0.001
                loc_b, norm_b, _, d_b = bvh_body.find_nearest(pk, max_dist=0.05)
                if loc_b is not None and norm_b is not None:
                    offset_b = _sub_vec(pk, loc_b)
                    s_eff = _dot_product(offset_b, norm_b) - rk
                    if s_eff < -0.0005:  # Collision threshold 0.5mm
                        shaft_collisions.append({
                            "strand_idx": s_idx,
                            "point_idx": k,
                            "location": list(pk),
                            "depth_mm": -s_eff * 1000.0,
                        })

                # Check garments
                for g_n, g_bvh in garment_bvhs.items():
                    loc_g, norm_g, _, d_g = g_bvh.find_nearest(pk, max_dist=0.03)
                    if loc_g is not None and norm_g is not None:
                        offset_g = _sub_vec(pk, loc_g)
                        s_g_eff = _dot_product(offset_g, norm_g) - rk
                        if s_g_eff < -0.0005:
                            garment_collisions.append({
                                "garment": g_n,
                                "strand_idx": s_idx,
                                "location": list(pk),
                                "depth_mm": -s_g_eff * 1000.0,
                            })

        # Flag Submerged Roots
        if submerged_roots:
            max_depth_mm = max(r["depth_mm"] for r in submerged_roots)
            sev = DefectSeverity.CRITICAL if max_depth_mm > 5.0 or len(submerged_roots) > 10 else DefectSeverity.MAJOR
            defects.append(DefectItem(
                defect_id=f"GROOM_ROOT_{h_name}_{uuid.uuid4().hex[:4]}",
                category=DefectCategory.GROOMING_COLLISION,
                defect_type="GROOMING_ROOT_SUBMERGED",
                severity=sev,
                affected_objects=[h_name, body_obj_name],
                source_object=h_name,
                target_object=body_obj_name,
                description=f"Hair '{h_name}' has {len(submerged_roots)} roots submerged inside cranium (max depth {max_depth_mm:.2f}mm).",
                location=submerged_roots[0]["location"],
                penetration_depth_mm=round(max_depth_mm, 2),
                penetration_count=len(submerged_roots),
                metrics={"submerged_roots_count": len(submerged_roots), "max_submerged_depth_mm": round(max_depth_mm, 2)},
                recommendation=ActionableRecommendation(
                    action="PROJECT_HAIR_ROOTS_TO_SCALP",
                    category=DefectCategory.GROOMING_COLLISION,
                    target_objects=[h_name],
                    parameters={"offset_mm": 1.0},
                    guidance=(
                        "Project hair curve root control points to scalp surface with +1.0mm normal clearance. "
                        "In Curves Sculpt Mode, use the Comb Brush with front/side projection to groom intersecting hair splines away from the scalp/garment surface."
                    ),
                ),
            ))

        # Flag Detached Roots
        if detached_roots:
            max_dist_mm = max(r["distance_mm"] for r in detached_roots)
            defects.append(DefectItem(
                defect_id=f"GROOM_FLOAT_{h_name}_{uuid.uuid4().hex[:4]}",
                category=DefectCategory.GROOMING_COLLISION,
                defect_type="GROOMING_ROOT_DETACHED",
                severity=DefectSeverity.MINOR,
                affected_objects=[h_name, body_obj_name],
                description=f"Hair '{h_name}' has {len(detached_roots)} floating/detached roots (max distance {max_dist_mm:.2f}mm from cranium).",
                location=detached_roots[0]["location"],
                metrics={"detached_roots_count": len(detached_roots), "max_distance_mm": round(max_dist_mm, 2)},
            ))

        # Flag Shaft Body Collisions
        if shaft_collisions:
            max_s_depth = max(c["depth_mm"] for c in shaft_collisions)
            sev = DefectSeverity.CRITICAL if max_s_depth > 10.0 else DefectSeverity.MAJOR
            defects.append(DefectItem(
                defect_id=f"GROOM_BODY_{h_name}_{uuid.uuid4().hex[:4]}",
                category=DefectCategory.GROOMING_COLLISION,
                defect_type="GROOMING_BODY_COLLISION",
                severity=sev,
                affected_objects=[h_name, body_obj_name],
                description=f"Hair shaft in '{h_name}' pierces body geometry ({len(shaft_collisions)} intersecting samples, max depth {max_s_depth:.2f}mm).",
                location=shaft_collisions[0]["location"],
                penetration_depth_mm=round(max_s_depth, 2),
                penetration_count=len(shaft_collisions),
                metrics={"shaft_collision_count": len(shaft_collisions), "max_depth_mm": round(max_s_depth, 2)},
                recommendation=ActionableRecommendation(
                    action="CURVE_SCULPT_COMB_DEFLECTION",
                    category=DefectCategory.GROOMING_COLLISION,
                    target_objects=[h_name, body_obj_name],
                    suggested_modifier="Curves Sculpt Comb",
                    suggested_tool="Curves Sculpt Comb Brush",
                    parameters={"brush_mode": "COMB", "collision_distance_mm": 2.0, "falloff": "SMOOTH"},
                    guidance=(
                        f"In Curves Sculpt Mode, use the Comb Brush with front/side projection to groom intersecting hair splines "
                        f"away from the scalp/garment surface (enable surface collision with 2.0mm clearance against '{body_obj_name}')."
                    ),
                ),
            ))

        # Flag Garment Collisions
        if garment_collisions:
            max_g_depth = max(c["depth_mm"] for c in garment_collisions)
            garm_target = garment_collisions[0]["garment"]
            defects.append(DefectItem(
                defect_id=f"GROOM_GARM_{h_name}_{uuid.uuid4().hex[:4]}",
                category=DefectCategory.GROOMING_COLLISION,
                defect_type="GROOMING_GARMENT_COLLISION",
                severity=DefectSeverity.MAJOR if max_g_depth > 3.0 else DefectSeverity.MINOR,
                affected_objects=[h_name, garm_target],
                description=f"Hair '{h_name}' clips through garment '{garm_target}' ({len(garment_collisions)} points).",
                location=garment_collisions[0]["location"],
                penetration_depth_mm=round(max_g_depth, 2),
                penetration_count=len(garment_collisions),
                metrics={"garment_collision_count": len(garment_collisions)},
                recommendation=ActionableRecommendation(
                    action="CURVE_SCULPT_COMB_DEFLECTION",
                    category=DefectCategory.GROOMING_COLLISION,
                    target_objects=[h_name, garm_target],
                    suggested_modifier="Curves Sculpt Comb",
                    suggested_tool="Curves Sculpt Comb Brush",
                    parameters={"brush_mode": "COMB", "collision_distance_mm": 2.0, "falloff": "SMOOTH"},
                    guidance=(
                        f"In Curves Sculpt Mode, use the Comb Brush with front/side projection to groom intersecting hair splines "
                        f"away from garment '{garm_target}' surface (enable surface collision with 2.0mm clearance)."
                    ),
                ),
            ))

    return defects

__all__ = [
    "_compute_vertex_normals",
    "_find_garment_boundary_edges",
    "evaluate_mesh_penetration",
    "evaluate_hair_grooming_intersections",
]
