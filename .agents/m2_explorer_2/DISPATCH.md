## 2026-09-10T05:33:25Z
You are Explorer 2 for Milestone 2 (M2: Procedural Botanical Fallback Generator).
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\m2_explorer_2
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\ORIGINAL_REQUEST.md
Also refer to:
- Project Specification: E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_1\PROJECT.md
- Survey Report on 3D Processing: E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_3\handoff.md
- Existing Geometry Utilities: E:\tool\mcp\MorphoMesh\src\morphomesh\geometry\mesh.py, exporters.py, quad_utils.py

Mission:
Investigate and design the offline deterministic procedural botanical fallback generator (`ProceduralBotanicalGenerator`) for `teamwork_projects/vegetation_library/vegetation_pipeline/generator.py`.

Scope of Investigation:
1. Design procedural 3D botanical mesh generation algorithms using MorphoMesh's `MeshGeometry` covering all 7 categories:
   - Broadleaf Trees: trunk + branch nodes + volumetric quad foliage crowns.
   - Conifers: central vertical spire + tiered descending conical needle whorls.
   - Tropical & Palms: curved trunk/pseudostem + radiating compound fronds.
   - Shrubs: multi-stemmed cluster + dense foliage mounds + flower accents.
   - Groundcover & Ferns: rosette fronds / weeping grass tussocks / cushion moss domes.
   - Succulents & Cacti: ribbed columnar stems (Saguaro) + spiraling rosettes (Aloe/Echeveria/Agave) + barrel spheres.
   - Vines: helical stems + cascading leaf planes.
2. Invariants to enforce:
   - STRICT ZERO armatures, bones, skinning weights ($N_{\text{bones}} = 0$).
   - Ground root pivot ($Z_{\min} = 0.0 \pm 0.005$m).
   - Vertex budget: $3,000 \le N_{\text{verts}} \le 45,000$ per asset.
   - 4-channel procedural PBR textures (Albedo, Normal, Roughness, Metallic) generated via `numpy` and `PIL.Image`.
   - Deterministic repeatability using integer seeds.
3. Formulate the exact code blueprints and data flow for the Worker.

Rules:
- Read-only exploration. DO NOT modify source code files.
- Deliver structured handoff report to E:\tool\mcp\MorphoMesh\.agents\m2_explorer_2\handoff.md.
- Send completion message to parent when finished.
