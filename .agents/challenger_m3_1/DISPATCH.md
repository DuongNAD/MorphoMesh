# Dispatch Assignment: Challenger M3-1 (Adversarial Clearance & Manifold Verification)

**Identity**: teamwork_preview_challenger
**Assigned Task**: Adversarial Stress-Testing of War Armor Clearances, Manifold Geometry, and PBR Shaders
**Working Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_m3_1`
**Authoritative Request**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md` (read sections `## 2026-09-05T15:44:52Z` and `## 2026-09-05T15:47:35Z`)
**Project Plan**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`
**Worker M3 Handoff**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m3/handoff.md`

## Instructions
1. Write and execute an adversarial inspection script in headless Blender 5.2.1 LTS verifying:
   - For all 6 armor plates, minimum Euclidean distance to underlying bear skin vertices $d_{\min} \ge 0.015\text{m}$ (assert strictly $> 0.015\text{m}$, expected $\approx 0.025 - 0.036\text{m}$).
   - Every armor plate is a 2-manifold closed shell with exactly 0 non-manifold edges.
   - Zero degenerate zero-area faces in armor meshes.
   - All 5 PBR materials contain valid Principled BSDF v2 sockets, metallic == 1.0 on steel & brass, coat weight >= 0.80 on wet nose, and roughness values matching specs.
2. Stress-test armor fitting under extreme scaling factors ($0.5\times$ to $2.0\times$) and verify clearance scaling holds.
3. Deliver report and verdict (`APPROVE` or `REJECT`) in `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_m3_1/handoff.md` and message orchestrator.

## 2026-09-05T16:53:07Z
You are Challenger M3-1 for Milestone M3.
Your working directory is `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_m3_1`.
Read your dispatch at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_m3_1/DISPATCH.md`, `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`, `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`, and Worker M3's handoff at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m3/handoff.md`.

Perform adversarial verification in headless Blender 5.2.1 LTS:
1. Assert for all 6 armor plates that minimum distance to bear skin vertices d_min >= 0.015m (expect 0.025-0.036m).
2. Assert every plate is 2-manifold closed shell with exactly 0 non-manifold edges.
3. Assert zero degenerate zero-area faces in armor meshes.
4. Assert 5 PBR materials contain valid Principled BSDF v2 sockets, metallic == 1.0 on steel & brass, coat weight >= 0.80 on wet nose.
5. Stress-test armor fitting under scaling (0.5x to 2.0x).
30: Deliver your verdict (APPROVE or REJECT) in `handoff.md` and message orchestrator.
31: 
## 2026-09-07T16:17:35Z
You are Challenger 1 (Challenger M3.1: Sandals Clearance, Height & Toes Exposure Empirical Challenger) for MorphoMesh Milestone M3.
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\challenger_m3_1

MANDATORY FIRST STEP:
You MUST read the following authoritative specification files:
1. ORIGINAL_REQUEST.md at: E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
2. PROJECT.md at: E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_anatomy_gen2\PROJECT.md
3. Worker M3 Handoff & Changes:
   - E:\tool\mcp\MorphoMesh\.agents\worker_m3\handoff.md
   - E:\tool\mcp\MorphoMesh\.agents\worker_m3\changes.md

YOUR OBJECTIVE:
Empirically stress-test the new procedural flat strappy sandals implementation in `src/morphomesh/wardrobe.py`.

SPECIFIC CHALLENGE TASKS:
1. Write and run empirical stress tests (in `tests/test_challenger_m3_sandals.py` or standalone test script):
   - Test extreme character scaling ($H \in [1.50\text{m}, 1.80\text{m}]$) and leg girth variations ($k_{\text{leg}} \in [0.8, 1.2]$).
   - Test total footwear height $\le 50.0\text{mm}$ across all scales.
   - Test sole length $\in [0.22, 0.25]\text{m}$ and ground elevation $Z = 0.0\text{m}$.
   - Test 100% exposed toes and toenails: sole perimeter terminates at $Y = -0.138\text{m}$, big toe and pinky toe landmarks extend past sole with $\ge 7\text{mm}$ clearance.
   - Test zero skin penetration: verify signed distance to underlying foot mesh $\ge +1.5\text{mm}$.
   - Test medial arch rise: verify top footbed elevates by $> +3.5\text{mm}$ along medial border.
   - Test normalized Rigify skinning: 100% of vertices have normalized weights $\sum w_i = 1.0 \pm 10^{-4}$ in `DEF-foot` and `DEF-toe`.
   - Test topology: verify zero degenerate (zero-area) faces.
2. Run tests: `uv run pytest tests/test_wardrobe_m3.py -v`.
3. Provide an explicit verdict in your handoff report: `APPROVE` or `REQUEST_CHANGES`.

COMPLETION REQUIREMENTS:
- Write your empirical report to: `E:\tool\mcp\MorphoMesh\.agents\challenger_m3_1\analysis.md`
- Write your 5-component handoff report to: `E:\tool\mcp\MorphoMesh\.agents\challenger_m3_1\handoff.md` with your explicit verdict.
- Update `progress.md` and send a completion message with your verdict and test results.
