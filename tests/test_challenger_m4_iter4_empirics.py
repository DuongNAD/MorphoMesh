import sys
import os
import math
import subprocess
from pathlib import Path

try:
    import bpy
    import bmesh
    import mathutils
except ImportError:
    bpy = None
    bmesh = None
    mathutils = None

STANDARDIZED_29_VGROUPS = [
    "head", "face", "eyes_left", "eyes_right", "eyelids", "eyebrows",
    "mouth", "lips", "teeth", "tongue", "neck", "torso", "chest",
    "waist", "hips", "arm_upper_L", "arm_lower_L", "hand_L", "fingers_L",
    "arm_upper_R", "arm_lower_R", "hand_R", "fingers_R",
    "leg_upper_L", "leg_lower_L", "foot_L", "leg_upper_R", "leg_lower_R", "foot_R"
]

ARKIT_52_KEYS = [
    "eyeBlinkLeft", "eyeLookDownLeft", "eyeLookInLeft", "eyeLookOutLeft", "eyeLookUpLeft", "eyeSquintLeft", "eyeWideLeft",
    "eyeBlinkRight", "eyeLookDownRight", "eyeLookInRight", "eyeLookOutRight", "eyeLookUpRight", "eyeSquintRight", "eyeWideRight",
    "jawForward", "jawLeft", "jawRight", "jawOpen",
    "mouthClose", "mouthFunnel", "mouthPucker", "mouthLeft", "mouthRight",
    "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight",
    "mouthDimpleLeft", "mouthDimpleRight", "mouthStretchLeft", "mouthStretchRight",
    "mouthRollLower", "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper",
    "mouthPressLeft", "mouthPressRight", "mouthLowerDownLeft", "mouthLowerDownRight",
    "mouthUpperUpLeft", "mouthUpperUpRight",
    "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
    "noseSneerLeft", "noseSneerRight", "tongueOut"
]

FINGER_DEF_BONES = [
    "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
    "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R"
]

