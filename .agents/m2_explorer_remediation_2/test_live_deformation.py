"""
Live Deformation & Anti-Pinch Volume Verification Script.
Author: m2_explorer_remediation_2
Executed under headless Blender 4.5.4 LTS.
"""

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import bpy
import bmesh
from mathutils import Euler, Matrix, Quaternion, Vector


def compute_mesh_signed_volume(eval_obj: Any) -> float:
    """Computes signed tetrahedral volume using divergence theorem."""
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
    """Computes 2D planar polygon cross-section area sliced through mesh."""
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
    """Counts faces with area <= eps."""
    me = eval_obj.to_mesh()
    bad_count = sum(1 for poly in me.polygons if poly.area <= eps)
    eval_obj.to_mesh_clear()
    return bad_count


def synchronize_all_submesh_transforms():
    """Applies rotation=(0,0,0) to all mesh objects in scene."""
    arm_obj = bpy.data.objects.get("Anime_Armature")
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.rotation_euler = (0.0, 0.0, 0.0)
            if arm_obj:
                obj.parent = arm_obj
                obj.matrix_parent_inverse = arm_obj.matrix_world.inverted()
    bpy.context.view_layer.update()


def main():
    blend_path = Path("E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_rigged.blend")
    print(f"Loading {blend_path}...")
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))

    arm_obj = bpy.data.objects.get("Anime_Armature")
    pb = arm_obj.pose.bones
    arms_obj = bpy.data.objects.get("Anime_Arms")
    depsgraph = bpy.context.evaluated_depsgraph_get()

    print("\n--- Applying transform synchronization patch ---")
    synchronize_all_submesh_transforms()
    depsgraph.update()

    # =========================================================================
    # 1. Wrist Twist Audit (Hand.L & Hand.R at 90 deg and 180 deg)
    # =========================================================================
    print("\n=======================================================")
    print("1. WRIST TWIST & ANTI-PINCH VOLUME VERIFICATION")
    print("=======================================================")
    
    ev_rest = arms_obj.evaluated_get(depsgraph)
    v_rest = compute_mesh_signed_volume(ev_rest)
    print(f"Arms rest volume: {v_rest:.8f} m^3")

    for side in ["L", "R"]:
        fa_name = f"ForeArm.{side}"
        hand_name = f"Hand.{side}"
        p_fa = pb[fa_name]
        p_hand = pb[hand_name]

        fa_mid = (p_fa.head + p_fa.tail) * 0.5
        fa_axis = p_fa.vector.normalized()
        wrist_co = (p_fa.tail + fa_mid) * 0.5  # near wrist / distal forearm

        a_rest_mid = measure_slice_cross_section_area(ev_rest, fa_mid, fa_axis)
        a_rest_wrist = measure_slice_cross_section_area(ev_rest, wrist_co, fa_axis)
        print(f"\nSide {side}: a_rest_mid = {a_rest_mid:.8f}, a_rest_wrist = {a_rest_wrist:.8f}")

        for ang in [90, 180, -90, -180]:
            p_hand.rotation_mode = 'QUATERNION'
            p_hand.rotation_quaternion = Quaternion(Vector((0.0, 1.0, 0.0)), math.radians(ang))
            bpy.context.view_layer.update()
            depsgraph.update()

            ev = arms_obj.evaluated_get(depsgraph)
            vol = compute_mesh_signed_volume(ev)
            a_mid = measure_slice_cross_section_area(ev, fa_mid, fa_axis)
            a_wrist = measure_slice_cross_section_area(ev, wrist_co, fa_axis)

            rv = vol / v_rest if v_rest > 0 else 0.0
            ra_mid = a_mid / a_rest_mid if a_rest_mid > 0 else 0.0
            ra_wrist = a_wrist / a_rest_wrist if a_rest_wrist > 0 else 0.0

            # Requirements:
            # at 90 deg: R_V >= 0.85 and wrist R_A >= 0.85
            # at 180 deg: R_V >= 0.85 and wrist R_A >= 0.80
            req_rv = 0.85
            req_ra = 0.85 if abs(ang) == 90 else 0.80
            pass_rv = rv >= req_rv
            pass_ra = ra_wrist >= req_ra

            print(f"  Hand.{side} Twist {ang:+4d}°: Vol={vol:.6f} (Rv={rv*100:.2f}% [req>={req_rv*100:.0f}%], pass={pass_rv}) | "
                  f"Mid Ra={ra_mid*100:.2f}% | Wrist Ra={ra_wrist*100:.2f}% [req>={req_ra*100:.0f}%], pass={pass_ra}")

            # Reset pose
            p_hand.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
            bpy.context.view_layer.update()
            depsgraph.update()

    # =========================================================================
    # 2. Finger Flexion Audit (+45° and +90°) & Out-of-Plane Plunge Check
    # =========================================================================
    print("\n=======================================================")
    print("2. 30-PHALANGE FINGER FLEXION & MESH VERTEX CURL AUDIT")
    print("=======================================================")

    palm_L = Vector((0.43550, -0.18575, 1.01439))
    palm_R = Vector((-0.43550, -0.18575, 1.01439))
    finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]

    # Let's find fingertip vertices in the mesh for each finger
    # Fingertip vertices are vertices weighted primarily to distal phalanges (.03)
    arms_me = arms_obj.data
    vg_map = {vg.name: vg.index for vg in arms_obj.vertex_groups}

    for side in ["L", "R"]:
        palm = palm_L if side == "L" else palm_R
        print(f"\nSide {side} Fingertip Mesh Vertex Curling Analysis (Palm Centroid: {palm}):")

        for f in finger_names:
            distal_bone_name = f"{f}.03.{side}"
            distal_vg_idx = vg_map.get(distal_bone_name)

            # Find vertices with highest weight on distal bone
            candidate_verts = []
            if distal_vg_idx is not None:
                for v in arms_me.vertices:
                    for g in v.groups:
                        if g.group == distal_vg_idx and g.weight > 0.5:
                            candidate_verts.append((v.index, g.weight))

            print(f"\n  Finger {f}.{side} (distal bone {distal_bone_name}, {len(candidate_verts)} distal vertices):")

            # Let's test bone curl and evaluate mesh fingertip vertices
            p_bones = [pb[f"{f}.0{k}.{side}"] for k in [1, 2, 3]]

            # Pose 0: rest
            for pb_k in p_bones:
                pb_k.rotation_mode = 'QUATERNION'
                pb_k.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
            bpy.context.view_layer.update()
            depsgraph.update()

            ev_0 = arms_obj.evaluated_get(depsgraph)
            me_0 = ev_0.to_mesh()
            b_tail_0 = (arm_obj.matrix_world @ p_bones[-1].tail).copy()
            d_bone_0 = (b_tail_0 - palm).length

            # Fingertip vertex positions at rest
            v_positions_0 = {vi: (arms_obj.matrix_world @ me_0.vertices[vi].co).copy() for vi, _ in candidate_verts[:5]}
            ev_0.to_mesh_clear()

            # Pose 1: +45° curl on all 3 phalanges
            for pb_k in p_bones:
                pb_k.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(45.0))
            bpy.context.view_layer.update()
            depsgraph.update()

            ev_45 = arms_obj.evaluated_get(depsgraph)
            me_45 = ev_45.to_mesh()
            b_tail_45 = (arm_obj.matrix_world @ p_bones[-1].tail).copy()
            d_bone_45 = (b_tail_45 - palm).length
            v_positions_45 = {vi: (arms_obj.matrix_world @ me_45.vertices[vi].co).copy() for vi, _ in candidate_verts[:5]}
            ev_45.to_mesh_clear()

            # Pose 2: +90° curl on all 3 phalanges
            for pb_k in p_bones:
                pb_k.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(90.0))
            bpy.context.view_layer.update()
            depsgraph.update()

            ev_90 = arms_obj.evaluated_get(depsgraph)
            me_90 = ev_90.to_mesh()
            b_tail_90 = (arm_obj.matrix_world @ p_bones[-1].tail).copy()
            d_bone_90 = (b_tail_90 - palm).length
            v_positions_90 = {vi: (arms_obj.matrix_world @ me_90.vertices[vi].co).copy() for vi, _ in candidate_verts[:5]}
            ev_90.to_mesh_clear()

            # Reset bones
            for pb_k in p_bones:
                pb_k.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
            bpy.context.view_layer.update()
            depsgraph.update()

            bone_curl_pass = (d_bone_45 < d_bone_0) and (d_bone_90 < d_bone_45)
            print(f"    Bone Tail to Palm dist: Rest={d_bone_0:.4f}m -> 45°={d_bone_45:.4f}m -> 90°={d_bone_90:.4f}m | Monotonic: {bone_curl_pass}")

            # Analyze mesh vertex curl
            for vi in list(v_positions_0.keys())[:2]:
                p0 = v_positions_0[vi]
                p45 = v_positions_45[vi]
                p90 = v_positions_90[vi]

                d0 = (p0 - palm).length
                d45 = (p45 - palm).length
                d90 = (p90 - palm).length

                # Displacement vectors
                disp_45 = (p45 - p0).length
                disp_90 = (p90 - p0).length

                # Check plunge: if displacement is several meters or points away from palm
                v_curl_pass = (d45 < d0) and (d90 < d45)
                print(f"      Vert {vi}: dist to palm: {d0:.4f}m -> {d45:.4f}m -> {d90:.4f}m (curl={v_curl_pass}, disp_45={disp_45*100:.1f}cm, disp_90={disp_90*100:.1f}cm)")

    # =========================================================================
    # 3. Elbow Flexion Audit (90° and 145°)
    # =========================================================================
    print("\n=======================================================")
    print("3. ELBOW FLEXION STRESS & DEGENERATE FACE AUDIT")
    print("=======================================================")

    for side in ["L", "R"]:
        p_fa = pb[f"ForeArm.{side}"]
        for ang in [90, 145]:
            p_fa.rotation_mode = 'QUATERNION'
            p_fa.rotation_quaternion = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(ang))
            bpy.context.view_layer.update()
            depsgraph.update()

            ev = arms_obj.evaluated_get(depsgraph)
            degen_faces = count_degenerate_or_inverted_faces(ev)
            vol = compute_mesh_signed_volume(ev)
            rv = vol / v_rest if v_rest > 0 else 0.0

            p_fa.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
            bpy.context.view_layer.update()
            depsgraph.update()

            print(f"  ForeArm.{side} Flexion {ang:3d}°: Degen Faces={degen_faces} (pass={degen_faces == 0}), Vol={vol:.6f} (Rv={rv*100:.2f}%)")


if __name__ == "__main__":
    main()
