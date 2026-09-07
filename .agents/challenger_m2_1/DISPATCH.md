# Dispatch Assignment: Challenger M2-1 (Adversarial Fur & Grooming Verification)

**Identity**: teamwork_preview_challenger
**Assigned Task**: Adversarial Stress-Testing of Fur Density, Biological Flow, and Masking
**Working Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_m2_1`
**Authoritative Request**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md` (read sections `## 2026-09-05T15:44:52Z` and `## 2026-09-05T15:47:35Z`)
**Project Plan**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`
**Worker M2 Handoff**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m2/handoff.md`

## Instructions
1. Write and execute an adversarial inspection script in headless Blender 5.2.1 LTS verifying:
   - Total parent strands across modifiers >= 10,000 (assert >= 12,000).
   - Total evaluated render strands >= 100,000.
   - Zero-fur masking: assert that 100% of vertices in `ZERO_FUR_GROUPS` (`snout`, `nostrils`, `mouth_cavity`, `teeth`, `eyes`, `eyelids`, `claws_front`, `claws_hind`, `pads_front`, `pads_hind`) have weight == 0.0 in `Fur_Density`.
   - Spine flow alignment: assert average spine tangent points caudally along spine ($t_y > 0.60$).
   - Ribbon mesh: assert quad polygons > 0, vertices > 0, and UVMap layer exists with valid UVs in [0, 1].
2. Stress-test random scaling and custom parameters.
3. Deliver report and verdict (`APPROVE` or `REJECT`) in `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_m2_1/handoff.md` and message orchestrator.

## 2026-09-05T16:34:56Z
You are Challenger M2-1 for Milestone M2.
Your working directory is `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_m2_1`.
Read your dispatch at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_m2_1/DISPATCH.md`, `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`, `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`, and Worker M2's handoff at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m2/handoff.md`.

Perform adversarial verification in headless Blender 5.2.1 LTS:
1. Assert total parent strands across modifiers >= 10,000 (verify >= 12,000) and render strands >= 100,000.
2. Assert 0.0 fur density on naked features (`snout`, `nostrils`, `mouth_cavity`, `teeth`, `eyes`, `eyelids`, `claws_front`, `claws_hind`, `pads_front`, `pads_hind`).
3. Assert biological flow alignment along dorsal spine ($t_y > 0.60$).
4. Assert ribbon mesh has valid polygons and UV coordinates in [0, 1].
Deliver your verdict (APPROVE or REJECT) in `handoff.md` and message orchestrator.

## 2026-09-07T04:46:35Z
You are Challenger M2_1: Camera Mathematics & Geometric Stress Challenger for Milestone 2.
Your working directory is: e:\tool\mcp\MorphoMesh\.agents\challenger_m2_1
Your parent orchestrator conversation ID is: 577aaa33-6b3f-4ebc-93eb-fcc632d94bc9
The authoritative user request is at: e:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md (specifically § 2026-09-07T03:34:32Z). You MUST read this file first.
The project scope document is at: e:\tool\mcp\MorphoMesh\PROJECT.md (specifically Milestone 2).
The Worker M2 handoff report is at: e:\tool\mcp\MorphoMesh\.agents\worker_m2\handoff.md.

Objective:
Empirically stress-test the camera math, bounding box solver, and framing algorithms:
- Write and execute an adversarial test harness in your working directory (`tests/test_adversarial_camera_math.py` or local runner) testing:
  1. Degenerate and edge-case geometries:
     - Single-vertex mesh, zero-volume mesh (flat 2D plane in XY, YZ, ZX).
     - Vast scale discrepancies (microscopic bounding box 1e-6, gigantic bounding box 1e6).
     - Extreme aspect ratios (e.g. 1000:1 pencil needle mesh).
  2. Gimbal lock and polar singularities:
     - Elevation phi = +90 degrees (zenith / top-down view).
     - Elevation phi = -90 degrees (nadir / bottom-up view).
     - Azimuth theta = 0, 90, 180, 270, 360, -720 degrees.
     - Verify camera quaternion is normalized, finite, and non-NaN.
  3. Frustum containment verification:
     - For every canonical viewpoint and a 360-degree turntable sweep (every 15 degrees), verify that every vertex of the bounding sphere projects strictly inside the normalized camera frustum [-1, 1] x [-1, 1] without clipping.
  4. Extreme camera parameters:
     - Extreme focal lengths (f = 5mm fisheye to f = 800mm super-telephoto).
     - Extreme sensor aspect ratios (32:9 ultra-wide, 9:16 vertical mobile portrait, 1:1 square).
- Run your tests, inspect results, and issue an empirical verdict: APPROVE or REJECT.
- Write your handoff report to `e:\tool\mcp\MorphoMesh\.agents\challenger_m2_1\handoff.md` and notify parent orchestrator via send_message.

