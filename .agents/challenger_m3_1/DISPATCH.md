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
Deliver your verdict (APPROVE or REJECT) in `handoff.md` and message orchestrator.
