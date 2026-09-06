# Project: Armored War Bear & MorphoMesh Engine Upgrade (Gen 2 Orchestrator)

## Architecture
MorphoMesh is an automated pipeline and MCP Server connecting AI generation with Blender. This project upgrades the core MorphoMesh engine (`src/morphomesh/`) to generate high-fidelity, photorealistic biological creatures with anatomically authentic geometry, volumetric fur grooming, and PBR shading, using the Armored War Bear as the canonical benchmark demonstration.

### Component Boundaries
1. **Procedural Geometry Engine (`src/morphomesh/inference_adapter.py`, `src/morphomesh/creature_generator.py`)**:
   - Upgraded `MeshGeometry` with biological modeling primitives: `add_curved_claw()`, `add_plantigrade_paw()`, `add_articulated_head()`, `add_anatomical_torso()`.
   - Continuous organic quadruped anatomy: paws attached without gaps, capped/closed limb cylinders, organic facial features.
   - Mathematical forward-and-downward claw curvature guarantee: $\vec{d}_{\text{claw}} \cdot \vec{u}_{\text{fwd}} > 0.60$ and $d_z < 0$.
   - 18 standardized vertex groups across all major body parts.
2. **Volumetric Fur & Grooming Pipeline (`src/morphomesh/grooming.py`, `src/morphomesh/blender_bridge.py`)**:
   - Multi-layer hair grooming system: undercoat + guard hairs with interpolated children.
   - Dual representation: Native Blender Curves in `.blend` + curve-to-mesh ribbon generator for standard glTF 2.0 `.glb` export.
3. **PBR Material & Armor Fitting Engine (`src/morphomesh/materials.py`, `src/morphomesh/armor.py`)**:
   - 5 distinct 4-channel PBR material slots compliant with Blender 5.2.1 Principled BSDF v2.
   - Procedural armor fitting generator maintaining non-intersecting radial clearance $d_{\min} \ge 0.015\text{m}$ (0 inside vertices in BVH check).
4. **Canonical Benchmark & Verification Suite (`examples/`, `verify_bear_anatomy.py`, `tests/test_bear_anatomy.py`)**:
   - Canonical assets: `examples/Armored_War_Bear_HD.glb` and `examples/Armored_War_Bear_HD.blend`.
   - Automated inspection script `verify_bear_anatomy.py` with true BVH point-to-surface distance testing.
   - Pytest suite `tests/test_bear_anatomy.py` with genuine watertightness and clearance tests.
   - 4 high-resolution beauty renders saved to `examples/renders/`.

---

## Milestones & Status
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Reusable Anatomy Generator & Claw Fix | Features 1-5 in `src/morphomesh/` (`inference_adapter.py`, `blender_bridge.py`) | none | DONE |
| M2 | Volumetric Fur & Grooming Engine | Features 6-8 in `src/morphomesh/grooming.py` + hair curves on bear mesh | M1 | DONE |
| M3 | PBR Shader Engine & War Armor Fitting | Features 9-10 in `src/morphomesh/materials.py`, `armor.py` | M1, M2 | DONE |
| M4 | Scene Assembly, Export, Verification & Renders | M4 Iteration 2: Remediate Findings 1, 2, 3; Re-assemble, Re-render, Verify | M1, M2, M3 | DONE |

---

## Remediation Objectives (M4 Iteration 2)
1. **Finding 1**: Replace facade test in `tests/test_bear_anatomy.py:209-219` with authentic watertight 2-manifold verification and surface clearance checks.
2. **Finding 2**: Eliminate pauldron interpenetration (-33.6 mm) in `src/morphomesh/armor.py` so that true BVH point-to-surface clearance $d_{\min} \ge 0.015\text{m}$ with 0 inside vertices, and update `verify_bear_anatomy.py` with true BVH point-to-surface collision testing.
3. **Finding 3**: Resolve anatomical discontinuity in `src/morphomesh/creature_generator.py` (reattach front-right paw, close limb cylinder openings, refine organic facial features) and re-render the 4 beauty renders with proper visual presentation.
