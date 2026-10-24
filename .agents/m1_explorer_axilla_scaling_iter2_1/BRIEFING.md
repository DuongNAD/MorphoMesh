# BRIEFING — 2026-09-08T01:39:15+07:00

## Mission
Formulate the exact continuous scaling formula anchoring arm span scaling to the shoulder width expansion in HumanAnatomyGenerator.generate(), eliminating boundary crossover that inverted face 20360 under realistic_female preset.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: E:\tool\mcp\MorphoMesh\.agents\m1_explorer_axilla_scaling_iter2_1
- Original parent: 79a32aca-3f45-4f6c-ae9e-59087d07960a
- Milestone: M1 Iteration 2

## 🔒 Key Constraints
- Read-only investigation — do NOT modify src/ directly
- Write only to .agents/m1_explorer_axilla_scaling_iter2_1/
- Preserve C^0 continuity between shoulder width and arm span scaling
- Eliminate face 20360 inversion and normal flips under all presets

## Current Parent
- Conversation ID: 79a32aca-3f45-4f6c-ae9e-59087d07960a
- Updated: 2026-09-08T01:44:50+07:00

## Investigation State
- **Explored paths**: `ORIGINAL_REQUEST.md`, `PROJECT.md`, `DISPATCH.md`, `.agents/m1_challenger_2/handoff.md`, `src/morphomesh/human_generator.py` (lines 610-850), `tests/test_m1_challenger_2_stress.py`, `tests/run_m1_challenger_2_audit.py`.
- **Key findings**:
  1. Root cause: An unanchored arm span scaling formula at line 655 (`transformed_verts[i][0] = sign_x * (0.18 * s + dist_out * k_arm)`) creates a $10.18$ mm step discontinuity $\Delta x = 0.18 s (k_{shoulder} - 1.0)$ across the $x = 0.18 s$ boundary when $k_{shoulder} > 1.0$ and $k_{arm} = 1.0$.
  2. Quad 10180 spans this boundary: $v_{10450}$ ($x_{raw} = 0.18054$) is pulled inward by $10.2$ mm relative to $v_{10512}$ ($x_{raw} = 0.17601$), inverting face 20360 ($\hat{f}_n \cdot \hat{v}_n = -0.1730$).
  3. Solution: Anchoring arm span scaling to the shoulder width expansion `transformed_verts[i][0] = sign_x * (0.18 * s * k_shoulder + dist_out * k_arm)` restores $C^0$ continuity ($\Delta x \equiv 0$) and strict monotonicity ($\frac{\partial |x_{new}|}{\partial |x|} > 0$).
  4. Verified that face 20360 alignment jumps from $-0.1730$ to $+0.9930$ and symmetric face 7125 from $+0.4368$ to $+0.9930$.
  5. 0 inverted faces across all 7 standard test presets and extreme stress presets ($k_{shoulder}, k_{arm} \in [0.60, 1.60]$).
  6. Restores perfect parity with the Rigify Metarig arm landmark scaling which already uses `(0.175 * k_shoulder + ... * k_arm) * s`.
- **Unexplored areas**: None for this investigation scope.

## Key Decisions Made
- Confirmed Challenger 2's proposed formula as the mathematically exact and minimal solution:
  `transformed_verts[i][0] = sign_x * (0.18 * s * k_shoulder + dist_out * k_arm)` in `src/morphomesh/human_generator.py:655`.
- Avoided unnecessary complex smoothstep windowing, as linear anchoring preserves the affine linearity of arm bones and maintains strict monotonicity without introducing parameter bloat.

## Artifact Index
- `BRIEFING.md` — Persistent working memory
- `progress.md` — Liveness heartbeat
- `handoff.md` — Final structured handoff report
