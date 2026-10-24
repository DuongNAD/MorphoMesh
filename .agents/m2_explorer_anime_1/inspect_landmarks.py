import sys
from pathlib import Path
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
from morphomesh.human.mold_loader import extract_makehuman_joint_landmarks

lm = extract_makehuman_joint_landmarks(1.65)
print(f"Total landmarks: {len(lm)}")
for k in sorted(lm.keys()):
    if "finger" in k or "hand" in k or "thumb" in k or "wrist" in k:
        print(f"  {k}: {lm[k]}")
