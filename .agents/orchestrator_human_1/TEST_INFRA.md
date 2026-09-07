# E2E Test Infra: MorphoMesh Digital Human Pipeline

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on internal implementation hacks.
- Methodology: Category-Partition + BVA + Pairwise + Workload Testing across 4 Tiers.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | Parametric Female Human Anatomy Generator | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 2 | FastMCP Human Engine Tools | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 3 | Blender Socket Bridge Human RPC | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 4 | Rigify Metarig 163 DEF Bones | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 5 | Anti-Pinch Vertex Skinning | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 6 | 52 ARKit FACS Facial Blendshapes | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 7 | PBR Random Walk SSS Skin Shader | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 8 | Dual-Chamber Refractive Eye Optics | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 9 | Geometry Nodes Hair Curves Grooming | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 10 | Dynamic Wardrobe Generator | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 11 | Magic Props: Marionette Red Strings & Butterflies | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 12 | Yu Nian An Master Asset & Collections | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 13 | Multi-Format Export (.blend, .fbx, .gltf) | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |

## Test Architecture
- Test runner: `pytest tests/` in virtual environment
- Blender test invocation: `blender --background --python scripts/test_runner.py` or active socket bridge tests
- Directory layout: `tests/`
