# Handoff Report: Vegetation Library Asset Pipeline, Normalization, Rendering & Viewer Survey

**Author**: Explorer Survey 2 (Asset Pipeline & Viewer Explorer)  
**Date**: 2026-09-10T11:18:00Z  
**Target Repository**: `teamwork_projects/vegetation_library`  
**Parent Agent**: `c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4`

---

## 1. Observation

### 1.1 Architecture & File Layout
The vegetation library asset pipeline is situated in `teamwork_projects/vegetation_library/` and comprises:
- `vegetation_pipeline/catalog.py` (16.9 KB, 438 lines): Defines 35 botanical species across 7 categories (`PlantSpecies`, `VegetationCatalog`).
- `vegetation_pipeline/generator.py` (68.3 KB, 1,523 lines): Implements `MeshyGenerator` (two-stage preview + refine API client), `ProceduralBotanicalGenerator` (offline procedural fallback), and `generate_plant()`.
- `vegetation_pipeline/post_processor.py` (43.8 KB, 1,049 lines): Implements `AssetPostProcessor`, metric scale normalization, ground contact pivot snapping, base contact centroid centering, production GLB binary export, companion OBJ/MTL export, and `asset_manifest.json` generation.
- `vegetation_pipeline/renderer.py` (36.0 KB, 912 lines): Implements headless Blender 4.5.4 LTS automation, 4-angle turntable renders (`turntable_01.png` - `04.png`), 1024x1024 2x2 contact sheet montage (`thumbnail.png`), and pure-Python software rasterizer fallback.
- `vegetation_pipeline/validator.py` (42.7 KB, 1,043 lines): Automated structural, geometric, static mesh, and 4-channel PBR texture validation suite (`validate_asset`, `validate_directory`).
- `pipeline.py` (30.8 KB, 795 lines): Master CLI orchestrator with `--species`, `--category`, `--all`, `--mode [auto|meshy|procedural]`, `--summary`, and manifest aggregator (`aggregate_manifest`).
- `output/manifest.json` (143.3 KB, 4,249 lines): Global catalog manifest indexing all 35 species deliverables.
- `viewer.html` (48.5 KB, 1,088 lines): Interactive browser dashboard displaying plant cards, search/filter, and modal previews.
- Test suites in `tests/`: `test_catalog.py`, `test_generator.py`, `test_normalization.py`, `test_renderer.py`, `test_validator.py`, `test_vegetation_pipeline.py`.

### 1.2 GLB Post-Processing & Normalization Implementation
Direct inspection of `vegetation_pipeline/post_processor.py` reveals the exact mathematical and algorithmic implementation:

1. **Ground Pivot Snapping (`snap_ground_pivot_and_center()`, lines 291-338)**:
   ```python
   # Line 316-317: Ground contact shift
   min_z = min(zs)
   mesh.vertices = [(v[0], v[1], v[2] - min_z) for v in mesh.vertices]
   ...
   # Line 333-335: Numerical precision clamp to guarantee Z_min = 0.000m
   final_min_z = min(v[2] for v in mesh.vertices)
   if abs(final_min_z) > 1e-7:
       mesh.vertices = [(v[0], v[1], v[2] - final_min_z) for v in mesh.vertices]
   ```
   *Behavior*: Calculates $z_{\min} = \min_{v \in V} v_z$, translates all vertices by $-z_{\min}$, then applies a second precision clamp ($|z_{\min}| > 10^{-7}$). This strictly enforces $Z_{\min} = 0.000\text{m} \pm 0.005\text{m}$ (in practice $\le 10^{-7}\text{m}$).

