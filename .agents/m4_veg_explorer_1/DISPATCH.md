## 2026-09-10T06:41:39Z
You are Explorer 1 for Milestone 4 (M4: Automated Inspection Suite & Preview Visuals).
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_1
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\ORIGINAL_REQUEST.md
Also refer to:
- Root User Request: E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md
- Project Specification: E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_1\PROJECT.md
- Catalog: teamwork_projects/vegetation_library/vegetation_pipeline/catalog.py
- Generator: teamwork_projects/vegetation_library/vegetation_pipeline/generator.py
- Post Processor: teamwork_projects/vegetation_library/vegetation_pipeline/post_processor.py

Mission:
Investigate and design the software architecture, algorithms, and validation rules for `teamwork_projects/vegetation_library/vegetation_pipeline/validator.py`.

Scope of Investigation:
1. Detailed Geometric Validation Algorithms:
   - Pure Python / numpy binary GLB parser to extract and decode vertex buffer accessors (POSITION, NORMAL, TEXCOORD_0, INDICES).
   - Zero NaN / Inf assertions across all vertex coordinates.
   - Vertex count budget: strictly assert 3,000 <= N_verts <= 45,000.
   - Normal vector validation: all normals must be finite, non-zero length, and unit normalized (||n|| == 1.0 +/- 0.05).
   - Non-degenerate faces check: triangles/quads must not have zero area or duplicate vertex indices.
   - Ground contact base alignment: root base Z_min == 0.000m +/- 0.005m (in Blender convention) / Y_min == 0.000m +/- 0.005m (in glTF coordinate convention).
   - Base contact centroid centering: centroid of bottom 5% height slice is centered at (0, 0) +/- 0.05m.
   - Metric scale bounds: bounding box height matches catalog target height within +/- 10%.
2. Static Mesh Invariant Validation:
   - GLB binary inspection: parse JSON chunk, strictly assert `skins` is None/omitted or empty `[]`, `animations` is None/omitted or empty `[]`, and zero primitive attributes contain `JOINTS_0` or `WEIGHTS_0`.
   - OBJ inspection: parse companion `.obj` file, assert absence of bone groups or skinning directives.
   - Verify N_bones == 0 strictly.
3. PBR Texture Completeness & Physical Plausibility Validation:
   - Inspect directory `textures/` and embedded GLB images.
   - Verify 4 required channels: `albedo.png`, `normal.png`, `roughness.png`, `metallic.png`.
   - Verify all are readable non-empty PNG images with non-zero dimensions (e.g. 512x512).
   - Verify Albedo: non-solid black (mean pixel value > 0.05, standard deviation > 0.02).
   - Verify Normal map: valid tangent space normal distribution (Z-component in [0.5, 1.0], vector magnitude ~= 1.0).
   - Verify Roughness: realistic organic roughness distribution (mean in [0.2, 0.95], std > 0.01).
   - Verify Metallic: dielectric vegetation material enforcement (metallic pixel values <= 0.05, mean <= 0.02).
4. Data Model and Entry Points:
   - `ValidationReport` Pydantic model:
     - `is_valid: bool`, `species_id: str`, `category: str`, `checks: Dict[str, bool]`, `metrics: Dict[str, Any]`, `errors: List[str]`, `warnings: List[str]`.
   - Functions:
     - `validate_asset(asset: Union[ExportedAsset, Path], catalog: Optional[VegetationCatalog] = None) -> ValidationReport`
     - `validate_directory(output_dir: Path, catalog: Optional[VegetationCatalog] = None) -> Dict[str, ValidationReport]`
5. Formulate precise implementation specifications and code templates for the Worker.
