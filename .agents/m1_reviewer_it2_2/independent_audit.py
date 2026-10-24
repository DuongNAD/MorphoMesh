"""
independent_audit.py
Independent verification script by m1_reviewer_it2_2
"""

import math
import os
import sys
import subprocess
from pathlib import Path

# Add project directory to sys.path
proj_dir = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline")
sys.path.insert(0, str(proj_dir))

from anime_pipeline.mesh.generator import AnimeMeshGenerator, AnimeMeshConfig
from anime_pipeline.mesh.topology_cleaner import TopologyValidator, NormalHarmonizer

def audit_memory_generation():
    print("=== 1. AUDIT GENERATOR IN-MEMORY ===")
    gen = AnimeMeshGenerator()
    res = gen.generate()
    
    total_verts = 0
    total_quads = 0
    total_tris = 0
    total_ngons = 0
    
    sub_stats = {}
    for name, sm in res.submeshes.items():
        rep = TopologyValidator.audit_mesh(sm.vertices, sm.quads)
        sub_stats[name] = {
            "verts": len(sm.vertices),
            "quads": len(sm.quads),
            "rep_quads": rep.quad_count,
            "tris": rep.tri_count,
            "ngons": rep.ngon_count,
            "non_manifold_edges": len(rep.non_manifold_edges),
            "non_manifold_verts": len(rep.non_manifold_vertices),
            "duplicate_verts": len(rep.duplicate_vertices),
            "degenerate_faces": len(rep.degenerate_faces),
            "is_valid": rep.is_valid,
            "normals_count": len(sm.normals) if sm.normals else 0
        }
        total_verts += len(sm.vertices)
        total_quads += rep.quad_count
        total_tris += rep.tri_count
        total_ngons += rep.ngon_count
        
        # Check normal unit length
        if sm.normals:
            assert len(sm.normals) == len(sm.vertices), f"{name} normals length mismatch"
            for idx, n in enumerate(sm.normals):
                nl = math.sqrt(n[0]**2 + n[1]**2 + n[2]**2)
                assert abs(nl - 1.0) < 1e-4, f"{name} normal at {idx} not normalized: length={nl}"
                
        print(f"  [{name}]: V={len(sm.vertices)}, Q={rep.quad_count}, T={rep.tri_count}, NG={rep.ngon_count}, NM_E={len(rep.non_manifold_edges)}, Valid={rep.is_valid}")
        assert rep.is_valid, f"{name} topology is invalid!"
        assert rep.tri_count == 0, f"{name} has {rep.tri_count} tris!"
        assert rep.ngon_count == 0, f"{name} has {rep.ngon_count} ngons!"
        assert len(rep.non_manifold_edges) == 0, f"{name} has non-manifold edges!"

    print(f"Total Vertices: {total_verts}, Total Quads: {total_quads}, Tris: {total_tris}, N-gons: {total_ngons}")
    assert total_quads == 14218, f"Expected 14,218 quads, got {total_quads}"
    assert total_tris == 0, f"Expected 0 tris, got {total_tris}"
    assert total_ngons == 0, f"Expected 0 ngons, got {total_ngons}"
    assert total_verts == 14532, f"Expected 14,532 vertices, got {total_verts}"
    print("PASS: In-memory generation 100% 2-manifold quads verified (14,218 quads, 0 tris, 0 ngons).")

    # Audit Seam Alignment in Memory
    print("\n=== 2. AUDIT SEAM ALIGNMENT IN MEMORY ===")
    seam_pairs = [
        ("Anime_Head", "Anime_Torso", 46),
        ("Anime_Torso", "Anime_Arms", 92),
        ("Anime_Torso", "Anime_Legs", 50),
    ]
    
    for name_a, name_b, expected_count in seam_pairs:
        ma = res.submeshes[name_a]
        mb = res.submeshes[name_b]
        
        # Check boundary coincident vertices
        coincident = []
        for ia, va in enumerate(ma.vertices):
            for ib, vb in enumerate(mb.vertices):
                dist = math.sqrt((va[0]-vb[0])**2 + (va[1]-vb[1])**2 + (va[2]-vb[2])**2)
                if dist < 1e-4:
                    na = ma.normals[ia]
                    nb = mb.normals[ib]
                    dot = max(-1.0, min(1.0, na[0]*nb[0] + na[1]*nb[1] + na[2]*nb[2]))
                    ang = math.acos(dot)
                    coincident.append((ia, ib, dist, ang))
        
        print(f"  Seam {name_a} <-> {name_b}: Coincident pairs found = {len(coincident)} (expected {expected_count})")
        assert len(coincident) == expected_count, f"Expected {expected_count} pairs, got {len(coincident)}"
        max_ang = max(c[3] for c in coincident)
        avg_ang = sum(c[3] for c in coincident) / len(coincident)
        max_dist = max(c[2] for c in coincident)
        print(f"    Max dist gap: {max_dist:.8f}m, Max normal angular deviation: {max_ang:.8f} rad, Avg: {avg_ang:.8f} rad")
        assert max_ang < 1e-6, f"Seam {name_a}<->{name_b} normal deviation {max_ang} exceeds 1e-6 in memory!"
    print("PASS: Memory seam alignment & normal harmonization verified!")