2. **Base Contact Centroid Centering (`snap_ground_pivot_and_center()`, lines 319-330)**:
   ```python
   # Line 320-328: Base slice centroid calculation
   current_h = max(v[2] for v in mesh.vertices)
   slice_h = max(1e-4, base_slice_ratio * current_h)  # base_slice_ratio = 0.05
   base_verts = [v for v in mesh.vertices if v[2] <= slice_h]
   cx = float(np.mean([v[0] for v in base_verts]))
   cy = float(np.mean([v[1] for v in base_verts]))
   # Line 330: Base centering translation
   mesh.vertices = [(v[0] - cx, v[1] - cy, v[2]) for v in mesh.vertices]
   ```
   *Behavior*: Evaluates the bottom 5% height slice ($z \le 0.05 H$), calculates horizontal centroid $(c_x, c_y)$, and translates $v_x \leftarrow v_x - c_x, v_y \leftarrow v_y - c_y$. This aligns the biological trunk base / root collar to $(0.000, 0.000)$, rather than the overall crown center, properly handling leaning trees and asymmetric canopies.

3. **Metric Scale Normalization (`normalize_metric_scale()`, lines 340-409)**:
   ```python
   # Line 362-365:
   scale_z = target_h / curr_h
   if strategy in ("uniform_height", "height_proportional"):
       scale_x = scale_y = scale_z
   ```
   *Behavior*: Uniformly scales mesh by $s = H_{\text{target}} / H_{\text{measured}}$, where $H_{\text{target}}$ comes from `PlantSpecies.dimensions.height_m`. Preserves aspect ratio, trunk circularity, and avoids normal warping. Normal vectors are unit re-normalized (lines 390-405).

4. **Production GLB Binary Export (`export_production_glb()`, lines 430-610)**:
   - Packs positions, normals, UVs, indices, and 5 texture image buffers (`albedo`, `metallicRoughness` ORM, `normal`, `roughness`, `metallic`) into glTF 2.0 binary chunks with 4-byte null padding (`pad_4`, line 159).
   - Sets `materials[0].doubleSided = True` (line 552) for two-sided foliage rendering.
   - Strictly omits `skins`, `animations`, and skeletal node hierarchies ($N_{\text{bones}} = 0$).

5. **Companion Wavefront OBJ & MTL Export (`export_companion_obj_mtl()`, lines 613-682)**:
   - Saves discrete PNG maps to `<species_dir>/textures/` (`albedo.png`, `normal.png`, `roughness.png`, `metallic.png`).
   - Writes 1-indexed `.obj` geometry and `.mtl` material file linking to `textures/` via relative paths.

### 1.3 Blender Headless Rendering Implementation
Direct inspection of `vegetation_pipeline/renderer.py` confirms:
1. **Binary Detection (`resolve_blender_binary()`, lines 184-211)**:
   - Checks explicit override, `BLENDER_BIN_PATH`, `BLENDER_PATH`, `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`, `PATH`.
   - On this machine, Blender 4.5.4 LTS is present at `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe` (verified via `blender --version`).
2. **Subprocess Invocation (`render_blender_headless()`, lines 712-760)**:
   - Invokes: `subprocess.run([blender_path, "--background", "--factory-startup", "--python", script_path, "--", ...])`.
   - Executes embedded Python script (`BLENDER_RENDER_SCRIPT_CODE`, lines 218-409).
3. **Lighting, Cameras & 4 Turntable Angles (`BLENDER_RENDER_SCRIPT_CODE`, lines 349-406)**:
   - Sets up transparent film (`film_transparent = True`), sRGB display, AgX view transform.
   - Ground contact shadow catcher plane at $Z = z_{\min} = 0.000\text{m}$.
   - 3-point botanical studio lighting: Key Sun (5500K, 4.5 energy, 45°/15°/45°), Fill Sun (6500K, 1.8 energy, 45°/-20°/-110°), Rim Sun (3.0 energy, edge translucency).
   - Auto-framing optical camera distance: $d = \frac{R}{\sin(\alpha)} \cdot (1 + \text{margin})$ with focal length 50mm and 15% margin padding.
   - 4 standardized angles:
     * `turntable_01.png`: Hero 3/4 view (elevation 25°, azimuth 45°)
     * `turntable_02.png`: Front elevation view (elevation 0°, azimuth 0°)
     * `turntable_03.png`: Side elevation view (elevation 0°, azimuth 90°)
     * `turntable_04.png`: Top-down crown view (elevation 85°, azimuth 0°)
