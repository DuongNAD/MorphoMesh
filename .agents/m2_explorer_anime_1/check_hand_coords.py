import sys
from pathlib import Path
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
from morphomesh.human.mold_loader import extract_makehuman_joint_landmarks

lm = extract_makehuman_joint_landmarks(1.65)

# Left Hand joints
print("Left hand joints:")
print(f"  wrist (joint-l-hand): {lm['joint-l-hand']}")
print(f"  mid-palm (joint-l-hand-2): {lm['joint-l-hand-2']}")
print(f"  metacarpal (joint-l-hand-3): {lm['joint-l-hand-3']}")
print("Thumb:")
for i in range(1, 5):
    print(f"  finger-1-{i}: {lm[f'joint-l-finger-1-{i}']}")
print("Index:")
for i in range(1, 5):
    print(f"  finger-2-{i}: {lm[f'joint-l-finger-2-{i}']}")
print("Middle:")
for i in range(1, 5):
    print(f"  finger-3-{i}: {lm[f'joint-l-finger-3-{i}']}")
print("Ring:")
for i in range(1, 5):
    print(f"  finger-4-{i}: {lm[f'joint-l-finger-4-{i}']}")
print("Pinky:")
for i in range(1, 5):
    print(f"  finger-5-{i}: {lm[f'joint-l-finger-5-{i}']}")
