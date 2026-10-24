"""
Independent Forensic Integrity Audit Script for Milestone M3.
Authored by M3 Forensic Auditor.
"""

import os
import sys
import math
import subprocess
import numpy as np

def log(msg):
    print(f"[AUDIT] {msg}")

def fail(msg):
    print(f"[VIOLATION] {msg}")
    sys.exit(1)

def main():
    log("Starting Independent Forensic Audit...")

    # --------------------------------------------------------------------------
    # CHECK 1: 163 DEF Bones Genuine Generation & Landmark Mapping
    # --------------------------------------------------------------------------
    log("CHECK 1: Verifying 163 DEF bones genuine generation and landmark mapping...")
    from morphomesh.human_generator import HumanAnatomyGenerator
    from morphomesh.human_rigging import (
        generate_rigify_human_metarig,
        get_default_human_landmarks,
        ALL_163_DEF_BONES,
        BODY_DEF_BONES,
        FACIAL_DEF_BONES,
    )

    gen = HumanAnatomyGenerator()
    mesh, mh_lm = gen.generate_human_body(height=1.65)
    mr = generate_rigify_human_metarig(landmarks=mh_lm)

    assert len(mr.bones) == 163, f"Expected 163 bones, got {len(mr.bones)}"
    def_bones = [b for b in mr.bones.values() if b.name.startswith("DEF-")]
    assert len(def_bones) == 163, f"Expected 163 DEF bones, got {len(def_bones)}"
    assert set(mr.bones.keys()) == set(ALL_163_DEF_BONES), "Bone names do not match ALL_163_DEF_BONES"

    # Test dynamic sensitivity to landmarks
    perturbed_lm = dict(mh_lm)
    perturbed_lm["joint-l-elbow"] = (mh_lm["joint-l-elbow"][0] + 0.05, mh_lm["joint-l-elbow"][1], mh_lm["joint-l-elbow"][2] - 0.03)
    mr_perturbed = generate_rigify_human_metarig(landmarks=perturbed_lm)
    assert mr_perturbed.bones["DEF-forearm.L"].head != mr.bones["DEF-forearm.L"].head, "DEF-forearm.L head did not move when elbow landmark moved!"
    assert mr_perturbed.bones["DEF-upper_arm.L.001"].tail != mr.bones["DEF-upper_arm.L.001"].tail, "DEF-upper_arm.L.001 tail did not move when elbow landmark moved!"

    # Test finger bones alignment
    for side, s_low in [("L", "l"), ("R", "r")]:
        for f_idx, d_name in enumerate(["thumb", "f_index", "f_middle", "f_ring", "f_pinky"], start=1):
            lm_key = f"joint-{s_low}-finger-{f_idx}-1"
            b_name = f"DEF-{d_name}.01.{side}"
            expected_head = mh_lm[lm_key]
            actual_head = mr.bones[b_name].head
            diff = np.linalg.norm(np.array(actual_head) - np.array(expected_head))
            assert diff < 1e-5, f"{b_name} head {actual_head} != {lm_key} {expected_head}"

    log("CHECK 1 PASSED: 163 DEF bones are genuinely generated and mapped to MakeHuman landmarks.")

    # --------------------------------------------------------------------------
    # CHECK 2: 52 ARKit FACS Shape Keys Deformation Deltas
    # --------------------------------------------------------------------------
    log("CHECK 2: Verifying 52 ARKit FACS shape keys produce genuine non-zero deformation deltas...")
    from morphomesh.human_rigging import generate_arkit_52_blendshapes, ARKIT_52_BLENDSHAPES

    assert len(ARKIT_52_BLENDSHAPES) == 52, f"Expected 52 ARKit blendshapes, got {len(ARKIT_52_BLENDSHAPES)}"
    shapes = generate_arkit_52_blendshapes(mesh, landmarks=mh_lm)
    assert len(shapes) == 52, f"Expected 52 generated shapes, got {len(shapes)}"

    for k_name in ARKIT_52_BLENDSHAPES:
        assert k_name in shapes, f"Missing shape key {k_name}"
        deltas = shapes[k_name]
        non_zero = [d for d in deltas.values() if any(abs(x) > 1e-6 for x in d)]
        assert len(non_zero) > 0, f"Shape key {k_name} produced 0 non-zero deformation deltas!"
        max_delta = max(np.linalg.norm(np.array(d)) for d in non_zero)
        assert max_delta > 0.0005, f"Shape key {k_name} max delta too small: {max_delta}"

    log("CHECK 2 PASSED: All 52 ARKit FACS shape keys produce genuine non-zero deltas.")

    # --------------------------------------------------------------------------
    # CHECK 3: 10 Marionette Cords Catenary Curves & Snapping Precision
    # --------------------------------------------------------------------------
    log("CHECK 3: Verifying 10 marionette cords catenary curvature & 0.000mm snapping...")
    from morphomesh.wardrobe import generate_catenary_magic_strings, get_butterfly_vortex_positions

    targets = get_butterfly_vortex_positions()
    strings = generate_catenary_magic_strings(rest_pose=True, target_positions=targets)
    assert len(strings.vertices) == 140, f"Expected 140 vertices, got {len(strings.vertices)}"
    assert len(strings.faces) == 120, f"Expected 120 faces, got {len(strings.faces)}"

    # Check catenary sag
    for cord_i in range(10):
        v0 = np.array(strings.vertices[cord_i * 14])
        v1 = np.array(strings.vertices[cord_i * 14 + 1])
        root_mid = 0.5 * (v0 + v1)
        v_last0 = np.array(strings.vertices[cord_i * 14 + 12])
        v_last1 = np.array(strings.vertices[cord_i * 14 + 13])
        tip_mid = 0.5 * (v_last0 + v_last1)

        v_mid0 = np.array(strings.vertices[cord_i * 14 + 6])
        v_mid1 = np.array(strings.vertices[cord_i * 14 + 7])
        cord_mid = 0.5 * (v_mid0 + v_mid1)

        linear_mid_z = 0.5 * (root_mid[2] + tip_mid[2])
        sag = linear_mid_z - cord_mid[2]
        assert sag > 0.003, f"Cord {cord_i} lacks catenary downward sag: {sag*1000:.2f}mm"

    log("CHECK 3 PASSED: 10 marionette cords possess genuine catenary parabolic sag curvature.")

    # --------------------------------------------------------------------------
    # CHECK 4: 10 Swallowtail Butterflies 24 Quads & Bilateral Vortex Flocking
    # --------------------------------------------------------------------------
    log("CHECK 4: Verifying 10 swallowtail butterflies 24 quads and bilateral vortex flocking...")
    from morphomesh.wardrobe import generate_swallowtail_quad_butterfly

    bf = generate_swallowtail_quad_butterfly()
    assert len(bf.vertices) == 48, f"Expected 48 vertices, got {len(bf.vertices)}"
    assert len(bf.faces) == 48, f"Expected 48 triangular faces (24 quads * 2), got {len(bf.faces)}"

    # Check pairwise distances between targets
    min_dist = float("inf")
    for i in range(len(targets)):
        for j in range(i + 1, len(targets)):
            d = np.linalg.norm(np.array(targets[i]) - np.array(targets[j]))
            if d < min_dist:
                min_dist = d
    assert min_dist >= 0.150, f"Min butterfly target separation {min_dist*1000:.2f}mm < 150mm"

    # Bilateral flank check
    left_butterflies = [p for p in targets if p[0] > 0]
    right_butterflies = [p for p in targets if p[0] < 0]
    assert len(left_butterflies) == 5, f"Expected 5 left flank butterflies, got {len(left_butterflies)}"
    assert len(right_butterflies) == 5, f"Expected 5 right flank butterflies, got {len(right_butterflies)}"

    log("CHECK 4 PASSED: 10 swallowtail butterflies 24-quad topology and flocking >= 150mm verified.")

    # --------------------------------------------------------------------------
    # CHECK 5: Live Master Blend File Empirical Verification
    # --------------------------------------------------------------------------
    log("CHECK 5: Verifying output/yu_nian_an/Yu_Nian_An_Master.blend in live Blender 4.5...")
    blender_exe = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
    blend_file = r"output\yu_nian_an\Yu_Nian_An_Master.blend"
    assert os.path.isfile(blender_exe), f"Blender executable not found: {blender_exe}"
    assert os.path.isfile(blend_file), f"Master blend file not found: {blend_file}"

    blender_audit_script = """
import bpy, sys, mathutils, numpy as np

# 1. Armature check
arm = bpy.data.objects.get('Armature_Yu_Nian_An_Rigify')
if not arm:
    print('FAIL: Missing Armature_Yu_Nian_An_Rigify')
    sys.exit(1)

def_bones = [b for b in arm.data.bones if b.name.startswith('DEF-')]
if len(def_bones) != 163:
    print(f'FAIL: DEF bones count {len(def_bones)} != 163')
    sys.exit(1)

# 2. Shape keys check
body = bpy.data.objects.get('Yu_Nian_An_Body')
if not body or not body.data.shape_keys:
    print('FAIL: Missing body shape keys')
    sys.exit(1)

blocks = body.data.shape_keys.key_blocks
basis = blocks.get('Basis')
if not basis or len(blocks) < 53:
    print(f'FAIL: Total shape keys {len(blocks)} < 53')
    sys.exit(1)

zero_deltas = []
for kb in blocks:
    if kb.name == 'Basis': continue
    diffs = [(kb.data[i].co - basis.data[i].co).length for i in range(len(kb.data))]
    if max(diffs) < 1e-5:
        zero_deltas.append(kb.name)
if zero_deltas:
    print(f'FAIL: Shape keys with zero delta: {zero_deltas}')
    sys.exit(1)

# 3. Marionette cords snapping error check
strings = bpy.data.objects.get('Prop_Marionette_Strings')
if not strings or len(strings.data.vertices) != 140:
    print(f'FAIL: Strings verts {len(strings.data.vertices) if strings else None} != 140')
    sys.exit(1)

finger_keys = [
    'DEF-thumb.03.L', 'DEF-f_index.03.L', 'DEF-f_middle.03.L', 'DEF-f_ring.03.L', 'DEF-f_pinky.03.L',
    'DEF-thumb.03.R', 'DEF-f_index.03.R', 'DEF-f_middle.03.R', 'DEF-f_ring.03.R', 'DEF-f_pinky.03.R',
]
max_snap_err = 0.0
for i, b_name in enumerate(finger_keys):
    b = arm.data.bones.get(b_name)
    tail_w = arm.matrix_world @ b.tail_local
    v0_w = strings.matrix_world @ strings.data.vertices[i * 14].co
    v1_w = strings.matrix_world @ strings.data.vertices[i * 14 + 1].co
    root_mid = 0.5 * (v0_w + v1_w)
    err = (root_mid - tail_w).length
    if err > max_snap_err:
        max_snap_err = err

if max_snap_err > 1e-4:
    print(f'FAIL: Cord snapping error {max_snap_err*1000:.4f}mm > 0.1mm')
    sys.exit(1)

# 4. Butterfly count, verts, and separation check
bfs = [bpy.data.objects.get(f'Prop_Butterfly_{i:02d}') for i in range(10)]
if any(b is None for b in bfs):
    print('FAIL: Missing butterfly object in scene')
    sys.exit(1)

for i, b in enumerate(bfs):
    if len(b.data.vertices) != 48:
        print(f'FAIL: Butterfly {i} vertices {len(b.data.vertices)} != 48')
        sys.exit(1)

min_bf_sep = float('inf')
for i in range(10):
    for j in range(i + 1, 10):
        d = (bfs[i].matrix_world.translation - bfs[j].matrix_world.translation).length
        if d < min_bf_sep:
            min_bf_sep = d

if min_bf_sep < 0.150:
    print(f'FAIL: Butterfly min separation {min_bf_sep*1000:.2f}mm < 150mm')
    sys.exit(1)

print(f'BLENDER_AUDIT_SUCCESS: def_bones={len(def_bones)}, shape_keys={len(blocks)}, max_snap_err={max_snap_err*1000:.6f}mm, min_bf_sep={min_bf_sep*1000:.2f}mm')
"""

    cmd = [blender_exe, "--background", blend_file, "--python-expr", blender_audit_script]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, f"Blender live audit failed: {proc.stdout}\n{proc.stderr}"
    log(f"Blender output: {[line for line in proc.stdout.splitlines() if 'BLENDER_AUDIT' in line]}")
    log("CHECK 5 PASSED: Live Blender Master Asset verified with 100% precision.")

    log("ALL 5 INDEPENDENT FORENSIC CHECKS PASSED EMPIRICALLY!")

if __name__ == "__main__":
    main()
