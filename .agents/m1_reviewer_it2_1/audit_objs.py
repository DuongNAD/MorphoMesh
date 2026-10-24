import os
from pathlib import Path

obj_dir = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output")

def audit_file(p):
    counts = {"v": 0, "vn": 0, "vt": 0, "f": 0, "o": 0}
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            tokens = line.strip().split()
            if tokens and tokens[0] in counts:
                counts[tokens[0]] += 1
    print(f"{p.name:30s} | v: {counts['v']:6d} | vn: {counts['vn']:6d} | vt: {counts['vt']:6d} | f: {counts['f']:6d} | o: {counts['o']:2d}")

print("=== OBJ FILE AUDIT ===")
audit_file(obj_dir / "anime_character_modular.obj")
for p in sorted((obj_dir / "meshes").glob("*.obj")):
    audit_file(p)
