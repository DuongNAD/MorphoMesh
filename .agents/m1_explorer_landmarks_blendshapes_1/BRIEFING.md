# BRIEFING — 2026-09-07T17:38:00Z

## Mission
Formulate the landmark extraction, vertex groups, and ARKit blendshapes strategy for Milestone M1 (Anatomical Female Base Mold): extracting 70+ anatomical joint landmarks from `data/templates/makehuman_base.obj`, mapping 24+ standardized vertex groups on the 13,380-vertex clean base mold, calibrating the 52 Apple ARKit FACS blendshapes, and ensuring seamless downstream compatibility with Rigify 163 DEF metarig alignment in `src/morphomesh/human_rigging.py`.

## 🔒 My Identity
- Archetype: Explorer
- Roles: Landmarks, Vertex Groups, FACS Blendshapes Specialist, Biomechanical Rigging Alignment Architect
- Working directory: E:\tool\mcp\MorphoMesh\.agents\m1_explorer_landmarks_blendshapes_1
- Original parent: 79a32aca-3f45-4f6c-ae9e-59087d07960a (orchestrator_female_mold_1)
- Milestone: M1 (Anatomical Female Base Mold)

## 🔒 Key Constraints
- Read-only investigation — do NOT modify production source code in `src/` directly (propose code and write comprehensive analysis and implementation recipes in agent folder).
- Formula for joint landmarks: $$\vec{C}_{\text{joint}} = \frac{1}{8}\sum_{i=1}^8 \vec{v}_i$$
- Coordinate transformation from MakeHuman (decimeters, Y-up) to Blender 4.5+ (meters, Z-up, grounded feet at Z=0.0).
- Standardized human vertex groups: All 24+ groups in `STANDARDIZED_HUMAN_VERTEX_GROUPS` must be mapped on the 13,380 vertex clean mesh.
- Blendshapes: All 52 ARKit FACS facial blendshapes (`ARKIT_52_BLENDSHAPES`) must be mapped or calibrated with non-zero, anatomically plausible deltas.
- Interface contract compatibility: Zero regression against `src/morphomesh/human_rigging.py`, `human_generator.py`, `character_assembler.py`, and the 1,994 pytest suite.

## Current Parent
- Conversation ID: 79a32aca-3f45-4f6c-ae9e-59087d07960a
- Updated: 2026-09-07T17:45:00Z

## Investigation State
- **Explored paths**: `ORIGINAL_REQUEST.md`, `PROJECT.md`, survey handoffs (`survey_explorer_codebase_1`, `survey_explorer_character_pipeline_1`), `m1_explorer_anatomy_contours_1/handoff.md`, `src/morphomesh/human_generator.py`, `src/morphomesh/human_rigging.py`, `data/templates/makehuman_base.obj`, `data/templates/makehuman_clean_body.obj`, `data/templates/anatomical_female_base_mold.obj`.
- **Key findings**:
  1. `data/templates/makehuman_base.obj` contains exactly 125 `joint-*` groups (16 head/face, 6 spine/pelvis, 14 arm/hand, 40 fingers, 10 leg/foot, 38 toes, 1 ground). Every single joint group has exactly 8 vertices forming a closed bounding box cuboid with 6 quad faces. Centroid averaging $\vec{C} = \frac{1}{8}\sum v_i$ yields the exact 3D ICR pivot.
  2. Coordinate transformation from MakeHuman decimeters to Blender meters: $X_b = 0.1 \cdot s \cdot X_{\text{mh}}$, $Y_b = -0.1 \cdot s \cdot Z_{\text{mh}}$, $Z_b = 0.1 \cdot s \cdot (Y_{\text{mh}} + 8.1676)$, where $s = H / 1.66589$.
  3. `data/templates/anatomical_female_base_mold.obj` is the authoritative 13,380-vertex base mold in Blender meters space (13,378 quads, 100% 2-manifold, 0 boundary edges), preserving 1:1 vertex index correspondence with `makehuman_clean_body.obj`.
  4. All 34 standardized human vertex groups (`STANDARDIZED_HUMAN_VERTEX_GROUPS`) are rigorously mapped via anatomical bounding planes and landmark-referenced spheres. Tested and verified: 100% non-empty, valid integer indices, exact bilateral symmetry.
  5. All 52 Apple ARKit FACS blendshapes produce valid sparse 3D displacements on the 13,380-vertex mold with non-zero magnitudes ($>10^{-6}\text{m}$), correct physiological vectors (blink down, jaw down, smile up/out, tongue forward), and strict anatomical facial zone confinement.
  6. Rigify 163 DEF metarig alignment, ICR pivot placement, and anti-pinch biharmonic skinning weight normalization ($\sum w_i = 1.0$) execute smoothly across all 13,380 vertices with 0 errors.
- **Unexplored areas**: None for M1 scope; downstream wardrobe binding and cloth simulation will be formulated in M2.

## Key Decisions Made
- Confirmed extraction of all 125 joint landmarks from `makehuman_base.obj` and mapping to the 53 canonical/extended landmarks required by `human_rigging.py` and `tests/test_empiric_m1_anatomy.py`.
- Formulated an exact spatial and landmark-referenced mapping recipe for all 34 `STANDARDIZED_HUMAN_VERTEX_GROUPS` on the 13,380-vertex clean mesh.
- Validated that `generate_arkit_52_blendshapes` in `human_rigging.py` operates polymorphically on the 13,380-vertex mesh when facial vertex groups are mapped.
- Verified that Rigify metarig generation, ICR pivot alignment, and dual-bone twist weight normalization succeed on the 13,380-vertex mesh.

## Artifact Index
- `BRIEFING.md` — Agent working memory
- `progress.md` — Liveness heartbeat and milestone tracking
- `handoff.md` — 5-component structured handoff report
- `extract_keys.py` — Landmark diagnostic utility

