"""
Independent Adversarial Verification Script
Run by m1_reviewer_it2_1
"""
import math
import sys
import os
import subprocess
from pathlib import Path

# Add project root to sys.path
project_dir = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline")
sys.path.insert(0, str(project_dir))

from anime_pipeline.mesh.generator import AnimeMeshGenerator, AnimeMeshConfig
from anime_pipeline.mesh.topology_cleaner import TopologyValidator, NormalHarmonizer, TopologyCleaner

def run_tests():
    print("=== STARTING INDEPENDENT ADVERSARIAL VERIFICATION ===")
    failures = []

    # -------------------------------------------------------------
    # 1. Seam Normal Harmonization Verification
    # -------------------------------------------------------------
    print("\n--- 1. Testing Seam Normal Harmonization ---")
    gen = AnimeMeshGenerator(AnimeMeshConfig())
    res = gen.generate()
    
    # Check that generator.py assigned normals to all submeshes
    for name, sm in res.submeshes.items():
        if not sm.normals or len(sm.normals) != len(sm.vertices):
            failures.append(f"Submesh {name} has invalid normals: {len(sm.normals) if sm.normals else 0} vs {len(sm.vertices)} vertices")
        else:
            # Check unit length of normals
            non_unit = 0
            for ni, n in enumerate(sm.normals):
                length = math.sqrt(n[0]**2 + n[1]**2 + n[2]**2)
                if abs(length - 1.0) > 1e-4:
                    non_unit += 1
            if non_unit > 0:
                failures.append(f"Submesh {name} has {non_unit} non-unit normals!")

    # Check coincident vertex normals between Head and Torso
    head = res.submeshes["Anime_Head"]
    torso = res.submeshes["Anime_Torso"]
    
    head_co = {i: head.vertices[i] for i in range(len(head.vertices))}
    torso_co = {i: torso.vertices[i] for i in range(len(torso.vertices))}
    
    coincident_neck = []
    for hi, hco in head_co.items():
        for ti, tco in torso_co.items():
            d2 = (hco[0]-tco[0])**2 + (hco[1]-tco[1])**2 + (hco[2]-tco[2])**2
            if d2 < 1e-8:
                hn = head.normals[hi]
                tn = torso.normals[ti]
                dot = max(-1.0, min(1.0, hn[0]*tn[0] + hn[1]*tn[1] + hn[2]*tn[2]))
                ang = math.acos(dot)
                coincident_neck.append((hi, ti, ang, hn, tn))
    
    print(f"Coincident neck vertices found: {len(coincident_neck)}")
    if len(coincident_neck) != 46:
        failures.append(f"Expected 46 coincident neck vertices, found {len(coincident_neck)}")
    else:
        max_ang = max(c[2] for c in coincident_neck)
        avg_ang = sum(c[2] for c in coincident_neck) / len(coincident_neck)
        print(f"Generator Neck Seam Max Angular Deviation: {max_ang:.8f} rad, Avg: {avg_ang:.8f} rad")
        if max_ang > 1e-6:
            failures.append(f"Generator neck seam normals not identical! Max dev: {max_ang}")

    # Check Torso <-> Arms and Torso <-> Legs coincident normals
    arms = res.submeshes["Anime_Arms"]
    coincident_arms = []
    for ti, tco in torso_co.items():
        for ai, aco in enumerate(arms.vertices):
            d2 = (tco[0]-aco[0])**2 + (tco[1]-aco[1])**2 + (tco[2]-aco[2])**2
            if d2 < 1e-8:
                tn = torso.normals[ti]
                an = arms.normals[ai]
                dot = max(-1.0, min(1.0, tn[0]*an[0] + tn[1]*an[1] + tn[2]*an[2]))
                ang = math.acos(dot)
                coincident_arms.append((ti, ai, ang))
    print(f"Coincident Torso-Arms vertices found: {len(coincident_arms)}")
    if len(coincident_arms) != 92:
        failures.append(f"Expected 92 coincident shoulder vertices, found {len(coincident_arms)}")
    else:
        max_arm_dev = max(c[2] for c in coincident_arms)
        print(f"Generator Shoulder Seam Max Angular Deviation: {max_arm_dev:.8f} rad")
        if max_arm_dev > 1e-6:
            failures.append(f"Generator shoulder seam normals not identical! Max dev: {max_arm_dev}")

    legs = res.submeshes["Anime_Legs"]
    coincident_legs = []
    for ti, tco in torso_co.items():
        for li, lco in enumerate(legs.vertices):
            d2 = (tco[0]-lco[0])**2 + (tco[1]-lco[1])**2 + (tco[2]-lco[2])**2
            if d2 < 1e-8:
                tn = torso.normals[ti]
                ln = legs.normals[li]
                dot = max(-1.0, min(1.0, tn[0]*ln[0] + tn[1]*ln[1] + tn[2]*ln[2]))
                ang = math.acos(dot)
                coincident_legs.append((ti, li, ang))
    print(f"Coincident Torso-Legs vertices found: {len(coincident_legs)}")
    if len(coincident_legs) != 50:
        failures.append(f"Expected 50 coincident hip vertices, found {len(coincident_legs)}")
    else:
        max_leg_dev = max(c[2] for c in coincident_legs)
        print(f"Generator Hip Seam Max Angular Deviation: {max_leg_dev:.8f} rad")
        if max_leg_dev > 1e-6:
            failures.append(f"Generator hip seam normals not identical! Max dev: {max_leg_dev}")

    # -------------------------------------------------------------
    # 2. Skirt Clearance Invariant (Point-to-Surface Distance)
    # -------------------------------------------------------------
    print("\n--- 2. Testing Skirt Clearance Invariant (>= 15.0mm) ---")
    def pt_tri_dist(p, a, b, c):
        # Implementation of point-to-triangle distance
        v0 = (b[0]-a[0], b[1]-a[1], b[2]-a[2])
        v1 = (c[0]-a[0], c[1]-a[1], c[2]-a[2])
        n = (v0[1]*v1[2]-v0[2]*v1[1], v0[2]*v1[0]-v0[0]*v1[2], v0[0]*v1[1]-v0[1]*v1[0])
        n_len = math.sqrt(n[0]**2 + n[1]**2 + n[2]**2)
        if n_len < 1e-12:
            return 1e9
        un = (n[0]/n_len, n[1]/n_len, n[2]/n_len)
        ap = (p[0]-a[0], p[1]-a[1], p[2]-a[2])
        dist_plane = ap[0]*un[0] + ap[1]*un[1] + ap[2]*un[2]
        proj = (p[0] - dist_plane*un[0], p[1] - dist_plane*un[1], p[2] - dist_plane*un[2])
        
        # Barycentric coordinates check
        v2 = (proj[0]-a[0], proj[1]-a[1], proj[2]-a[2])
        d00 = v0[0]*v0[0]+v0[1]*v0[1]+v0[2]*v0[2]
        d01 = v0[0]*v1[0]+v0[1]*v1[1]+v0[2]*v1[2]
        d11 = v1[0]*v1[0]+v1[1]*v1[1]+v1[2]*v1[2]
        d20 = v2[0]*v0[0]+v2[1]*v0[1]+v2[2]*v0[2]
        d21 = v2[0]*v1[0]+v2[1]*v1[1]+v2[2]*v1[2]
        denom = d00 * d11 - d01 * d01
        if abs(denom) < 1e-12:
            return 1e9
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w
        if u >= -1e-6 and v >= -1e-6 and w >= -1e-6:
            return abs(dist_plane)
        
        # Edge distances
        def pt_seg(p, a, b):
            ab = (b[0]-a[0], b[1]-a[1], b[2]-a[2])
            ap = (p[0]-a[0], p[1]-a[1], p[2]-a[2])
            ab2 = ab[0]**2 + ab[1]**2 + ab[2]**2
            if ab2 < 1e-12:
                return math.sqrt(ap[0]**2 + ap[1]**2 + ap[2]**2)
            t = max(0.0, min(1.0, (ap[0]*ab[0] + ap[1]*ab[1] + ap[2]*ab[2]) / ab2))
            pr = (a[0]+t*ab[0], a[1]+t*ab[1], a[2]+t*ab[2])
            return math.sqrt((p[0]-pr[0])**2 + (p[1]-pr[1])**2 + (p[2]-pr[2])**2)
        return min(pt_seg(p, a, b), pt_seg(p, b, c), pt_seg(p, c, a))

    def min_skirt_clearance(res_obj, girth_scale=1.0):
        skirt = res_obj.submeshes["Anime_Skirt"]
        legs = res_obj.submeshes["Anime_Legs"]
        torso = res_obj.submeshes["Anime_Torso"]
        z_min = min(v[2] for v in skirt.vertices)
        z_max = max(v[2] for v in skirt.vertices)
        
        body_verts = []
        for v in legs.vertices:
            if z_min <= v[2] <= z_max:
                cx = 0.088 if v[0] > 0 else -0.088
                cy = -0.020
                sx = cx + (v[0] - cx) * girth_scale
                sy = cy + (v[1] - cy) * girth_scale
                body_verts.append((sx, sy, v[2]))
        for v in torso.vertices:
            if z_min <= v[2] <= z_max:
                body_verts.append(v)
        
        min_d = 1e9
        for bv in body_verts:
            for q in skirt.quads:
                d1 = pt_tri_dist(bv, skirt.vertices[q[0]], skirt.vertices[q[1]], skirt.vertices[q[2]])
                d2 = pt_tri_dist(bv, skirt.vertices[q[0]], skirt.vertices[q[2]], skirt.vertices[q[3]])
                min_d = min(min_d, d1, d2)
        return min_d * 1000.0

    c_nom = min_skirt_clearance(res, 1.0)
    print(f"Nominal Skirt Clearance: {c_nom:.2f} mm")
    if c_nom < 15.0:
        failures.append(f"Nominal skirt clearance {c_nom:.2f}mm is less than required 15.0mm")
    
    for gscale in [1.05, 1.10, 1.15]:
        c_girth = min_skirt_clearance(res, gscale)
        print(f"Skirt Clearance under +{(gscale-1.0)*100:.0f}% thigh girth: {c_girth:.2f} mm")
        if c_girth < 15.0:
            failures.append(f"Skirt clearance {c_girth:.2f}mm under girth {gscale} is less than 15.0mm")

    # Also test across heights: 1.45m, 1.65m, 1.75m
    for h in [1.45, 1.75]:
        res_h = AnimeMeshGenerator(AnimeMeshConfig(height=h)).generate()
        c_h = min_skirt_clearance(res_h, 1.0)
        print(f"Skirt Clearance at height {h}m: {c_h:.2f} mm")
        if c_h < 15.0 * (h / 1.65):
            failures.append(f"Skirt clearance {c_h:.2f}mm at height {h}m is below threshold")

    # -------------------------------------------------------------
    # 3. Shoe Alignment & Grounding
    # -------------------------------------------------------------
    print("\n--- 3. Testing Shoe Alignment & Grounding ---")
    shoes = res.submeshes["Anime_Shoes"]
    l_foot_verts = [v for v in legs.vertices if v[0] > 0 and v[2] < 0.08]
    r_foot_verts = [v for v in legs.vertices if v[0] < 0 and v[2] < 0.08]
    l_shoe_verts = [v for v in shoes.vertices if v[0] > 0]
    r_shoe_verts = [v for v in shoes.vertices if v[0] < 0]

    foot_l_cx = sum(v[0] for v in l_foot_verts) / len(l_foot_verts)
    foot_l_cy = sum(v[1] for v in l_foot_verts) / len(l_foot_verts)
    shoe_l_cx = sum(v[0] for v in l_shoe_verts) / len(l_shoe_verts)
    shoe_l_cy = sum(v[1] for v in l_shoe_verts) / len(l_shoe_verts)

    disp_l = math.hypot(foot_l_cx - shoe_l_cx, foot_l_cy - shoe_l_cy) * 1000.0
    print(f"Left Shoe-to-Foot Center Displacement: {disp_l:.4f} mm")
    if disp_l > 30.0:
        failures.append(f"Left shoe displacement {disp_l:.2f}mm exceeds 30mm!")

    foot_r_cx = sum(v[0] for v in r_foot_verts) / len(r_foot_verts)
    foot_r_cy = sum(v[1] for v in r_foot_verts) / len(r_foot_verts)
    shoe_r_cx = sum(v[0] for v in r_shoe_verts) / len(r_shoe_verts)
    shoe_r_cy = sum(v[1] for v in r_shoe_verts) / len(r_shoe_verts)

    disp_r = math.hypot(foot_r_cx - shoe_r_cx, foot_r_cy - shoe_r_cy) * 1000.0
    print(f"Right Shoe-to-Foot Center Displacement: {disp_r:.4f} mm")
    if disp_r > 30.0:
        failures.append(f"Right shoe displacement {disp_r:.2f}mm exceeds 30mm!")

    # Test Sole Grounding with offsets: 0.0, 0.05, -0.02
    for gz in [0.0, 0.05, -0.02]:
        res_gz = AnimeMeshGenerator(AnimeMeshConfig(ground_sole_z=gz)).generate()
        s_min_z = min(v[2] for v in res_gz.submeshes["Anime_Shoes"].vertices)
        l_min_z = min(v[2] for v in res_gz.submeshes["Anime_Legs"].vertices)
        print(f"Sole grounding check gz={gz}: Shoes min Z={s_min_z:.5f}, Legs min Z={l_min_z:.5f}")
        if abs(s_min_z - gz) > 1e-4:
            failures.append(f"Shoes sole Z {s_min_z} does not match ground_sole_z {gz}")
        if abs(l_min_z - gz) > 1e-4:
            failures.append(f"Legs sole Z {l_min_z} does not match ground_sole_z {gz}")

    # -------------------------------------------------------------
    # 4. Quad Face Deduplication in merge_duplicate_vertices
    # -------------------------------------------------------------
    print("\n--- 4. Testing Quad Face Deduplication ---")
    test_verts = [
        (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0), # Quad 0
        (0.0, 0.0, 0.0), # duplicate of 0 (vert 4)
        (1.0, 0.0, 0.0), # duplicate of 1 (vert 5)
        (1.0, 1.0, 0.0), # duplicate of 2 (vert 6)
        (0.0, 1.0, 0.0), # duplicate of 3 (vert 7)
    ]
    # Quads with duplicate vertices that resolve to identical canonical quads
    test_quads = [
        (0, 1, 2, 3), # original
        (4, 5, 6, 7), # duplicate via duplicate vertices
        (1, 2, 3, 0), # cyclic permutation
        (3, 2, 1, 0), # reversed order (same 4 vertices)
        (0, 1, 4, 2), # collapses to triangle/degenerate because 0 and 4 are duplicate!
    ]
    merged_v, merged_q = TopologyCleaner.merge_duplicate_vertices(test_verts, test_quads, epsilon=1e-4)
    print(f"Initial: {len(test_verts)} verts, {len(test_quads)} quads. Merged: {len(merged_v)} verts, {len(merged_q)} quads.")
    if len(merged_v) != 4:
        failures.append(f"merge_duplicate_vertices failed: expected 4 unique vertices, got {len(merged_v)}")
    if len(merged_q) != 1:
        failures.append(f"merge_duplicate_vertices deduplication failed: expected 1 unique quad, got {len(merged_q)}: {merged_q}")

    # -------------------------------------------------------------
    # 5. TopologyValidator NaN/Inf Float Handling
    # -------------------------------------------------------------
    print("\n--- 5. Testing TopologyValidator NaN/Inf Handling ---")
    nan_tests = [
        [(float("nan"), 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)],
        [(0.0, float("nan"), 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)],
        [(0.0, 0.0, float("nan")), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)],
        [(float("inf"), 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)],
        [(0.0, float("-inf"), 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)],
        [(float("nan"), float("inf"), float("-inf")), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)],
    ]
    for idx, nv in enumerate(nan_tests):
        try:
            rep = TopologyValidator.audit_mesh(nv, [(0, 1, 2, 3)])
            if rep.is_valid:
                failures.append(f"NaN/Inf test {idx} returned is_valid=True, should be False!")
        except Exception as e:
            failures.append(f"NaN/Inf test {idx} raised unexpected exception: {type(e).__name__}: {e}")

    # Test detect_duplicates directly with NaN/Inf
    try:
        dups = TopologyValidator.detect_duplicates([(float("nan"), 0.0, 0.0), (float("inf"), 0.0, 0.0)], 1e-5)
        print(f"detect_duplicates on NaN/Inf returned {len(dups)} dups without crashing.")
    except Exception as e:
        failures.append(f"detect_duplicates crashed on NaN/Inf: {type(e).__name__}: {e}")

    # -------------------------------------------------------------
    # 6. Blender Direct Verification of output/ assets
    # -------------------------------------------------------------
    print("\n--- 6. Testing output/ Files in Blender ---")
    blender_exe = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
    blend_file = project_dir / "output" / "anime_mesh_clean.blend"
    glb_file = project_dir / "output" / "anime_mesh_clean.glb"
    
    if not blend_file.exists():
        failures.append(f"{blend_file} does not exist!")
    if not glb_file.exists():
        failures.append(f"{glb_file} does not exist!")

    if blend_file.exists():
        bl_script = f"""
import bpy, math
head = bpy.data.objects.get('Anime_Head')
torso = bpy.data.objects.get('Anime_Torso')
assert head is not None, 'Anime_Head not found'
assert torso is not None, 'Anime_Torso not found'

head_verts = {{i: (head.matrix_world @ v.co, (head.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(head.data.vertices)}}
torso_verts = {{i: (torso.matrix_world @ v.co, (torso.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(torso.data.vertices)}}

coincident = []
for hi, (hco, hno) in head_verts.items():
    for ti, (tco, tno) in torso_verts.items():
        if (hco - tco).length < 1e-4:
            dot = max(-1.0, min(1.0, hno.dot(tno)))
            coincident.append(math.acos(dot))

print(f"BLENDER_COINCIDENT_COUNT: {{len(coincident)}}")
max_ang = max(coincident) if coincident else 999.0
avg_ang = sum(coincident)/len(coincident) if coincident else 999.0
print(f"BLENDER_MAX_DEV: {{max_ang:.6f}} rad")
print(f"BLENDER_AVG_DEV: {{avg_ang:.6f}} rad")
assert len(coincident) == 46, f"Expected 46 coincident verts, got {{len(coincident)}}"
assert max_ang < 0.005, f"Max deviation {{max_ang}} exceeds 0.005 rad!"
"""
        cmd = [blender_exe, "--background", str(blend_file), "--python-expr", bl_script]
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
        print(r.stdout)
        if r.returncode != 0:
            failures.append(f"Blender .blend audit failed (code {r.returncode}):\n{r.stderr}\n{r.stdout}")

    if glb_file.exists():
        glb_script = f"""
import bpy, math
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"{str(glb_file)}")
objs = {{o.name: o for o in bpy.context.scene.objects if o.type == 'MESH'}}
head = objs.get('Anime_Head')
torso = objs.get('Anime_Torso')
assert head is not None and torso is not None, 'Head or Torso missing in GLB'

head_verts = {{i: (head.matrix_world @ v.co, (head.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(head.data.vertices)}}
torso_verts = {{i: (torso.matrix_world @ v.co, (torso.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(torso.data.vertices)}}

coincident = []
for hi, (hco, hno) in head_verts.items():
    for ti, (tco, tno) in torso_verts.items():
        if (hco - tco).length < 1e-4:
            dot = max(-1.0, min(1.0, hno.dot(tno)))
            coincident.append(math.acos(dot))

print(f"GLB_COINCIDENT_COUNT: {{len(coincident)}}")
max_ang = max(coincident) if coincident else 999.0
avg_ang = sum(coincident)/len(coincident) if coincident else 999.0
print(f"GLB_MAX_DEV: {{max_ang:.6f}} rad")
print(f"GLB_AVG_DEV: {{avg_ang:.6f}} rad")
assert len(coincident) == 46, f"Expected 46 coincident verts in GLB, got {{len(coincident)}}"
assert max_ang < 0.005, f"GLB Max deviation {{max_ang}} exceeds 0.005 rad!"
"""
        cmd = [blender_exe, "--background", "--python-expr", glb_script]
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
        print(r.stdout)
        if r.returncode != 0:
            failures.append(f"Blender .glb audit failed (code {r.returncode}):\n{r.stderr}\n{r.stdout}")

    # Summary
    print("\n=== VERIFICATION SUMMARY ===")
    if failures:
        print(f"FAILURES DETECTED ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return False
    else:
        print("ALL INDEPENDENT ADVERSARIAL CHECKS PASSED (0 failures)!")
        return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