def run_adversarial_challenge():
    print("=" * 80)
    print("EMPIRICAL CHALLENGER VERIFICATION HARNESS (Milestone 4 Iteration 4)")
    print("Target: output/yu_nian_an/Yu_Nian_An_Master.blend")
    print("=" * 80)

    failures = []
    warnings = []

    # =========================================================================
    # PART 1: ANATOMY & QUAD TOPOLOGY VERIFICATION
    # =========================================================================
    print("\n" + "-" * 40)
    print("PART 1: ANATOMY & QUAD TOPOLOGY VERIFICATION")
    print("-" * 40)

    body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
    if not body_obj:
        print("CRITICAL DEFECT: Object 'Yu_Nian_An_Body' not found!")
        failures.append("Object 'Yu_Nian_An_Body' missing from Master.blend")
        return failures

    mesh = body_obj.data
    n_verts = len(mesh.vertices)
    n_polys = len(mesh.polygons)
    print(f"Body Mesh Vertex Count: {n_verts}")
    print(f"Body Mesh Polygon Count: {n_polys}")

    quad_count = sum(1 for p in mesh.polygons if len(p.vertices) == 4)
    tri_count = sum(1 for p in mesh.polygons if len(p.vertices) == 3)
    ngon_count = sum(1 for p in mesh.polygons if len(p.vertices) > 4)

    print(f"  Quads: {quad_count} ({quad_count / n_polys * 100:.2f}%)")
    print(f"  Triangles: {tri_count}")
    print(f"  N-gons: {ngon_count}")

    if quad_count != 2036:
        failures.append(f"Body mesh quads count {quad_count} != 2,036 requirement!")
    if tri_count != 0:
        failures.append(f"Body mesh has {tri_count} triangles (must be 0 pure quads)!")
    if ngon_count != 0:
        failures.append(f"Body mesh has {ngon_count} n-gons (must be 0 pure quads)!")

    # BMesh integrity checks
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
    boundary_edges = [e for e in bm.edges if e.is_boundary]
    zero_area_faces = [f for f in bm.faces if f.calc_area() < 1e-8]

    print(f"  Non-manifold Edges: {len(non_manifold_edges)}")
    print(f"  Boundary Edges: {len(boundary_edges)}")
    print(f"  Zero-area Faces: {len(zero_area_faces)}")

    if len(non_manifold_edges) > 0:
        failures.append(f"Body mesh has {len(non_manifold_edges)} non-manifold edges!")
    if len(boundary_edges) > 0:
        failures.append(f"Body mesh has {len(boundary_edges)} boundary edges (watertightness violation)!")
    if len(zero_area_faces) > 0:
        failures.append(f"Body mesh has {len(zero_area_faces)} zero-area degenerate faces!")

    # Facial Contours Empirical Verification
    print("\n--- Empirical Facial Contour Analysis ---")
    world_verts = [body_obj.matrix_world @ v.co for v in mesh.vertices]

    # Nose inspection: look for vertices at midline |X| < 0.015, Z in [1.45, 1.55]
    midline_face = [(i, v) for i, v in enumerate(world_verts) if abs(v.x) < 0.015 and 1.45 <= v.z <= 1.55]
    midline_sorted_y = sorted(midline_face, key=lambda x: x[1].y)
    most_anterior_face = midline_sorted_y[0] if midline_sorted_y else None
    if most_anterior_face:
        nose_idx, nose_pos = most_anterior_face
        print(f"  Most anterior midline vertex (Nose Tip candidate): idx={nose_idx}, pos=({nose_pos.x:.4f}, {nose_pos.y:.4f}, {nose_pos.z:.4f})")
        if nose_pos.y > -0.135:
            failures.append(f"Nose tip anterior protrusion insufficient: Y={nose_pos.y:.4f}m (expected < -0.135m)")
        else:
            print(f"  Nose protrusion check: PASS (Y = {nose_pos.y:.4f}m < -0.135m)")
        if not (1.48 <= nose_pos.z <= 1.52):
            warnings.append(f"Nose tip Z={nose_pos.z:.4f}m outside nominal [1.48, 1.52]")
    else:
        failures.append("No midline facial vertices detected around nose level!")

    # Orbital socket check: compare eye socket vertices at X ~ +/- 0.035, Z ~ 1.52 vs midline
    orbit_verts_L = [v for v in world_verts if 0.025 <= v.x <= 0.045 and 1.51 <= v.z <= 1.535]
    orbit_verts_R = [v for v in world_verts if -0.045 <= v.x <= -0.025 and 1.51 <= v.z <= 1.535]
    if orbit_verts_L and orbit_verts_R:
        min_y_orbit_L = min(v.y for v in orbit_verts_L)
        min_y_orbit_R = min(v.y for v in orbit_verts_R)
        print(f"  Orbital socket L anterior Y: {min_y_orbit_L:.4f}m | R: {min_y_orbit_R:.4f}m")
        if most_anterior_face and (min_y_orbit_L <= nose_pos.y or min_y_orbit_R <= nose_pos.y):
            failures.append("Orbital sockets not recessed relative to nose tip!")
        else:
            recession_L = (min_y_orbit_L - nose_pos.y) * 1000
            recession_R = (min_y_orbit_R - nose_pos.y) * 1000
            print(f"  Orbital recession relative to nose: L={recession_L:.1f}mm, R={recession_R:.1f}mm (PASS)")
    else:
        warnings.append("Could not sample orbital socket vertices at expected coordinates.")

    # Mouth / Lips / Chin check
    lip_verts = [v for v in world_verts if abs(v.x) < 0.025 and 1.46 <= v.z <= 1.485]
    chin_verts = [v for v in world_verts if abs(v.x) < 0.020 and 1.43 <= v.z <= 1.455]
    if lip_verts and chin_verts:
        min_y_lip = min(v.y for v in lip_verts)
        min_y_chin = min(v.y for v in chin_verts)
        print(f"  Lip region anterior Y: {min_y_lip:.4f}m | Chin anterior Y: {min_y_chin:.4f}m")
    else:
        warnings.append("Could not sample lip or chin vertices.")

    # Vertex Groups Verification (29 standardized)
    print("\n--- Vertex Groups Verification ---")
    vgroups_dict = {vg.name: vg for vg in body_obj.vertex_groups}
    print(f"  Total Vertex Groups on Body: {len(vgroups_dict)}")

    missing_standard_vgroups = [g for g in STANDARDIZED_29_VGROUPS if g not in vgroups_dict]
    print(f"  Missing Standardized Groups ({len(missing_standard_vgroups)}): {missing_standard_vgroups}")
    if missing_standard_vgroups:
        failures.append(f"Body mesh is missing {len(missing_standard_vgroups)} standardized vertex groups: {missing_standard_vgroups}")

    empty_groups = []
    improperly_weighted_groups = []
    for g_name in STANDARDIZED_29_VGROUPS:
        if g_name in vgroups_dict:
            vg = vgroups_dict[g_name]
            g_idx = vg.index
            assigned_verts = []
            for i, v in enumerate(mesh.vertices):
                for g in v.groups:
                    if g.group == g_idx and g.weight > 0.0:
                        assigned_verts.append((i, g.weight))
            if len(assigned_verts) == 0:
                empty_groups.append(g_name)
            else:
                weights = [w for _, w in assigned_verts]
                min_w = min(weights)
                max_w = max(weights)
                if min_w < 0.0 or max_w > 1.0:
                    improperly_weighted_groups.append((g_name, min_w, max_w))

    print(f"  Empty Standardized Groups ({len(empty_groups)}): {empty_groups}")
    if empty_groups:
        failures.append(f"Standardized vertex groups are empty: {empty_groups}")
    if improperly_weighted_groups:
        failures.append(f"Vertex groups with invalid weights (outside [0, 1]): {improperly_weighted_groups}")

    # Check for orphan (unweighted) vertices across deformation DEF bone vertex groups
    def_vgroups = [vg.name for vg in body_obj.vertex_groups if vg.name.startswith("DEF-")]
    print(f"  Total DEF Bone Vertex Groups on Body: {len(def_vgroups)}")
    def_group_indices = {vgroups_dict[name].index for name in def_vgroups}

    unweighted_def_verts = []
    for i, v in enumerate(mesh.vertices):
        def_weight_sum = sum(g.weight for g in v.groups if g.group in def_group_indices)
        if def_weight_sum < 1e-4:
            unweighted_def_verts.append(i)

    print(f"  Vertices with 0 DEF weight (orphan from rig): {len(unweighted_def_verts)} / {n_verts}")
    if len(unweighted_def_verts) > 0:
        failures.append(f"{len(unweighted_def_verts)} vertices have 0 DEF bone weight (orphan vertices)!")

    bm.free()

    # =========================================================================
    # PART 2: 52 ARKit FACS BLENDSHAPE VERIFICATION
    # =========================================================================
    print("\n" + "-" * 40)
    print("PART 2: 52 ARKit FACS BLENDSHAPE VERIFICATION")
    print("-" * 40)

    sk = mesh.shape_keys
    if not sk:
        failures.append("Body mesh has NO shape keys block!")
        return failures

    basis_key = sk.key_blocks.get("Basis")
    if not basis_key:
        failures.append("Shape keys block has NO Basis key!")
        return failures
    print("  Basis key block: PRESENT")

    existing_shape_keys = [kb.name for kb in sk.key_blocks if kb.name != "Basis"]
    print(f"  Total non-basis shape keys: {len(existing_shape_keys)}")

    missing_arkit = [k for k in ARKIT_52_KEYS if k not in existing_shape_keys]
    print(f"  Missing ARKit keys ({len(missing_arkit)}): {missing_arkit}")
    if missing_arkit:
        failures.append(f"Missing {len(missing_arkit)} ARKit shape keys: {missing_arkit}")

    basis_coords = [v.co.copy() for v in basis_key.data]

    zero_delta_keys = []
    locality_violations = []
    key_stats = {}

    for k_name in ARKIT_52_KEYS:
        kb = sk.key_blocks.get(k_name)
        if not kb:
            continue

        max_disp = 0.0
        sum_disp = 0.0
        affected_verts = []

        for i, kb_v in enumerate(kb.data):
            disp_vec = kb_v.co - basis_coords[i]
            disp_len = disp_vec.length
            if disp_len > 1e-5:
                affected_verts.append((i, basis_coords[i], disp_vec))
                sum_disp += disp_len
                if disp_len > max_disp:
                    max_disp = disp_len

        n_affected = len(affected_verts)
        mean_disp = (sum_disp / n_affected) if n_affected > 0 else 0.0
        key_stats[k_name] = {
            "count": n_affected,
            "max": max_disp,
            "mean": mean_disp
        }

        if max_disp < 1e-5 or n_affected == 0:
            zero_delta_keys.append(k_name)
            continue

        # Locality Check: No facial shape key should affect vertices below neck (Z < 1.35m)
        below_neck_affected = [v for v in affected_verts if v[1].z < 1.35]
        if len(below_neck_affected) > 0:
            locality_violations.append((k_name, len(below_neck_affected), min(v[1].z for v in below_neck_affected)))

    print(f"  Zero-delta Shape Keys ({len(zero_delta_keys)}): {zero_delta_keys}")
    if zero_delta_keys:
        failures.append(f"{len(zero_delta_keys)} ARKit shape keys have zero displacement deltas: {zero_delta_keys}")

    print(f"  Facial Shape Keys with Locality Violations (Z < 1.35m) ({len(locality_violations)}): {locality_violations}")
    if locality_violations:
        failures.append(f"Locality violations: facial shape keys displacing body below neck: {locality_violations}")

    # Specific Asymmetry and Anatomical Direction Checks
    print("\n--- Specific Blendshape Realism & Locality Checks ---")
    # 1. eyeBlinkLeft vs eyeBlinkRight
    blink_L_kb = sk.key_blocks.get("eyeBlinkLeft")
    blink_R_kb = sk.key_blocks.get("eyeBlinkRight")
    if blink_L_kb and blink_R_kb:
        disp_L = [(basis_coords[i], kb_v.co - basis_coords[i]) for i, kb_v in enumerate(blink_L_kb.data) if (kb_v.co - basis_coords[i]).length > 1e-4]
        disp_R = [(basis_coords[i], kb_v.co - basis_coords[i]) for i, kb_v in enumerate(blink_R_kb.data) if (kb_v.co - basis_coords[i]).length > 1e-4]

        L_on_L_side = sum(1 for p, d in disp_L if p.x > 0.0)
        L_on_R_side = sum(1 for p, d in disp_L if p.x < 0.0)
        R_on_R_side = sum(1 for p, d in disp_R if p.x < 0.0)
        R_on_L_side = sum(1 for p, d in disp_R if p.x > 0.0)

        print(f"  eyeBlinkLeft: {len(disp_L)} verts affected (L-side +X: {L_on_L_side}, R-side -X: {L_on_R_side})")
        print(f"  eyeBlinkRight: {len(disp_R)} verts affected (R-side -X: {R_on_R_side}, L-side +X: {R_on_L_side})")

        if L_on_R_side > 0.1 * len(disp_L):
            failures.append(f"eyeBlinkLeft affects {L_on_R_side} right-side vertices (crosstalk)!")
        if R_on_L_side > 0.1 * len(disp_R):
            failures.append(f"eyeBlinkRight affects {R_on_L_side} left-side vertices (crosstalk)!")

        avg_dz_L = sum(d.z for _, d in disp_L) / len(disp_L) if disp_L else 0
        avg_dz_R = sum(d.z for _, d in disp_R) / len(disp_R) if disp_R else 0
        print(f"  eyeBlinkLeft mean dz: {avg_dz_L*1000:.3f} mm | eyeBlinkRight mean dz: {avg_dz_R*1000:.3f} mm")
        if avg_dz_L >= 0 or avg_dz_R >= 0:
            failures.append(f"eyeBlink does not displace downward (avg dz L={avg_dz_L}, R={avg_dz_R})!")

    # 2. jawOpen
    jaw_kb = sk.key_blocks.get("jawOpen")
    if jaw_kb:
        jaw_disp = [(basis_coords[i], kb_v.co - basis_coords[i]) for i, kb_v in enumerate(jaw_kb.data) if (kb_v.co - basis_coords[i]).length > 1e-4]
        avg_jaw_dz = sum(d.z for _, d in jaw_disp) / len(jaw_disp) if jaw_disp else 0
        min_jaw_dz = min(d.z for _, d in jaw_disp) if jaw_disp else 0
        print(f"  jawOpen: {len(jaw_disp)} verts affected, avg dz: {avg_jaw_dz*1000:.2f} mm, min dz: {min_jaw_dz*1000:.2f} mm")
        if min_jaw_dz >= 0:
            failures.append("jawOpen does not displace jaw downward (-Z)!")
        jaw_above_eyes = [p for p, _ in jaw_disp if p.z > 1.53]
        if len(jaw_above_eyes) > 0:
            failures.append(f"jawOpen affects {len(jaw_above_eyes)} vertices above eye level!")

    # 3. mouthSmileLeft and mouthSmileRight
    smile_L_kb = sk.key_blocks.get("mouthSmileLeft")
    smile_R_kb = sk.key_blocks.get("mouthSmileRight")
    if smile_L_kb and smile_R_kb:
        disp_smile_L = [(basis_coords[i], kb_v.co - basis_coords[i]) for i, kb_v in enumerate(smile_L_kb.data) if (kb_v.co - basis_coords[i]).length > 1e-4]
        disp_smile_R = [(basis_coords[i], kb_v.co - basis_coords[i]) for i, kb_v in enumerate(smile_R_kb.data) if (kb_v.co - basis_coords[i]).length > 1e-4]
        avg_smile_dz_L = sum(d.z for _, d in disp_smile_L) / len(disp_smile_L) if disp_smile_L else 0
        avg_smile_dz_R = sum(d.z for _, d in disp_smile_R) / len(disp_smile_R) if disp_smile_R else 0
        print(f"  mouthSmileLeft: {len(disp_smile_L)} verts, avg dz: {avg_smile_dz_L*1000:+.2f} mm (upward: {avg_smile_dz_L > 0})")
        print(f"  mouthSmileRight: {len(disp_smile_R)} verts, avg dz: {avg_smile_dz_R*1000:+.2f} mm (upward: {avg_smile_dz_R > 0})")
        if avg_smile_dz_L <= 0 or avg_smile_dz_R <= 0:
            failures.append("mouthSmile does not lift mouth corners upward (+Z)!")

    # Sample statistics across key categories
    print("\n  Sample ARKit Shape Key Displacements:")
    sample_keys = ["eyeBlinkLeft", "jawOpen", "mouthSmileLeft", "browDownLeft", "cheekPuff", "tongueOut"]
    for sk_name in sample_keys:
        if sk_name in key_stats:
            st = key_stats[sk_name]
            print(f"    {sk_name:18}: verts={st['count']:3d}, max_delta={st['max']*1000:6.2f} mm, mean_delta={st['mean']*1000:6.2f} mm")

    # =========================================================================
    # PART 3: STRING ANCHOR SNAPPING VERIFICATION
    # =========================================================================
    print("\n" + "-" * 40)
    print("PART 3: STRING ANCHOR SNAPPING VERIFICATION (< 2.0 mm)")
    print("-" * 40)

    arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
    strings_obj = bpy.data.objects.get("Prop_Marionette_Strings")

    if not arm_obj:
        failures.append("Armature 'Armature_Yu_Nian_An_Rigify' missing!")
        return failures
    if not strings_obj:
        failures.append("Props object 'Prop_Marionette_Strings' missing!")
        return failures

    missing_def_bones = [b for b in FINGER_DEF_BONES if b not in arm_obj.data.bones]
    if missing_def_bones:
        failures.append(f"Missing finger DEF bones in armature: {missing_def_bones}")

    n_string_verts = len(strings_obj.data.vertices)
    print(f"  Total Vertices in Prop_Marionette_Strings: {n_string_verts}")
    verts_per_string = n_string_verts // 10
    print(f"  Vertices per String Cord: {verts_per_string}")

    max_snapping_gap = 0.0
    gaps_mm = []

    for i, bone_name in enumerate(FINGER_DEF_BONES):
        bone = arm_obj.data.bones.get(bone_name)
        if not bone:
            continue
        bone_tail_world = arm_obj.matrix_world @ bone.tail_local
        root_vert_idx = i * verts_per_string
        string_root_world = strings_obj.matrix_world @ strings_obj.data.vertices[root_vert_idx].co

        gap_m = (string_root_world - bone_tail_world).length
        gap_mm = gap_m * 1000.0
        gaps_mm.append((bone_name, gap_mm, bone_tail_world, string_root_world))

        if gap_mm > max_snapping_gap:
            max_snapping_gap = gap_mm

        print(f"  String #{i:02d} -> {bone_name:16}: gap = {gap_mm:7.4f} mm | root=({string_root_world.x:+.3f}, {string_root_world.y:+.3f}, {string_root_world.z:+.3f})")

        if gap_mm >= 2.0:
            failures.append(f"String #{i} gap {gap_mm:.3f} mm >= 2.0 mm limit from {bone_name} tail!")

    print(f"\n  Maximum String-to-Bone Snapping Gap: {max_snapping_gap:.4f} mm")
    if max_snapping_gap < 2.0:
        print(f"  STRING SNAPPING VERIFICATION: PASS (Max gap {max_snapping_gap:.4f} mm < 2.0 mm)")
    else:
        print(f"  STRING SNAPPING VERIFICATION: FAIL (Max gap {max_snapping_gap:.4f} mm >= 2.0 mm)")

    # =========================================================================
    # PART 4: SUMMARY & EMPIRICAL VERDICT
    # =========================================================================
    print("\n" + "=" * 80)
    print("EMPIRICAL CHALLENGER VERDICT & SUMMARY")
    print("=" * 80)

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  [WARN] {w}")

    if failures:
        print(f"\nCRITICAL DEFECTS FOUND ({len(failures)}):")
        for f in failures:
            print(f"  [FAIL] {f}")
        print("\nOVERALL EMPIRICAL VERDICT: CHALLENGE")
        sys.exit(2)
    else:
        print("\nALL ADVERSARIAL CHALLENGES CONFIRMED ROBUST!")
        print("OVERALL EMPIRICAL VERDICT: CONFIRM (ROBUST)")
        sys.exit(0)

def test_live_master_blend_adversarial_empirical_audit():
    """Pytest wrapper: executes this audit script inside Blender background mode."""
    blender_exe = Path("C:/Program Files/Blender Foundation/Blender 4.5/blender.exe")
    blend_file = Path("output/yu_nian_an/Yu_Nian_An_Master.blend")
    script_file = Path(__file__).resolve()

    if not blender_exe.exists() or not blend_file.exists():
        import pytest
        pytest.skip(f"Blender executable or blend file missing.")

    cmd = [
        str(blender_exe),
        "--background",
        str(blend_file),
        "--python",
        str(script_file)
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    print(proc.stdout)
    assert proc.returncode == 0, f"Blender empirical audit failed with code {proc.returncode}:\n{proc.stdout}"

if __name__ == "__main__":
    if bpy is not None:
        run_adversarial_challenge()
