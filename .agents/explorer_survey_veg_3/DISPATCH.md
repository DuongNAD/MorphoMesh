# Task Assignment: Explorer 3 (Survey - 3D Processing, Unrigged Static Mesh, Export & Verification)
Working Directory: E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_3
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\ORIGINAL_REQUEST.md

## 2026-09-10T05:07:12Z
<USER_REQUEST>
You are Explorer 3 for the Vegetation Library project Survey phase.
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_3
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\ORIGINAL_REQUEST.md
Also refer to: E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md

Mission:
Investigate 3D asset processing, topology optimization, PBR materials, unrigged static mesh guarantees, pivot normalization, export formats, and automated verification suites.

Scope of Investigation:
1. Static Mesh Enforcement: How to programmatically inspect and guarantee that generated assets have ZERO armature bones, bone weights, skinning clusters, or skeletal data in GLB and OBJ formats.
2. Pivot & Normalization: Methods to compute bounding boxes, calculate ground contact base (Z_min = 0 or Y_min = 0 depending on coordinate convention, standardizing on Z-up / Y-up as glTF requires Y-up while Blender uses Z-up), and set object pivot strictly at root base.
3. Topology & Polycount: Ensuring clean geometry within the 3,000 to 45,000 vertex range, checking for manifold geometry, non-degenerate faces, valid vertex normals, and zero NaN/Inf coordinates.
4. PBR Texture Completeness: Required PBR maps (BaseColor/Albedo, Normal, Roughness, Metallic/Specular), verifying valid image files (PNG/JPEG), dimensions, channel assignments, and confirming non-black / non-corrupt textures.
5. Export & Visual Showcase: Production GLB packaging with embedded textures, companion OBJ/MTL, and generating multi-angle turntable / thumbnail renders (e.g., via headless Blender or software OpenGL / trimesh / matplotlib / pyrender).
6. Quality Assurance Suite: Requirements for an automated verification test suite (e.g. test_vegetation_pipeline.py) that asserts 100% compliance across all acceptance criteria.

Rules:
- Read-only exploration. DO NOT write or modify source code files.
- Maintain your progress.md in your working directory E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_3\progress.md.
- Write a comprehensive, structured handoff report to E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_3\handoff.md.
- When finished, send a completion message back to parent.
</USER_REQUEST>
