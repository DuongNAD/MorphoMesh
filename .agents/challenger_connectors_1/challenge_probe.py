"""
Empirical Challenge Probe for MorphoMesh Phase 2 Connectors.
Exploratory checks across the 4 challenge areas.
"""

import math
import numpy as np
import os
import sys

# Ensure src is on path
sys.path.insert(0, "/Users/duongnad/Documents/tool/MorphoMesh/src")

from morphomesh.connectors.animals3d_connector import (
    RX_90_SMAL_TO_BLENDER,
    CANONICAL_SMAL_35_JOINTS,
    SMAL_TO_RIGIFY_WOLF,
    transform_smal_to_blender,
    Animals3DConnector,
    AnimalPoseInput,
)
from morphomesh.connectors.meshanything_connector import (
    MeshAnythingConnector,
    MeshAnythingInput,
    RetopologyConfig,
)
from morphomesh.connectors.anycreature_connector import (
    AnyCreatureConnector,
    CreaturePromptSpec,
)
from morphomesh.connectors.trellis_connector import (
    TrellisConnector,
    TrellisInput,
)
from morphomesh.connectors.hunyuan_connector import (
    HunyuanConnector,
    HunyuanInput,
)

print("--- 1. ANIMALS3D / SMAL CHECK ---")
R = np.array(RX_90_SMAL_TO_BLENDER)
det = np.linalg.det(R)
is_orthogonal = np.allclose(np.dot(R, R.T), np.eye(3))
print(f"R:\n{R}")
print(f"det(R): {det:.6f}")
print(f"R * R^T == I: {is_orthogonal}")

# Check SMAL 35 joints mapping
missing_keys = set(CANONICAL_SMAL_35_JOINTS.keys()) - set(SMAL_TO_RIGIFY_WOLF.keys())
print(f"SMAL 35 count: {len(CANONICAL_SMAL_35_JOINTS)}")
print(f"Missing keys in SMAL_TO_RIGIFY_WOLF: {missing_keys}")

# Test canonical points mapping
test_pts = [
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
    [1.23, -4.56, 7.89],
]
for pt in test_pts:
    res = transform_smal_to_blender(pt)
    expected = [round(pt[0], 6), round(-pt[2], 6), round(pt[1], 6)]
    mat_mul = np.dot(R, np.array(pt)).tolist()
    mat_mul = [round(x, 6) for x in mat_mul]
    print(f"Pt {pt} -> fn: {res}, mat: {mat_mul}, expected: {expected}, match: {res == expected == mat_mul}")

print("\n--- 2. MESHANYTHING CHECK ---")
mc = MeshAnythingConnector()
print(f"MeshAnything initialized: {mc.initialize()}")

print("\n--- 3. ANYCREATURE CHECK ---")
ac = AnyCreatureConnector()
print(f"AnyCreature initialized: {ac.initialize()}")

print("\n--- 4. TRELLIS & HUNYUAN CHECK ---")
tc = TrellisConnector()
hc = HunyuanConnector()
print(f"Trellis initialized: {tc.initialize()}")
print(f"Hunyuan initialized: {hc.initialize()}")
