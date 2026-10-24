import sys
from pathlib import Path

mesh_dir = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output\meshes")

submeshes = {}
for name in ["Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs", "Anime_Shoes", "Anime_Skirt", "Anime_Hair"]:
    obj_path = mesh_dir / f"{name}.obj"
    verts = []
    if obj_path.exists():
        with open(obj_path, "r") as f:
            for line in f:
                if line.startswith("v "):
                    verts.append([float(x) for x in line.strip().split()[1:4]])
    submeshes[name] = verts
    print(f"Loaded {name}: {len(verts)} verts")

# Compute overall bounding box
all_verts = [v for vs in submeshes.values() for v in vs]
min_x, max_x = min(v[0] for v in all_verts), max(v[0] for v in all_verts)
min_y, max_y = min(v[1] for v in all_verts), max(v[1] for v in all_verts)
min_z, max_z = min(v[2] for v in all_verts), max(v[2] for v in all_verts)

total_height = max_z - min_z
print(f"\nCharacter Overall Bounds:")
print(f"  X: [{min_x:.4f}, {max_x:.4f}] span={max_x-min_x:.4f}")
print(f"  Y: [{min_y:.4f}, {max_y:.4f}] span={max_y-min_y:.4f}")
print(f"  Z: [{min_z:.4f}, {max_z:.4f}] span={total_height:.4f}")

# Check key anatomical slices
# 1. Head top: max Z of Anime_Head
head_top_z = max(v[2] for v in submeshes["Anime_Head"])
# 2. Chin: lowest anterior vertex of head
chin_candidates = [v for v in submeshes["Anime_Head"] if v[1] < -0.04 and v[2] < 1.45 and abs(v[0]) < 0.03]
chin_pt = min(chin_candidates, key=lambda v: v[2]) if chin_candidates else None
print(f"Head Top Z: {head_top_z:.4f}")
if chin_pt:
    print(f"Chin Point: ({chin_pt[0]:.4f}, {chin_pt[1]:.4f}, {chin_pt[2]:.4f})")

# 3. Neck seam: coincident between Head and Torso
neck_head_verts = [v for v in submeshes["Anime_Head"] if v[2] < 1.42]
neck_torso_verts = [v for v in submeshes["Anime_Torso"] if v[2] > 1.37]
print(f"Neck Head verts near seam: {len(neck_head_verts)}, Torso verts near seam: {len(neck_torso_verts)}")
neck_cz = sum(v[2] for v in neck_torso_verts) / len(neck_torso_verts)
print(f"Neck Seam Z: {neck_cz:.4f}")

# 4. Pelvis / Hips: bottom of Torso
pelvis_verts = [v for v in submeshes["Anime_Torso"] if v[2] < 0.88]
pelvis_c = (
    sum(v[0] for v in pelvis_verts) / len(pelvis_verts),
    sum(v[1] for v in pelvis_verts) / len(pelvis_verts),
    sum(v[2] for v in pelvis_verts) / len(pelvis_verts),
)
print(f"Pelvis Centroid: ({pelvis_c[0]:.4f}, {pelvis_c[1]:.4f}, {pelvis_c[2]:.4f})")

# 5. Elbows: lateral extremum in arms
elbow_l_candidates = [v for v in submeshes["Anime_Arms"] if v[0] > 0.28 and 1.10 < v[2] < 1.25]
elbow_l_c = (
    sum(v[0] for v in elbow_l_candidates) / len(elbow_l_candidates),
    sum(v[1] for v in elbow_l_candidates) / len(elbow_l_candidates),
    sum(v[2] for v in elbow_l_candidates) / len(elbow_l_candidates),
)
print(f"Elbow Left Centroid: ({elbow_l_c[0]:.4f}, {elbow_l_c[1]:.4f}, {elbow_l_c[2]:.4f})")

# 6. Wrists: constriction before hand
wrist_l_candidates = [v for v in submeshes["Anime_Arms"] if v[0] > 0.38 and 1.02 < v[2] < 1.08 and v[1] > -0.20]
wrist_l_c = (
    sum(v[0] for v in wrist_l_candidates) / len(wrist_l_candidates) if wrist_l_candidates else (0,0,0)
)
print(f"Wrist Left Centroid: {wrist_l_c}")
