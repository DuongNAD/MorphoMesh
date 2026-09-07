import sys
import os
import subprocess
import tempfile

sys.path.insert(0, "src")
from morphomesh.human_generator import get_human_generation_script, HumanAnatomyConfig

script = get_human_generation_script("Audit_Blender_Mesh", HumanAnatomyConfig())

blender_test = """
import bpy

obj = bpy.data.objects.get("Audit_Blender_Mesh")
assert obj is not None, "Mesh object not created!"
me = obj.data

tot_polys = len(me.polygons)
quads = sum(1 for p in me.polygons if len(p.vertices) == 4)
tris = sum(1 for p in me.polygons if len(p.vertices) == 3)
ngons = sum(1 for p in me.polygons if len(p.vertices) > 4)
quad_ratio = quads / tot_polys if tot_polys > 0 else 0

print(f"BLENDER_NATIVE: vertices={len(me.vertices)}, total_polys={tot_polys}, quads={quads}, tris={tris}, ngons={ngons}, quad_ratio={quad_ratio:.4f}")
assert tris == 0, f"Blender mesh has {tris} triangles"
assert ngons == 0, f"Blender mesh has {ngons} ngons"
assert quad_ratio >= 0.95, f"Blender quad ratio {quad_ratio} < 0.95"
"""

full_script = script + "\n" + blender_test

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
    assert proc.returncode == 0, f"Blender exited with code {proc.returncode}"
finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

print("Blender headless execution PASSED!")
