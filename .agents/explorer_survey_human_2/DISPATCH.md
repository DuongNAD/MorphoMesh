## 2026-09-06T17:38:00Z
You are Explorer 2 (Anatomy, Rigify 163 DEF Bones & FACS Blendshapes Explorer).
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\explorer_survey_human_2
Your parent is orchestrator_human_1 (conversation ID: fa73b7ae-2239-4440-89d0-f3a69497b7b7).
Path to ORIGINAL_REQUEST.md: E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md

MISSION:
Investigate parametric human female mesh generation, Rigify Human Metarig integration with 163 DEF bones, vertex weighting without pinching, and the complete 52 ARKit FACS facial blendshapes specification.

INSTRUCTIONS:
1. First, read E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md in its entirety.
2. Investigate procedural/parametric female human anatomy generation:
   - Anatomical proportions (height, head ratio 1:7.5 to 1:8, shoulder-to-hip proportions, waist-to-hip ratio).
   - Mesh topology: quad-dominant (>=95% quads in deforming regions), manifold geometry, correct outwards normals, edge loops around eyes, mouth, nasolabial folds, shoulders, elbows, knees.
   - Hands with 5 articulated fingers each (thumb + 4 fingers, 3 phalanges each), articulated feet.
3. Investigate Rigify Human Metarig integration in Blender:
   - The exact bone structure of Rigify Human metarig that produces 163 DEF bones (DEF-spine.*, DEF-head, DEF-jaw, DEF-upper_arm.*, DEF-forearm.*, DEF-hand.*, DEF-finger_*.*, DEF-thigh.*, DEF-shin.*, DEF-foot.*, face DEF bones, etc.).
   - Automated landmark alignment algorithms to snap bone heads/tails to human mesh vertices.
   - Rigify generation script / bpy commands in Blender 4.5+ (`bpy.ops.pose.rigify_generate()` or programmatic generation).
   - Vertex weighting and skinning strategies to ensure clean articulation (no collapsing/pinching at shoulders, elbows, knees).
4. Investigate the 52 ARKit FACS Facial Blendshapes / Shape Keys:
   - Exact standard naming convention (e.g. eyeBlinkLeft, eyeLookDownLeft, jawOpen, mouthSmileLeft, etc.).
   - Specific vertex deformation targets on the face mesh for all 52 shapes.
   - How to programmatically generate and store these shape keys on the Blender mesh.
5. Write your comprehensive technical report to:
   E:\tool\mcp\MorphoMesh\.agents\explorer_survey_human_2\handoff.md
6. Update your progress.md and send a message back to orchestrator_human_1 when finished.
