# Worker M1 Fix Dispatch
Milestone: M1 (Research & Benchmark Docs) — Fix Implementation
Target File: docs/RESEARCH_BENCHMARK.md
Fix Plan: /Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_fix/fix_plan.md
Working Directory: /Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m1_fix
Original Request: /Users/duongnad/Documents/tool/MorphoMesh/ORIGINAL_REQUEST.md

## 2026-09-05T11:41:01Z
You are Worker M1 Fix for MorphoMesh Milestone M1 (Research & Benchmark Docs).
Your working directory is: /Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m1_fix
The authoritative user request is: /Users/duongnad/Documents/tool/MorphoMesh/ORIGINAL_REQUEST.md
The project plan is: /Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_1/PROJECT.md
The target file you own exclusively is: /Users/duongnad/Documents/tool/MorphoMesh/docs/RESEARCH_BENCHMARK.md
The exact step-by-step fix blueprint is at: /Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_fix/fix_plan.md
The explorer handoff is at: /Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_fix/handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your task:
Read `fix_plan.md` and apply all updates to `docs/RESEARCH_BENCHMARK.md`:
1. Section 2 & 3: Correct license classifications:
   - MeshAnything / MeshAnything V2: S-Lab 1.0 (Non-commercial research only).
   - TRELLIS.2: MIT Code + NVIDIA nvdiffrast non-commercial license for rasterization kernel.
   - Tencent Hunyuan Community License: Add territorial exclusion footnote (barring commercial use in EU, UK, South Korea).
   - SMAL / BARC / BITE: Note Max Planck Society non-commercial restriction.
2. Section 6: Update hardware analysis to explicitly document that `spconv` and `nvdiffrast` have no macOS wheels or compilation support, establishing the Remote Cloud GPU tier as a hard architectural requirement (not just latency).
3. Section 7.1: Replace `assemble_fantasy_chimera_rig` with the verified Blender 5.2.1 script from `fix_plan.md` using `armature_wolf_metarig_add`, `armature_bird_metarig_add`, pre-join bird bone pruning, `shoulder.L.001` reparenting to `spine.002`, and `RIG-MetaRig_Chimera` retrieval.
4. Section 7.2: Add the verified 35-joint `SMAL_TO_RIGIFY_WOLF` translation table and IK roll alignment instructions.
5. Section 7.3: Replace `bake_high_to_low_poly` with the verified script from `fix_plan.md` including UV smart project, active material creation, texture node setup, and scale-aware rays.

Verify that `docs/RESEARCH_BENCHMARK.md` is updated, syntactically clean, and complete.
Write your handoff report to `handoff.md`, update `progress.md`, and notify me via `send_message`.

