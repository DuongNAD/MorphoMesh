# Task Dispatch — M3 Explorer 3 (Rigify 163 DEF Metarig & Skinning)

## Objective
Formulate the exact technical implementation strategy for Feature 15 (Rigify 163 DEF Metarig & Biological Pivots) in `src/morphomesh/human_rigging.py`:
1. Landmark to Bone Mapping:
   - Align all 163 DEF bones (64 body + 99 facial) to the 125 M1 anatomical joint landmarks (`joint-*` ICR coordinates) from `human_generator.py`.
   - Biological joint pre-bends: elbow +Y (flexion plane), knee -Y (flexion plane) to prevent pole target flipping and volume collapse.
2. Geodesic Biharmonic Skinning Weights:
   - Volume-preserving weight assignment summing strictly to 1.0 for all 13,380 vertices in M1 base mold.
   - Dual-bone twist decomposition (upper arm, forearm, thigh, shin).
   - Clamping deltoid and axilla weights to prevent weight stealing across chest/underarm and inner thighs.
   - Secondary breast and gluteal bone placement and soft skinning gradients.
3. Compatibility and Rig Tests:
   - Review existing implementation in `src/morphomesh/human_rigging.py`.
   - Review `tests/test_human_rigging.py`, `tests/test_adversarial_rigging.py`, `tests/test_adversarial_skinning.py`.
   - Map exact mathematical formulas and parameters for seamless Rigify generation.

## Reference Materials
- `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md` (Mandatory reading)
- `E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md`
- Skeletal Reference: `media_1788785935854.png`

## Output
Write your comprehensive handoff report to:
`E:\tool\mcp\MorphoMesh\.agents\m3_explorer_rigify_metarig_1\handoff.md`
Notify the orchestrator via `send_message` when done.