def audit_exported_objs():
    print("\n=== 3. AUDIT EXPORTED OBJ FILES ===")
    output_dir = proj_dir / "output"
    meshes_dir = output_dir / "meshes"
    
    submesh_names = [
        "Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs",
        "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
    ]
    
    total_obj_v = 0
    total_obj_vn = 0
    total_obj_f = 0
    
    for name in submesh_names:
        p = meshes_dir / f"{name}.obj"
        assert p.exists(), f"OBJ file {p} does not exist"
        assert p.stat().st_size > 0, f"OBJ file {p} is empty"
        
        v_lines = 0
        vn_lines = 0
        vt_lines = 0
        f_lines = 0
        f_quad_count = 0
        f_tri_count = 0
        
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("v "):
                    v_lines += 1
                elif line.startswith("vn "):
                    vn_lines += 1
                elif line.startswith("vt "):
                    vt_lines += 1
                elif line.startswith("f "):
                    f_lines += 1
                    parts = line.strip().split()[1:]
                    if len(parts) == 4:
                        f_quad_count += 1
                    elif len(parts) == 3:
                        f_tri_count += 1
                        
        print(f"  {p.name}: V={v_lines}, VN={vn_lines}, VT={vt_lines}, Faces={f_lines} (Quads={f_quad_count}, Tris={f_tri_count})")
        assert v_lines > 0
        assert vn_lines == v_lines, f"{p.name} has {vn_lines} vn but {v_lines} v!"
        assert f_lines == f_quad_count, f"{p.name} has non-quad faces!"
        assert f_tri_count == 0
        total_obj_v += v_lines
        total_obj_vn += vn_lines
        total_obj_f += f_lines
        
    print(f"Total Individual OBJ: V={total_obj_v}, VN={total_obj_vn}, Faces={total_obj_f}")
    assert total_obj_v == 14532
    assert total_obj_vn == 14532
    assert total_obj_f == 14218
    
    # Audit master OBJ
    master_obj = output_dir / "anime_character_modular.obj"
    assert master_obj.exists(), "Master OBJ does not exist"
    mv = 0
    mvn = 0
    mvt = 0
    mf = 0
    mf_quads = 0
    with open(master_obj, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("v "):
                mv += 1
            elif line.startswith("vn "):
                mvn += 1
            elif line.startswith("vt "):
                mvt += 1
            elif line.startswith("f "):
                mf += 1
                parts = line.strip().split()[1:]
                if len(parts) == 4:
                    mf_quads += 1
                    # check indices
                    for part in parts:
                        v_idx = int(part.split("/")[0])
                        assert 1 <= v_idx <= 14532, f"Master OBJ vertex index {v_idx} out of range"
    print(f"Master OBJ: V={mv}, VN={mvn}, VT={mvt}, Faces={mf} (Quads={mf_quads})")
    assert mv == 14532
    assert mvn == 14532
    assert mf == 14218
    assert mf == mf_quads
    print("PASS: Individual and master OBJ files format integrity & 100% quads verified.")

def audit_blend_and_glb():
    print("\n=== 4. AUDIT BLEND AND GLB IN HEADLESS BLENDER ===")
    blender_exe = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
    blend_path = proj_dir / "output" / "anime_mesh_clean.blend"
    glb_path = proj_dir / "output" / "anime_mesh_clean.glb"
    
    assert blend_path.exists(), f"{blend_path} missing"
    assert glb_path.exists(), f"{glb_path} missing"
    print(f"  anime_mesh_clean.blend size: {blend_path.stat().st_size} bytes")
    print(f"  anime_mesh_clean.glb size: {glb_path.stat().st_size} bytes")
    
    # Script to run inside Blender
    blender_script = """
import bpy, math

print("--- BLENDER AUDIT START ---")
# Check Blend file objects
mesh_objs = {obj.name: obj for obj in bpy.data.objects if obj.type == 'MESH'}
print("Objects found:", list(mesh_objs.keys()))
assert len(mesh_objs) == 7, f"Expected 7 mesh objects in blend, got {len(mesh_objs)}"

total_b_verts = sum(len(o.data.vertices) for o in mesh_objs.values())
total_b_polys = sum(len(o.data.polygons) for o in mesh_objs.values())
quad_polys = sum(sum(1 for p in o.data.polygons if len(p.vertices) == 4) for o in mesh_objs.values())
tri_polys = sum(sum(1 for p in o.data.polygons if len(p.vertices) == 3) for o in mesh_objs.values())
ngon_polys = total_b_polys - quad_polys - tri_polys

print(f"Blend scene: Verts={total_b_verts}, Polys={total_b_polys}, Quads={quad_polys}, Tris={tri_polys}, Ngons={ngon_polys}")
assert total_b_verts == 14532
assert total_b_polys == 14218
assert quad_polys == 14218
assert tri_polys == 0
assert ngon_polys == 0

# Check Seam Normal Alignment across ALL 3 seams in Blend file
seams = [
    ('Anime_Head', 'Anime_Torso', 46),
    ('Anime_Torso', 'Anime_Arms', 92),
    ('Anime_Torso', 'Anime_Legs', 50)
]

for name_a, name_b, exp_count in seams:
    oa = mesh_objs[name_a]
    ob = mesh_objs[name_b]
    va_data = {i: (oa.matrix_world @ v.co, (oa.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(oa.data.vertices)}
    vb_data = {i: (ob.matrix_world @ v.co, (ob.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(ob.data.vertices)}
    coinc = []
    for ia, (coa, noa) in va_data.items():
        for ib, (cob, nob) in vb_data.items():
            if (coa - cob).length < 1e-4:
                dot = max(-1.0, min(1.0, noa.dot(nob)))
                ang = math.acos(dot)
                coinc.append((ia, ib, ang))
    print(f"Blend Seam {name_a} <-> {name_b}: coincident={len(coinc)} (exp {exp_count})")
    assert len(coinc) == exp_count, f"Seam {name_a}<->{name_b} had {len(coinc)} pairs"
    max_ang = max(c[2] for c in coinc)
    avg_ang = sum(c[2] for c in coinc) / len(coinc)
    print(f"  Max normal dev: {max_ang:.6f} rad, Avg: {avg_ang:.6f} rad")
    assert max_ang < 0.005, f"Max normal deviation {max_ang} exceeds 0.005 rad in {name_a}<->{name_b}"

# Now import GLB and check GLB
print("--- IMPORTING GLB ---")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r'""" + str(glb_path).replace("\\", "\\\\") + """')
glb_objs = {obj.name: obj for obj in bpy.context.scene.objects if obj.type == 'MESH'}
print("GLB objects found:", list(glb_objs.keys()))
assert len(glb_objs) == 7

# In GLB, meshes are triangulated or converted according to glTF spec, but let's check seam normals and vertices
for name_a, name_b, exp_count in seams:
    oa = glb_objs[name_a]
    ob = glb_objs[name_b]
    va_data = {i: (oa.matrix_world @ v.co, (oa.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(oa.data.vertices)}
    vb_data = {i: (ob.matrix_world @ v.co, (ob.matrix_world.to_3x3() @ v.normal).normalized()) for i, v in enumerate(ob.data.vertices)}
    coinc = []
    for ia, (coa, noa) in va_data.items():
        for ib, (cob, nob) in vb_data.items():
            if (coa - cob).length < 1e-4:
                dot = max(-1.0, min(1.0, noa.dot(nob)))
                ang = math.acos(dot)
                coinc.append((ia, ib, ang))
    print(f"GLB Seam {name_a} <-> {name_b}: coincident={len(coinc)}")
    assert len(coinc) >= exp_count
    max_ang = max(c[2] for c in coinc)
    avg_ang = sum(c[2] for c in coinc) / len(coinc)
    print(f"  GLB Max normal dev: {max_ang:.6f} rad, Avg: {avg_ang:.6f} rad")
    assert max_ang < 0.005, f"GLB Max normal deviation {max_ang} exceeds 0.005 rad in {name_a}<->{name_b}"

print("PASS_BLENDER_GLB_AUDIT")
"""
    cmd = [blender_exe, "--background", str(blend_path), "--python-expr", blender_script]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    print(res.stdout)
    assert res.returncode == 0, f"Blender headless audit failed:\n{res.stderr}\n{res.stdout}"
    assert "PASS_BLENDER_GLB_AUDIT" in res.stdout
    print("PASS: .blend and .glb format integrity and seam normal alignment verified across all seams.")

if __name__ == "__main__":
    audit_memory_generation()
    audit_exported_objs()
    audit_blend_and_glb()
    print("\nALL INDEPENDENT VERIFICATION CHECKS PASSED SUCCESSFULLY!")
