# Task Dispatch — M3 Worker (Yu Nian An Assembly & Rigify Rigging Implementation)

## Objective
Implement Features 12, 13, 14, and 15 of Milestone 3 for MorphoMesh:
1. **Feature 12: 6-Strata Hime Cut Hair System** (`src/morphomesh/human_grooming.py`, `src/morphomesh/character_assembler.py`):
   - Stratum 1: Straight bangs (`Hair_Hime_Bangs`) conforming to forehead curvature with horizontal blunt cut at $Z \in [1.54, 1.58]$m grazing eyebrow ridge, $+3.2$mm clearance ($>1.5$mm requirement).
   - Stratum 2: Sidelocks (`Hair_Hime_Sidelocks`, "Hime Bins") with cheek-hugging trajectory and razor-sharp blunt cutoff at jawline/chin level $Z \in [1.42, 1.48]$m with $+2.8$mm clearance. Maintain length preset compatibility.
   - Stratum 3: Back cascade (`Hair_Back_Cascade`) conforming to cervical/thoracic/lumbar lordosis down to hip/thigh level $Z \in [0.70, 0.80]$m with $+15.5$mm clearance over spine and dress.
   - Stratum 4: Crown volume (`Hair_Scalp_Crown`) with calvaria envelope volume lift (+8mm) and offset parting producing the Tenshi no Wa (angel ring) highlight.
   - Stratum 5: Eyebrows (`Hair_Eyebrows`) with delicate melancholic arch.
   - Stratum 6: Eyelashes (`Hair_Eyelashes`) with upper and lower lid lash fringes.
   - Dual representation: Native Curves with `GN_HairGroom` Geometry Nodes modifier in Blender and evaluated pure-quad ribbon meshes for glTF/FBX.
2. **Feature 13: 10 Crimson Marionette Strings** (`src/morphomesh/character_assembler.py`):
   - 0.0mm precise snapping coordinates to the 10 fingertips from M1 landmarks (`joint-l/r-finger-{1..5}-4`).
   - Catenary curve formulation $y(x) = a \cosh(x/a)$ with tension $\tau = 0.85$, sag ratio $\sigma = 0.035$, pure-quad ribbon (width 0.8mm, 0 non-manifold edges).
3. **Feature 14: 10 Glowing Swallowtail Butterflies** (`src/morphomesh/character_assembler.py`):
   - 24 pure-quad swallowtail butterflies (48 vertices, 0 triangles) with 3D segmented body, antennae, and swallowtail spurs.
   - Bilateral vortex spiral flocking formation (5 left-wing, 5 right-wing) orbiting hands and flanks in logarithmic spiral: pairwise separation $\ge 150$mm, $Z \in [0.88, 1.32]$m, $|X| \ge 0.35$m.
   - Emissive glow shader (`Mat_Magic_Butterfly`: emission 3.2, SSS 0.45, pearl white with soft blue rim).
   - In `character_assembler.py:1296-1307`, replace legacy hardcoded `flutter_positions` with `get_butterfly_vortex_positions` to resolve string detachment and spacing in `test_challenger_m3_props.py`.
4. **Feature 15: Rigify 163 DEF Metarig & Biological Pivots** (`src/morphomesh/human_rigging.py`):
   - Align all 163 DEF bones (64 body + 99 facial) directly to MakeHuman 125 `joint-*` landmarks, resolving the ~25cm arm/wrist/finger coordinate offset.
   - Properly partition 1,316 finger vertices into: thumb: 34, index: 308, middle: 312, ring: 318, pinky: 344 using point-to-segment distance to `joint-*-finger-{1..5}-{1..4}`.
   - Enforce $+Y$ (posterior $\ge +0.015$m) elbow pre-bend and $-Y$ (anterior $\le -0.018$m) knee pre-bend.
   - Closed-form edit bone roll normalization.
   - Geodesic biharmonic skinning weights summing strictly to 1.0 ($\sum w_i = 1.00000$) across all 13,380 base mold vertices.
   - Axilla fold clamping ($\ge 75\%$ on `DEF-spine.003`), 0.00% arm bone weight stealing on chest, bilateral inner thigh separation across $X=0$.
   - Teardrop breast soft skinning gradient across 143 vertices in `breast.L` and `breast.R`.

## Exclusive Write Ownership
- `src/morphomesh/character_assembler.py`
- `src/morphomesh/human_rigging.py`
- `src/morphomesh/human_grooming.py`
- Relevant test files in `tests/` for M3 verification

## Input Reports
- `E:\tool\mcp\MorphoMesh\.agents\m3_explorer_hair_strata_1\handoff.md`
- `E:\tool\mcp\MorphoMesh\.agents\m3_explorer_cords_butterflies_1\handoff.md`
- `E:\tool\mcp\MorphoMesh\.agents\m3_explorer_rigify_metarig_1\handoff.md`

## Verification Commands
- `uv run pytest tests/test_human_grooming.py tests/test_character_assembler.py tests/test_adversarial_character_assembler.py -v`
- `uv run pytest tests/test_human_rigging.py tests/test_adversarial_rigging.py tests/test_adversarial_skinning.py -v`
- `uv run pytest tests/test_challenger_m3_props.py -v`
- `uv run pytest tests/test_wardrobe_m3.py -v`

## 2026-09-08T02:41:48Z
Implement Features 12, 13, 14, 15:
- Feature 12 (6-Strata Hime Cut Hair System): Bangs, sidelocks, back cascade, crown volume, brows/lashes; dual representation (native curves GN modifier + evaluated pure-quad ribbons).
- Feature 13 & 14 (10 Crimson Strings & 10 Glowing Butterflies): 0.0mm finger-snapping with M1 landmarks, catenary curves, pure-quad swallowtail butterflies (48 verts, 0 tris) in bilateral vortex flocking (5 L, 5 R, separation >= 150mm), replace hardcoded flutter_positions in character_assembler.py:1296-1307.
- Feature 15 (Rigify 163 DEF Metarig & Biological Pivots): Align 163 DEF bones to MakeHuman 125 landmarks, partition 1,316 finger vertices into 5 digits, enforce +Y elbow and -Y knee pre-bends, bone roll normalization, geodesic biharmonic skinning weights summing strictly to 1.0.
- Verify 100% test pass.

## 2026-09-08T03:00:15Z
**Context**: Milestone M3 Character Assembly & Rigging Implementation
**Content**: Checking on current progress and active step. What step are you currently executing?
**Action**: Please report your current progress, files touched, or test execution status.
