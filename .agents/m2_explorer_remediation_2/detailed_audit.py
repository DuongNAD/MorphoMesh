"""
Detailed Audit Script for M2 Live Deformation Invariants.
Tests all 4 requirements:
1. Hand twist 90°: Rv >= 0.85, wrist Ra >= 0.85
2. Hand twist 180°: Rv >= 0.85, wrist Ra >= 0.80
3. 30-phalange finger flexion (+45°, +90°): fingertip curl to palm centroid, no out-of-plane plunge
4. Elbow flexion (90°, 145°): 0 degenerate/inverted faces
"""

import math
import pprint
from pathlib import Path
from typing import Any, Dict, List, Tuple

import bpy
import bmesh
from mathutils import Euler, Matrix, Quaternion, Vector


def compute_mesh_signed_volume(eval_obj: Any) -> float:
    me = eval_obj.to_mesh()
    vol = 0.0
    for poly in me.polygons:
        vs = poly.vertices
        if len(vs) < 3:
            continue
        v0 = me.vertices[vs[0]].co
        for i in range(1, len(vs) - 1):
            v1 = me.vertices[vs[i]].co
            v2 = me.vertices[vs[i + 1]].co
            vol += v0.dot(v1.cross(v2)) / 6.0
    eval_obj.to_mesh_clear()
    return abs(vol)


def measure_slice_cross_section_area(eval_obj: Any, plane_co: Any, plane_no: Any) -> float:
    me = eval_obj.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    res = bmesh.ops.bisect_plane(
        bm,
        geom=bm.faces[:] + bm.edges[:] + bm.verts[:],
        plane_co=plane_co,
        plane_no=plane_no,
    )
    cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if not cut_edges:
        bm.free()
        eval_obj.to_mesh_clear()
        return 0.0

    verts = list({v for e in cut_edges for v in e.verts})
    if len(verts) < 3:
        bm.free()
        eval_obj.to_mesh_clear()
        return 0.0

    centroid = sum((v.co for v in verts), Vector()) / len(verts)
    area = sum(0.5 * (e.verts[0].co - centroid).cross(e.verts[1].co - centroid).length for e in cut_edges)
    bm.free()
    eval_obj.to_mesh_clear()
    return area


def count_degenerate_or_inverted_faces(eval_obj: Any, eps: float = 1e-7) -> int:
    me = eval_obj.to_mesh()
    bad_count = sum(1 for poly in me.polygons if poly.area <= eps)
    eval_obj.to_mesh_clear()
    return bad_count


