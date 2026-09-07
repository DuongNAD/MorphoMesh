## 2026-09-07T04:31:50Z
You are Explorer M2_1: Camera Mathematics & Framing Algorithm Explorer.
Your working directory is: e:\tool\mcp\MorphoMesh\.agents\explorer_m2_1
Your parent orchestrator conversation ID is: 577aaa33-6b3f-4ebc-93eb-fcc632d94bc9
The authoritative user request is at: e:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md (specifically § 2026-09-07T03:34:32Z). You MUST read this file first.
The project scope document is at: e:\tool\mcp\MorphoMesh\PROJECT.md (specifically Milestone 2).

Objective:
Detail the exact implementation blueprint for src/morphomesh/camera_rig.py (new module):
1. Hierarchical World Bounding Box Solver:
   - Calculate world-space AABB across multi-mesh character hierarchies using evaluated depsgraph and matrix_world.
   - Return (center, radius, min_corner, max_corner).
2. Optical Framing Distance Derivation:
   - Calculate exact framing distance d = (R / sin(alpha_min)) * (1 + margin) where alpha_min = min(FOV_h, FOV_v)/2 and margin ˜ 0.15.
   - Account for focal length (mm), sensor width/height, and render resolution aspect ratio.
3. 5 Anatomical Sub-Region Framing Centers:
   - Full Body: geometric center C, radius R
   - Head/Portrait: top 15-20% height or head vertex group, f=85mm
   - Torso/Bodice: mid-torso center, f=70mm
   - Hands/Marionette: hand bone landmarks or lateral offset, f=85mm
   - Feet/Sandals: ground-level center, f=70mm
4. Spherical Orbit Viewpoints:
   - Spherical coordinates P_cam(theta, phi, d) with D.to_track_quat('-Z', 'Y') for:
     ront (0, 0), side (90, 0), ack (180, 0), 	hree_quarter (45, 15), close_up_head, close_up_hands, and 	urntable_4views.
5. Camera Creation and Management in Blender:
   - Dedicated camera object MorphoMesh_Inspector_Camera without deleting user cameras.

Scope boundaries: Read-only exploration. DO NOT edit or create any source code files.
Write your report to e:\tool\mcp\MorphoMesh\.agents\explorer_m2_1\handoff.md and notify your parent orchestrator via send_message.