4. **Contact Sheet Montage (`render_contact_sheet()`, lines 416-574)**:
   - Pure-Python PIL compositor creating a 1024x1024 2x2 grid `thumbnail.png`.
   - Header banner: botanical common name, italic scientific name, category, metric height, polygon count.
   - Viewpoint badge pills: "1. HERO 3/4", "2. FRONT ELEVATION", "3. SIDE ELEVATION", "4. TOP CROWN".
   - QC footer bar: "MorphoMesh QC Verified • Zero Armatures (N_bones=0) • Ground Pivot Z_min = 0.000m • Real-Time PBR".
5. **Software Rasterizer Fallback (`render_software_fallback()`, lines 580-685)**:
   - Pure-Python / NumPy / PIL orthographic depth-sorted polygon rasterizer ensuring pipeline never crashes if Blender is absent.

### 1.4 Manifest Structure & Current State
1. **Global Manifest (`output/manifest.json`)**:
   - Contains top-level schema metadata (`schema_version: "1.0.0"`, `total_catalog_species: 35`, `indexed_species_count: 35`, `categories_summary` for all 7 biomes).
   - Asset entries contain: `species_id`, `common_name`, `scientific_name`, `family`, `category`, `category_id`, `biome`, `dimensions`, `geometry` (`vertex_count`, `face_count`), `files`, `validation` (20 check flags + metrics), `source`, `status`, `execution_time_s`.
2. **Current Provenance Discrepancy Across the 35 Assets**:
   An automated audit of all 35 GLB files in `output/` reveals:
   - Exactly **1 asset** (`veg_tree_oak_01`) is genuine Meshy: `src: meshy`, `task_id: 01a089f7-2837-7074-af0e-89c25070c634`, 58,853 vertices, 59,487 faces.
   - **34 assets** are procedural fallbacks (`src: procedural`), with identical clone vertex counts within categories:
     * Broadleaf (4 species): identical 4,320 verts, 4,238 faces.
     * Conifers (5 species): identical 5,024 verts, 4,850 faces.
     * Groundcover (5 species): identical 3,656 verts, 1,872 faces.
     * Shrubs (5 species): identical 4,552 verts, 3,580 faces.
     * Succulents (5 species): identical 3,336 verts, 3,932 faces.
     * Tropical (5 species): identical 3,960 verts, 2,442 faces.
     * Vines (5 species): identical 4,064 verts, 3,280 faces.
   - Furthermore, `output/manifest.json` was generated *before* `veg_tree_oak_01` was updated with Meshy AI, so `output/manifest.json` still records oak as `source: "auto"`, `vertex_count: 4320`!

### 1.5 Viewer Implementation (`viewer.html`)
1. **Data Loading**:
   - `viewer.html` does **not** dynamically fetch `output/manifest.json`.
   - Data is hardcoded in-line inside `<script>`: `const categories = [...]` and `const plants = [...]` (lines 224-961).
   - Line 1003 contains hardcoded badge: `${p.id === 'veg_tree_oak_01' ? '<span class="... bg-emerald-600 ...">Meshy AI 3D</span>' : ''}`.
   - Lines 80-138 contains a static hero comparison section highlighting Meshy AI Oak vs Procedural fallback.
2. **3D Preview Engine**:
   - `viewer.html` uses **neither** Three.js nor `<model-viewer>`.
   - Cards display the 2D contact sheet `thumbnail.png`.
   - Clicking a card opens `plantModal`, displaying `thumbnail.png`, the 4 turntable PNGs (`turntable_01.png` - `04.png`), and download links for GLB and OBJ.
   - There is no interactive WebGL canvas allowing real-time 3D rotation in the browser.

### 1.6 Pipeline Test Suite & Critical Edge Cases
Running `uv run pytest teamwork_projects/vegetation_library/tests/ -v` yielded 249 passed, 6 failed:
1. `test_geometry_standards_all_species`: Fails on `veg_tree_oak_01` because its vertex count is 58,853, exceeding the old test budget assertion `3000 <= V <= 45000` (`test_vegetation_pipeline.py:225`).
2. `test_pbr_material_standards_all_species`: Fails on `veg_tree_oak_01` because `textures/albedo.png` has spatial standard deviation `0.00032 <= 0.02` (it is a solid flat green `(45, 95, 35)`).
   *Root Cause*: In `post_processor.py:extract_textures_from_glb()`, image extraction checks `if "albedo" in name:`. However, Meshy AI GLB containers emit image dictionaries without a `name` key (`[{'mimeType': 'image/jpeg', 'bufferView': 4}, ...]`). The texture extractor failed to find images by material binding, so `post_processor.py:840` fell back to synthetic solid green `(45, 95, 35)`.
