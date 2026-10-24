## 2026-09-10T05:06:09Z

You are the Project Orchestrator for the Vegetation Library project.

Working Directory: E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_1
Project Directory: E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library
Authoritative User Request: E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md and E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\ORIGINAL_REQUEST.md

Mission:
Build an end-to-end automated generation pipeline and high-fidelity 3D botanical asset library using Meshy AI Text-to-3D, producing 30+ diverse, unrigged plant species across major biomes with complete PBR materials and clean quad topology.

Integrity mode: development

Requirements:
- R1. Comprehensive Botanical Taxonomy & Catalog Specification:
  Structured botanical catalog covering at least 30 distinct plant species across >= 6 major categories:
  1. Broadleaf & Deciduous Trees (e.g., Oak, Maple, Birch, Willow)
  2. Conifers & Evergreens (e.g., Pine, Spruce, Cypress)
  3. Tropical Foliage & Palms (e.g., Fan Palm, Monstera, Banana Plant, Fern Tree)
  4. Flowering Shrubs & Ornamental Plants (e.g., Rose Bush, Hydrangea, Lavender)
  5. Ferns, Grasses & Groundcover (e.g., Boston Fern, Tall Pampas Grass, Forest Moss clump)
  6. Succulents & Cacti (e.g., Saguaro Cactus, Aloe Vera, Echeveria)
  7. Climbing Vines & Epiphytes (e.g., English Ivy, Wisteria)
  Each catalog item must specify scientific name, common name, morphological characteristics, and tuned botanical prompts (canopy shape, leaf clustering, trunk texture, floral accents).

- R2. Meshy AI Text-to-3D Botanical Generation Engine:
  Implement an automated generation harness leveraging Meshy AI Text-to-3D:
  - Structured botanical prompt conditioning optimized for natural vegetation structure.
  - Enable full 4-channel PBR material generation (Albedo/BaseColor, Normal map, Roughness map, and Metallic/Specular).
  - Remesh to clean quad/triangle topology (target ~15,000 – 30,000 polygons per asset) optimized for real-time rendering.
  - Explicitly enforce static mesh generation with ZERO skeletal armatures or rigging weights (plants do not require bones or skinning).
  - Robust rate limiting, retry backoff, task polling, and offline deterministic fallback for headless or rate-limited environments.

- R3. Asset Post-Processing, Normalization & Multi-Format Export:
  Process and normalize all generated botanical models:
  - Set object pivot/origin strictly at the ground contact base (Z=0 / Y=0 at root base).
  - Normalize real-world metric scales (e.g., trees 4-12m, shrubs 1-2m, small plants 0.2-0.8m).
  - Export production-ready GLB (glTF binary with embedded PBR textures) and companion OBJ/MTL formats.
  - Organize assets into categorized directory hierarchies with metadata manifests (`manifest.json`).

- R4. Automated Quality Verification & Visual Showcase:
  Provide an automated inspection and validation suite:
  - Programmatically verify geometry integrity (manifold faces, valid normals, zero NaN/Inf coordinates).
  - Programmatically verify absence of bone armatures or skeletal data.
  - Programmatically verify texture completeness (valid resolution, correct channel assignments).
  - Generate multi-angle preview contact sheets and high-resolution thumbnail renders (isometric/turntable) for all 30+ species.

Acceptance Criteria:
- Catalog manifest defines >= 30 distinct species across at least 6 botanical categories.
- All 30+ species are generated and exported in valid `.glb` format with accompanying metadata.
- Every exported model has pivot point located at the root/base (Z_min ≈ 0 within tolerance).
- Every exported model contains ZERO armature bones, bone weights, or skinning structures.
- Geometry vertex count is between 3,000 and 45,000 vertices per asset with zero NaN/Inf coordinates.
- Each asset includes valid PBR texture maps (BaseColor/Albedo, Normal, Roughness) verified to be readable images without corrupt data or solid black placeholders.
- Programmatic test suite (`test_vegetation_pipeline.py` or verification script) passes 100% on all generated assets.
- Visual preview renders (PNG/JPG) exist for every plant model in the library.

Operating Guidelines:
- Decompose the project into clear milestones with specialized subagents (explorers, workers, reviewers, challengers).
- Maintain your `plan.md`, `progress.md`, and `BRIEFING.md` in your working directory `E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_1`.
- Update `progress.md` frequently with milestone status so sentinel crons can track progress.
- When all deliverables are completed and verified, deliver your victory claim back to me via send_message.
