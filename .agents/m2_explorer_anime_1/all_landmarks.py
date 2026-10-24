import sys
from pathlib import Path
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
from morphomesh.human.mold_loader import extract_makehuman_joint_landmarks

lm = extract_makehuman_joint_landmarks(1.65)
print("=== All Landmarks ===")
for k in sorted(lm.keys()):
    print(f"{k}: {lm[k]}")
