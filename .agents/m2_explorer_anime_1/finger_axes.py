import sys
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
from morphomesh.human.mold_loader import extract_makehuman_joint_landmarks

lm = extract_makehuman_joint_landmarks(1.65)
dorsal_L = Vector((-0.2, -0.6, 0.77)).normalized()

finger_defs = [
    ("Thumb", ["joint-l-finger-1-1", "joint-l-finger-1-2", "joint-l-finger-1-3", "joint-l-finger-1-4"]),
    ("Index", ["joint-l-finger-2-1", "joint-l-finger-2-2", "joint-l-finger-2-3", "joint-l-finger-2-4"]),
    ("Middle", ["joint-l-finger-3-1", "joint-l-finger-3-2", "joint-l-finger-3-3", "joint-l-finger-3-4"]),
    ("Ring", ["joint-l-finger-4-1", "joint-l-finger-4-2", "joint-l-finger-4-3", "joint-l-finger-4-4"]),
    ("Pinky", ["joint-l-finger-5-1", "joint-l-finger-5-2", "joint-l-finger-5-3", "joint-l-finger-5-4"]),
]

for name, pts in finger_defs:
    p0, p1, p2, p3 = [Vector(lm[p]) for p in pts]
    v01 = (p1 - p0).normalized()
    v12 = (p2 - p1).normalized()
    v23 = (p3 - p2).normalized()
    h = v01.cross(v12)
    if h.length < 1e-4:
        h = v12.cross(v23)
    h.normalize()
    up = h.cross(v01).normalized()
    if up.z < 0:
        up = -up
        h = -h
    print(f"Finger {name:6s}:")
    print(f"  v01: ({v01.x:.4f}, {v01.y:.4f}, {v01.z:.4f})")
    print(f"  hinge (cross): ({h.x:.4f}, {h.y:.4f}, {h.z:.4f})")
    print(f"  finger_up: ({up.x:.4f}, {up.y:.4f}, {up.z:.4f})")
