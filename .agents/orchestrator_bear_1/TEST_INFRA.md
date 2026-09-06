# E2E Test Infra: Armored War Bear & MorphoMesh Engine

## Test Philosophy
- Requirement-driven, opaque-box, and mathematical verification.
- Validates both engine-level procedural generators and canonical asset outputs in Blender 5.2.1 LTS.

## Feature Inventory & Test Coverage
| # | Feature | Requirement | Tier 1 (Unit/Feature) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (E2E Benchmark) |
|---|---------|-------------|:---------------------:|:-----------------:|:-----------------:|:----------------------:|
| 1 | Socket Bridge Fix | Robust IPC dispatch | ✓ | ✓ | ✓ | ✓ |
| 2 | Curved Claw Direction | dot(claw, fwd) > 0.6, dz < 0 | ✓ | ✓ | ✓ | ✓ |
| 3 | Plantigrade Paws & Pads | Calcaneus heel & 5 pads | ✓ | ✓ | ✓ | ✓ |
| 4 | Articulated Head & Face | Nostrils, mouth, teeth, eyelids | ✓ | ✓ | ✓ | ✓ |
| 5 | Volumetric Fur System | Multi-layer, >=10,000 strands | ✓ | ✓ | ✓ | ✓ |
| 6 | 4-Channel PBR Materials | 5 distinct material slots | ✓ | ✓ | ✓ | ✓ |
| 7 | Non-intersecting Armor | Radial clearance > 0.02m | ✓ | ✓ | ✓ | ✓ |
| 8 | Production glTF & .blend | Valid file headers, non-empty | ✓ | ✓ | ✓ | ✓ |
| 9 | Multi-Angle Renders | 4 camera renders saved | ✓ | ✓ | ✓ | ✓ |

## Test Architecture
- **Standalone Script**: `verify_bear_anatomy.py` executed via `/Applications/Blender.app/Contents/MacOS/Blender --background examples/Armored_War_Bear_HD.blend --python verify_bear_anatomy.py`.
- **Pytest Suite**: `tests/test_bear_anatomy.py` executed via `pytest -v tests/test_bear_anatomy.py`.
- **Assertion Formulas**:
  1. Claws: $\forall i \in [0, 19]: \vec{d}_{\text{claw}, i} \cdot (0, -1, 0) > 0.60$ and $\vec{d}_{\text{claw}, i} \cdot (0, 0, -1) > 0.0$ (pitch downward).
  2. Features: Check existence of non-empty vertex groups or mesh components for `snout`, `nostrils`, `mouth_cavity`, `teeth`, `eyelids`, `ears`, `pads`.
  3. Fur: Assert active hair particle/curve strands count $\ge 10,000$.
  4. Armor: Minimum distance between armor vertices and underlying bear body mesh $\ge 0.015\text{m}$.
  5. Exports: File sizes of `examples/Armored_War_Bear_HD.glb` and `examples/Armored_War_Bear_HD.blend` $> 500\text{ KB}$.
