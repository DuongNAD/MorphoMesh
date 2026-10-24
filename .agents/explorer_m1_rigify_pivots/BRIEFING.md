# BRIEFING — 2026-09-07T13:20:00Z

## Mission
Formulate exact code changes for src/morphomesh/human_rigging.py to realign Rigify 163 DEF metarig joint pivots to biological skeletal centers (Feature 7 of Milestone M1).

## 🔒 My Identity
- Archetype: explorer
- Roles: Rigify Pivots Explorer
- Working directory: E:\tool\mcp\MorphoMesh\.agents\explorer_m1_rigify_pivots
- Original parent: 8e1c858e-2863-448c-aaeb-b9860ae4a909
- Milestone: M1 — Human Skeletal Proportions & Anatomic Rigging Realignment

## 🔒 Key Constraints
- Read-only investigation — do NOT implement directly in src/
- Realignment of Rigify 163 DEF metarig joint pivots to biological skeletal centers
- Exact pivot placements:
  * Femoral head hip pivot: raised +0.038m into true acetabular socket (Z = z_pelvic_crest - 0.082m, Y = -0.010m)
  * Knee condylar hinge axis: placed at Z = z_patella - 0.025m, Y = -0.008m (recessed behind patella so flexion swings lower leg without collapsing kneecap)
  * Oblique bimalleolar ankle axis: oriented along true bimalleolar line connecting medial malleolus (Z = 0.088m, Y = +0.002m) and lateral malleolus (Z = 0.076m, Y = -0.006m)
  * Oblique MTP break axis: angled ~65 degrees across metatarsal heads
- Bone hierarchy and roll angle preservation: 163 DEF bones invariant (64 body DEF + 99 facial DEF) must remain 100% compliant with existing tests (test_adversarial_rigging.py)

## Current Parent
- Conversation ID: 8e1c858e-2863-448c-aaeb-b9860ae4a909
- Updated: 2026-09-07T13:20:00Z

## Investigation State
- **Explored paths**:
  * `ORIGINAL_REQUEST.md`: Read section 2026-09-07T13:01:03Z (full team requirements R1-R4)
  * `PROJECT.md`: Read Milestone M1 scope, Feature 7 specifications, interface contracts
  * `survey_anatomy.md`: Comprehensive medical anatomical report on joint pivots, malleoli, and 163 DEF bones
  * `src/morphomesh/human_rigging.py`: Analyzed bone creation, pre-bends, skin weights, blendshapes, script generator
  * `tests/test_adversarial_rigging.py`: Verified all 24 tests pass, checked pre-bend, patella, and headless Blender execution constraints
  * `tests/test_human_rigging.py`: Verified all 21 tests pass, checked landmark snapping and bone counts
  * `tests/test_adversarial_m2_iter2_empirics.py`: Verified all 15 tests pass
- **Key findings**:
  * Femoral head hip pivot: $Z = z_{pelvic\_crest} - 0.082\text{m} \cdot s = 0.863\text{m} \cdot s$ ($+0.038\text{m}$ above crotch line $0.825\text{m}$), $Y = -0.010\text{m}$, $X = \pm 0.088\text{m}$.
  * Knee condylar hinge axis: $Z = z_{patella} - 0.025\text{m} \cdot s = 0.445\text{m} \cdot s$, $Y = -0.008\text{m}$ (maintains $30\text{mm}$ lever arm to patella). Pre-bend $-Y$ satisfied (interior angle $176.55^\circ \in [160^\circ, 179.5^\circ]$).
  * Oblique bimalleolar ankle axis: midpoint of medial malleolus ($Z=0.088\text{m}, Y=+0.002\text{m}$) and lateral malleolus ($Z=0.076\text{m}, Y=-0.006\text{m}$); center pivot $(\pm 0.089, -0.002, 0.082)$; roll Left $-0.156$ rad ($-8.95^\circ$), Right $+0.156$ rad ($+8.95^\circ$).
  * Oblique MTP break axis: center pivot $(\pm 0.089, -0.089, 0.022)$; transverse slant $25^\circ$, longitudinal angle $65^\circ$; roll Left $-0.153$ rad ($-8.74^\circ$), Right $+0.153$ rad ($+8.74^\circ$).
  * 163 DEF bones compile-time invariant (64 body + 99 facial) is 100% preserved.
- **Unexplored areas**: None for M1 Feature 7.

## Key Decisions Made
- Derived exact roll angles for `DEF-foot` and `DEF-toe` to align Blender edit bone local axes with the true bimalleolar line and MTP break line.
- Formulated the implementation of `align_rigify_metarig_pivots` to support both `MetarigStructure` Python objects and live Blender edit bones.
- Enhanced `calculate_anti_pinch_weights` for malleoli anchoring ($\ge 80\%$ on `DEF-shin.001`) and smooth cubic Hermite transition across the $65^\circ$ oblique MTP line.
- Documented all changes and exact diff blocks in `pivots_spec.md`.

## Artifact Index
- pivots_spec.md — Complete technical specification with exact mathematical formulas and before/after code diffs
- handoff.md — 5-component handoff report for orchestrator and downstream worker
- progress.md — Task progress and liveness heartbeat
- DISPATCH.md — Log of received dispatch messages
