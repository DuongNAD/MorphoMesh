import sys
import os
import subprocess
import tempfile

sys.path.insert(0, "src")
from morphomesh.human_generator import get_human_generation_script, HumanAnatomyConfig

script = get_human_generation_script("Audit_Manifold_Mesh", HumanAnatomyConfig())

blender_check = """
import bpy
import bmesh

obj = bpy.data.objects.get("Audit_Manifold_Mesh")
bm = bmesh.new()
bm.from_mesh(obj.data)

boundary_edges = [e for e in bm.edges if e.is_boundary]
non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
total_edges = len(bm.edges)
total_faces = len(bm.faces)

print(f"BLENDER_BMESH: edges={total_edges}, faces={total_faces}, boundary_edges={len(boundary_edges)}, non_manifold={len(non_manifold_edges)}")
assert len(boundary_edges) == 0, f"Found {len(boundary_edges)} boundary edges in Blender!"
assert len(non_manifold_edges) == 0, f"Found {len(non_manifold_edges)} non-manifold edges in Blender!"
bm.free()
"""

full_script = script + "\n" + blender_check

with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
    f.write(full_script)
    tmp_path = f.name

try:
    proc = subprocess.run(
        [r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe", "--background", "--factory-startup", "--python", tmp_path],
        capture_output=True,
        text=True
    )
    print("STDOUT:")
    print(proc.stdout)
    if proc.stderr:
        print("STDERR:")
        print(proc.stderr)
    assert proc.returncode == 0
finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

print("Blender BMesh manifold check PASSED!")
