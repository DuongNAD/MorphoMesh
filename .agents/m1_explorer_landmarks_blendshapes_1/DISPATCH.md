# Dispatch for M1 Explorer 3 (Landmarks & Vertex Groups Strategy)

## Mission
Formulate the exact strategy for Milestone M1 (Anatomical Female Base Mold) landmark extraction and vertex group assignment:
1. Extract 70+ anatomical landmark coordinates from `data/templates/makehuman_base.obj` `joint-*` groups via 8-vertex bounding box centroid averaging:
   $$\vec{C}_{\text{joint}} = \frac{1}{8}\sum_{i=1}^8 \vec{v}_i$$
   and transform to Blender coordinates.
2. Map all 24+ standardized vertex groups (`STANDARDIZED_HUMAN_VERTEX_GROUPS`) on the 13,380 vertex clean base mesh.
3. Map or calibrate the 52 Apple ARKit FACS facial blendshapes (`ARKIT_52_BLENDSHAPES`).
4. Ensure full integration with `src/morphomesh/human_rigging.py` for Rigify 163 DEF metarig alignment.

## Input Files
- E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
- E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md
- E:\tool\mcp\MorphoMesh\.agents\survey_explorer_codebase_1\handoff.md
- E:\tool\mcp\MorphoMesh\.agents\survey_explorer_character_pipeline_1\handoff.md
- E:\tool\mcp\MorphoMesh\src\morphomesh\human_generator.py

## Working Directory
E:\tool\mcp\MorphoMesh\.agents\m1_explorer_landmarks_blendshapes_1

## Output File
E:\tool\mcp\MorphoMesh\.agents\m1_explorer_landmarks_blendshapes_1\handoff.md

## 2026-09-07T17:37:33Z
You are M1 Explorer 3 (Landmarks & Vertex Groups Strategy).
Your identity: M1 Explorer 3 (Landmarks & Vertex Groups Strategy).
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\m1_explorer_landmarks_blendshapes_1
You MUST create your own BRIEFING.md and progress.md in your working directory.

MANDATORY FIRST STEP: Read the authoritative user request at:
E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md

Also read your dispatch instructions at:
E:\tool\mcp\MorphoMesh\.agents\m1_explorer_landmarks_blendshapes_1\DISPATCH.md
and the master project specification at:
E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md

Your Mission:
Formulate the landmark extraction, vertex groups, and blendshapes strategy for Milestone M1:
1. Extract 70+ anatomical landmark coordinates from data/templates/makehuman_base.obj joint-* groups via 8-vertex bounding box centroid averaging:
   C_joint = (1/8) * sum(v_i) and transform to Blender coordinates.
2. Map all 24+ standardized vertex groups (STANDARDIZED_HUMAN_VERTEX_GROUPS) on the 13,380 vertex clean base mesh.
3. Map or calibrate the 52 Apple ARKit FACS facial blendshapes (ARKIT_52_BLENDSHAPES).
4. Ensure seamless downstream interface compatibility with src/morphomesh/human_rigging.py for Rigify 163 DEF metarig alignment.

Produce your structured handoff report at:
E:\tool\mcp\MorphoMesh\.agents\m1_explorer_landmarks_blendshapes_1\handoff.md
Notify me via send_message when done.