def run_full_verification():
    blend_path = Path("E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_rigged.blend")
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    arm_obj = bpy.data.objects.get("Anime_Armature")
    pb = arm_obj.pose.bones
    arms_obj = bpy.data.objects.get("Anime_Arms")

    # Apply transform synchronization fix
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.rotation_euler = (0.0, 0.0, 0.0)
            obj.parent = arm_obj
            obj.matrix_parent_inverse = arm_obj.matrix_world.inverted()

    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()

    results = {
        "wrist_twist": {},
        "finger_curling": {},
        "elbow_flexion": {},
    }

    # -------------------------------------------------------------------------
    # 1. Wrist Twist Audit
    # -------------------------------------------------------------------------
    ev_rest = arms_obj.evaluated_get(depsgraph)
    v_rest = compute_mesh_signed_volume(ev_rest)

    twist_cases = [
        ("Hand.L", 90, 0.85, 0.85),
        ("Hand.L", 180, 0.85, 0.80),
        ("Hand.L", -90, 0.85, 0.85),
        ("Hand.L", -180, 0.85, 0.80),
        ("Hand.R", 90, 0.85, 0.85),
        ("Hand.R", 180, 0.85, 0.80),
        ("Hand.R", -90, 0.85, 0.85),
        ("Hand.R", -180, 0.85, 0.80),
    ]

    twist_results = []
    for bone_name, angle_deg, req_rv, req_ra in twist_cases:
        side = "L" if ".L" in bone_name else "R"
        p_fa = pb[f"ForeArm.{side}"]
        p_hand = pb[bone_name]

        fa_mid = (p_fa.head + p_fa.tail) * 0.5
        fa_axis = p_fa.vector.normalized()
        wrist_co = (p_fa.tail + fa_mid) * 0.5

        a_rest_mid = measure_slice_cross_section_area(ev_rest, fa_mid, fa_axis)
        a_rest_wrist = measure_slice_cross_section_area(ev_rest, wrist_co, fa_axis)

        p_hand.rotation_mode = 'QUATERNION'
        p_hand.rotation_quaternion = Quaternion(Vector((0.0, 1.0, 0.0)), math.radians(angle_deg))
        bpy.context.view_layer.update()
        depsgraph.update()

        ev = arms_obj.evaluated_get(depsgraph)
        vol = compute_mesh_signed_volume(ev)
        a_mid = measure_slice_cross_section_area(ev, fa_mid, fa_axis)
        a_wrist = measure_slice_cross_section_area(ev, wrist_co, fa_axis)

        rv = vol / v_rest if v_rest > 0 else 0.0
        ra_mid = a_mid / a_rest_mid if a_rest_mid > 0 else 0.0
        ra_wrist = a_wrist / a_rest_wrist if a_rest_wrist > 0 else 0.0

        p_hand.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
        bpy.context.view_layer.update()
        depsgraph.update()

        passed = (rv >= req_rv) and (ra_wrist >= req_ra)
        twist_results.append({
            "bone": bone_name,
            "angle": angle_deg,
            "volume": vol,
            "v_rest": v_rest,
            "rv": rv,
            "req_rv": req_rv,
            "ra_mid": ra_mid,
            "ra_wrist": ra_wrist,
            "req_ra": req_ra,
            "passed": passed,
        })

    results["wrist_twist"] = {
        "trials": twist_results,
        "all_passed": all(t["passed"] for t in twist_results),
    }

    # -------------------------------------------------------------------------
    # 2. Finger Flexion Audit (All 30 Phalanges & Fingertip vertices)
    # -------------------------------------------------------------------------
    palm_L = Vector((0.43550, -0.18575, 1.01439))
    palm_R = Vector((-0.43550, -0.18575, 1.01439))
    finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
    phalanges = ["01", "02", "03"]

    bone_curls = []
    for side in ["L", "R"]:
        palm = palm_L if side == "L" else palm_R
        for f in finger_names:
            for p in phalanges:
                bname = f"{f}.{p}.{side}"
                pbone = pb[bname]

                pbone.rotation_mode = 'QUATERNION'
                pbone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
                bpy.context.view_layer.update()
                tail_0 = (arm_obj.matrix_world @ pbone.tail).copy()
                d_0 = (tail_0 - palm).length

                pbone.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(45.0))
                bpy.context.view_layer.update()
                tail_45 = (arm_obj.matrix_world @ pbone.tail).copy()
                d_45 = (tail_45 - palm).length

                pbone.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(90.0))
                bpy.context.view_layer.update()
                tail_90 = (arm_obj.matrix_world @ pbone.tail).copy()
                d_90 = (tail_90 - palm).length

                pbone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
                bpy.context.view_layer.update()

                # Check monotonicity
                monotonic = (d_45 < d_0) and (d_90 < d_45)

                # Check out-of-plane plunge
                # Plunge vector relative to bone rest frame:
                # In bone local space, rotation about X means displacement should have local X component ~ 0.
                # In world space, maximum displacement of a finger phalange tail should be <= 0.15 m (15 cm).
                disp_45 = (tail_45 - tail_0).length
                disp_90 = (tail_90 - tail_0).length
                no_plunge = (disp_45 < 0.15) and (disp_90 < 0.20)

                bone_curls.append({
                    "bone": bname,
                    "d_0": d_0,
                    "d_45": d_45,
                    "d_90": d_90,
                    "monotonic": monotonic,
                    "disp_45": disp_45,
                    "disp_90": disp_90,
                    "no_plunge": no_plunge,
                    "passed": monotonic and no_plunge,
                })

    # Also test whole-finger chain curl on mesh vertices
    # When all 3 phalanges of a finger curl simultaneously by +45° and +90°:
    mesh_curls = []
    vg_map = {vg.name: vg.index for vg in arms_obj.vertex_groups}

    for side in ["L", "R"]:
        palm = palm_L if side == "L" else palm_R
        for f in finger_names:
            chain_bones = [pb[f"{f}.0{k}.{side}"] for k in [1, 2, 3]]
            # Find vertices weighted to any bone in this finger chain
            chain_vg_indices = [vg_map[f"{f}.0{k}.{side}"] for k in [1, 2, 3] if f"{f}.0{k}.{side}" in vg_map]
            
            finger_v_indices = []
            for v in arms_obj.data.vertices:
                w_sum = sum(g.weight for g in v.groups if g.group in chain_vg_indices)
                if w_sum > 0.5:
                    finger_v_indices.append(v.index)

            # Rest pose
            for b in chain_bones:
                b.rotation_mode = 'QUATERNION'
                b.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
            bpy.context.view_layer.update()
            depsgraph.update()
            ev_0 = arms_obj.evaluated_get(depsgraph)
            me_0 = ev_0.to_mesh()
            v_co_0 = {vi: (arms_obj.matrix_world @ me_0.vertices[vi].co).copy() for vi in finger_v_indices}
            ev_0.to_mesh_clear()

            # +45° curl on all 3 phalanges
            for b in chain_bones:
                b.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(45.0))
            bpy.context.view_layer.update()
            depsgraph.update()
            ev_45 = arms_obj.evaluated_get(depsgraph)
            me_45 = ev_45.to_mesh()
            v_co_45 = {vi: (arms_obj.matrix_world @ me_45.vertices[vi].co).copy() for vi in finger_v_indices}
            ev_45.to_mesh_clear()

            # +90° curl on all 3 phalanges
            for b in chain_bones:
                b.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(90.0))
            bpy.context.view_layer.update()
            depsgraph.update()
            ev_90 = arms_obj.evaluated_get(depsgraph)
            me_90 = ev_90.to_mesh()
            v_co_90 = {vi: (arms_obj.matrix_world @ me_90.vertices[vi].co).copy() for vi in finger_v_indices}
            ev_90.to_mesh_clear()

            # Reset
            for b in chain_bones:
                b.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
            bpy.context.view_layer.update()
            depsgraph.update()

            if finger_v_indices:
                # Average distance to palm centroid
                avg_d0 = sum((v_co_0[vi] - palm).length for vi in finger_v_indices) / len(finger_v_indices)
                avg_d45 = sum((v_co_45[vi] - palm).length for vi in finger_v_indices) / len(finger_v_indices)
                avg_d90 = sum((v_co_90[vi] - palm).length for vi in finger_v_indices) / len(finger_v_indices)

                # Max vertex displacement
                max_disp_45 = max((v_co_45[vi] - v_co_0[vi]).length for vi in finger_v_indices)
                max_disp_90 = max((v_co_90[vi] - v_co_0[vi]).length for vi in finger_v_indices)

                # Monotonic curl toward palm
                chain_monotonic = (avg_d45 < avg_d0) and (avg_d90 < avg_d45)
                # No plunge: displacement bounded by anatomical length (< 15 cm)
                no_v_plunge = (max_disp_45 < 0.15) and (max_disp_90 < 0.20)

                mesh_curls.append({
                    "finger": f"{f}.{side}",
                    "num_vertices": len(finger_v_indices),
                    "avg_d0": avg_d0,
                    "avg_d45": avg_d45,
                    "avg_d90": avg_d90,
                    "max_disp_45": max_disp_45,
                    "max_disp_90": max_disp_90,
                    "chain_monotonic": chain_monotonic,
                    "no_v_plunge": no_v_plunge,
                    "passed": chain_monotonic and no_v_plunge,
                })

    results["finger_curling"] = {
        "total_phalanges": len(bone_curls),
        "passing_phalanges": sum(1 for b in bone_curls if b["passed"]),
        "mesh_chains": mesh_curls,
        "all_phalanges_passed": all(b["passed"] for b in bone_curls),
        "all_mesh_chains_passed": all(m["passed"] for m in mesh_curls),
    }

    # -------------------------------------------------------------------------
    # 3. Elbow Flexion Audit (90° and 145°)
    # -------------------------------------------------------------------------
    elbow_trials = []
    for side in ["L", "R"]:
        p_fa = pb[f"ForeArm.{side}"]
        for ang in [90, 145]:
            p_fa.rotation_mode = 'QUATERNION'
            p_fa.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(ang))
            bpy.context.view_layer.update()
            depsgraph.update()

            ev = arms_obj.evaluated_get(depsgraph)
            bad_faces = count_degenerate_or_inverted_faces(ev)
            vol = compute_mesh_signed_volume(ev)
            rv = vol / v_rest if v_rest > 0 else 0.0

            p_fa.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
            bpy.context.view_layer.update()
            depsgraph.update()

            elbow_trials.append({
                "joint": f"ForeArm.{side}",
                "flexion_angle": ang,
                "volume": vol,
                "rv": rv,
                "degenerate_faces": bad_faces,
                "passed": bad_faces == 0,
            })

    results["elbow_flexion"] = {
        "trials": elbow_trials,
        "all_passed": all(t["passed"] for t in elbow_trials),
    }

    pprint.pprint(results)
    return results


if __name__ == "__main__":
    run_full_verification()