3. `test_full_inspection_suite_100_percent_pass`: Fails because `validate_directory()` found `raw_meshy_model.glb` before `veg_tree_oak_01.glb` (alphabetical sort in `target_path.glob("*.glb")`), evaluating un-normalized coordinates ($Y_{\min} = -0.951\text{m}$, height $1.879\text{m}$) instead of the normalized file.
4. `test_cli_summary_mode_execution`: Fails on Windows due to `UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d` when `subprocess.run(..., text=True)` decodes UTF-8 stdout using default Windows code page `cp1252`.

---

## 2. Logic Chain

1. **User Objective**:
   The user request under `## 2026-09-10T11:11:31Z` requires rebuilding the entire 35-species library using 100% genuine Meshy AI cloud API generation, eliminating identical clone geometry and procedural fallbacks, reaching 20,000 to 60,000 polygons per asset, 4-channel PBR materials, ground contact $Z_{\min} = 0.000\text{m} \pm 0.005\text{m}$, re-rendering all 4-angle turntables and contact sheets with headless Blender, updating `manifest.json`, and synchronizing `viewer.html`.

2. **Current Pipeline State**:
   - The normalization logic in `post_processor.py` (`snap_ground_pivot_and_center()` and `normalize_metric_scale()`) is mathematically sound and conforms to all geometric constraints.
   - The rendering logic in `renderer.py` is fully functional with Blender 4.5.4 LTS.
   - However, 34 out of 35 assets are still procedural dummy clones because they were generated during offline development.
   - Exactly one asset (`veg_tree_oak_01`) was generated with Meshy AI, serving as an empirical benchmark.

3. **Required Upgrades for Generation & Normalization**:
   - **Texture Extraction Bug in `post_processor.py`**: When Meshy AI GLBs omit image names, the extractor must follow glTF material bindings:
     `material.pbrMetallicRoughness.baseColorTexture.index` $\rightarrow$ `textures[index].source` $\rightarrow$ `images[source]`.
     This will preserve the authentic high-resolution PBR textures generated by Meshy rather than falling back to solid green.
   - **Validator GLB Selection**: In `validator.py:835`, `target_path.glob("*.glb")` must prioritize `target_path / f"{species_id}.glb"` over auxiliary files like `raw_meshy_model.glb`.
   - **Vertex Budget Expansion**: Both `validator.py:382` and `test_vegetation_pipeline.py:225` must update the upper vertex/face budget from 45,000 to 60,000 (or 65,000) to reflect genuine Meshy AI high-detail models.
   - **Windows CLI Encoding**: In `pipeline.py` and `test_vegetation_pipeline.py:374`, subprocess execution of `--summary` must specify `encoding="utf-8", errors="replace"` to prevent Windows `cp1252` charmap crashes.

4. **Required Upgrades for `viewer.html`**:
   - Currently, `viewer.html` has hardcoded procedural stats and static 2D image previews.
   - To synchronize with genuine Meshy models, `viewer.html` should either:
     a. Fetch `output/manifest.json` dynamically via JavaScript `fetch()`, or
     b. Be updated via an automated synchronization script (`scripts/sync_viewer.py` or a method in `pipeline.py`) that reads `output/manifest.json` and embeds the genuine metadata, polygon counts, and thumbnails.
   - To provide true 3D interactive viewing, integrate Google `<model-viewer>` (`@google/model-viewer`) in the modal popup, allowing users to spin, zoom, inspect wireframe, and toggle lighting on the genuine `.glb` models directly in the browser.

---

## 3. Caveats

