import os
import subprocess
from pathlib import Path

blender_exe = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
out_dir = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output")

script = """
import bpy
objs = [o.name for o in bpy.data.objects if o.type == 'MESH']
print("OBJECTS:", sorted(objs))
cols = [c.name for c in bpy.data.collections]
print("COLLECTIONS:", sorted(cols))
"""

for fname in ["anime_mesh_clean.blend", "anime_character_model.blend"]:
    fpath = out_dir / fname
    if fpath.exists():
        print(f"=== {fname} ===")
        cmd = [blender_exe, "--background", str(fpath), "--python-expr", script]
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
        for line in r.stdout.splitlines():
            if "OBJECTS:" in line or "COLLECTIONS:" in line:
                print(" ", line)
