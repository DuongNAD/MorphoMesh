import sys
from pathlib import Path

mesh_dir = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output\meshes")
obj_files = sorted(mesh_dir.glob("*.obj"))

print(f"Found {len(obj_files)} OBJ files in {mesh_dir}")

for obj_path in obj_files:
    if "modular" in obj_path.name:
        continue
    verts = []
    with open(obj_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("v "):
                parts = line.strip().split()[1:]
                verts.append([float(p) for p in parts[:3]])
    
    if not verts:
        print(f"[{obj_path.name}] No vertices")
        continue

    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]

    print(f"\n[{obj_path.name}] Vertices: {len(verts)}")
    print(f"  X: min={min(xs):.4f}, max={max(xs):.4f}, span={max(xs)-min(xs):.4f}")
    print(f"  Y: min={min(ys):.4f}, max={max(ys):.4f}, span={max(ys)-min(ys):.4f}")
    print(f"  Z: min={min(zs):.4f}, max={max(zs):.4f}, span={max(zs)-min(zs):.4f}")