1. **Meshy AI Rate Limits & Cost**: Generating 34 new species via Meshy AI Text-to-3D requires 34 Stage 1 previews and 34 Stage 2 refines (68 API tasks). The exponential backoff in `generator.py` is essential to handle concurrent task limits (typically 2-4 concurrent tasks per account).
2. **Offline Testing Fallback**: Unit tests running in CI without a live `MESHY_API_KEY` must continue to support mock or cached assets, so `ProceduralBotanicalGenerator` must remain intact as a fallback when explicitly requested.
3. **CORS on `file://` for `viewer.html`**: If a user opens `viewer.html` directly from Windows Explorer (`file:///E:/.../viewer.html`), modern browsers block `fetch("output/manifest.json")` due to local file CORS restrictions. Therefore, embedding the synchronized JSON into `viewer.html` (or providing both a local server script `python -m http.server` and an embedded fallback) ensures the viewer works in all environments.

---

## 4. Conclusion

The botanical asset pipeline architecture in `teamwork_projects/vegetation_library` is robust, modular, and ready for full-scale generation. Scale normalization, ground pivot snapping ($Z_{\min} = 0.000\text{m} \pm 0.005\text{m}$), and base centroid centering ($X=0, Y=0$) are already implemented in `post_processor.py`. Blender 4.5.4 LTS is fully operational for 4-angle turntable renders and contact sheets.

To fulfill the user request under `## 2026-09-10T11:11:31Z`, the following sequential actions are recommended:
1. **Fix GLB Texture Extraction in `post_processor.py`**: Resolve glTF images via material texture indices so Meshy PBR textures are cleanly extracted and embedded without falling back to flat colors.
2. **Update Vertex Budget in `validator.py` and `tests/`**: Increase max budget from 45,000 to 60,000 faces/vertices.
3. **Fix Validator File Resolution in `validator.py`**: Explicitly target `{species_id}.glb` to avoid misidentifying `raw_meshy_model.glb`.
4. **Execute Meshy Generation for All 35 Species**: Run `pipeline.py --all --mode meshy` using the live API key.
5. **Re-Render Turntables & Contact Sheets**: Run headless Blender to generate authentic multi-angle renders.
6. **Aggregate Manifest**: Run `pipeline.py --validate-only` to update `output/manifest.json` with genuine Meshy task IDs and face counts.
7. **Synchronize `viewer.html`**: Update plant records with genuine metrics and embed `<model-viewer>` for real-time 3D viewing.

---

## 5. Verification Method

To independently verify these findings, run the following commands in powershell:

1. **Verify Blender 4.5.4 LTS Installation**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --version
   ```
2. **Verify Current Meshy vs Procedural Counts Across All 35 Species**:
   ```powershell
   uv run python -c "
   import json
   from pathlib import Path
   from vegetation_pipeline.generator import parse_glb_vertex_and_face_counts
   output_dir = Path('teamwork_projects/vegetation_library/output')
   for m in sorted(output_dir.glob('*/*/asset_manifest.json')):
       sp_id = m.parent.name
       glb = m.parent / f'{sp_id}.glb'
       v, f = parse_glb_vertex_and_face_counts(glb)
       with open(m, 'r') as fp: data = json.load(fp)
       src = data.get('provenance', {}).get('source')
       task = data.get('provenance', {}).get('generator_metadata', {}).get('task_id', 'N/A')
       print(f'{sp_id:30s} | {src:10s} | task: {task} | v: {v:5d}, f: {f:5d}')
   "
   ```
3. **Run Existing Test Suite to Observe the 6 Edge Cases**:
   ```powershell
   uv run pytest teamwork_projects/vegetation_library/tests/ -v
   ```
4. **Inspect `post_processor.py` Normalization Functions**:
   Inspect `vegetation_pipeline/post_processor.py` at lines 291-338 (`snap_ground_pivot_and_center`) and lines 340-409 (`normalize_metric_scale`).
5. **Inspect `viewer.html` Structure**:
   Inspect lines 224-250 and lines 995-1020 of `teamwork_projects/vegetation_library/viewer.html` to confirm hardcoded data and lack of WebGL 3D canvas.
