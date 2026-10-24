# Project: Vegetation Library Rebuild

## Architecture
The 3D Botanical Asset Library rebuild transforms `teamwork_projects/vegetation_library` into an automated production pipeline producing 100% genuine Meshy AI Text-to-3D botanical assets:
1. **Catalog Subsystem (`vegetation_pipeline/catalog.py`)**:
   - Manages 35 botanical species across 7 biomes.
   - Enforces scientific naming, real-world metric dimensions, and morphological prompt conditioning.
2. **Meshy AI Generation Engine (`vegetation_pipeline/generator.py`)**:
   - Communicates with Meshy OpenAPI v2 (`/openapi/v2/text-to-3d`) using `MESHY_API_KEY`.
   - Two-stage cloud synthesis: Stage 1 Preview (`meshy-6`, quad topology, target polycount) + Stage 2 Refine (`enable_pbr=True`, `texture_richness="high"`).
   - Robust polling, exponential backoff on 429/5xx, and strict prohibition of procedural dummy fallback meshes.
3. **Post-Processing & Normalization Subsystem (`vegetation_pipeline/post_processor.py`)**:
   - Uniform metric scaling $s = H_{\text{target}} / H_{\text{curr}}$ preserving proportions.
   - Ground contact snapping: strictly $Z_{\min} = 0.000\text{m} \pm 0.005\text{m}$.
   - Horizontal base centering: $(X_{\text{base}}, Y_{\text{base}}) \to (0, 0)$.
   - Embedded 4-channel PBR materials (Albedo, Normal, Roughness, Metallic) with double-sided foliage rendering and $N_{\text{bones}} = 0$.
   - Companion Wavefront OBJ/MTL export.
4. **Blender Headless Rendering Subsystem (`vegetation_pipeline/renderer.py`)**:
   - Automated studio rendering via Headless Blender 4.5.
   - 4 turntable angles (`turntable_01.png` - `04.png`) with shadow catcher and AgX color management.
   - 1024x1024 2x2 contact sheet montage (`thumbnail.png`).
5. **Quality Assurance & Validator Subsystem (`vegetation_pipeline/validator.py`)**:
   - Pure Python/NumPy geometry validation (20k-60k polygons, zero NaN/Inf, manifold checks).
   - Static mesh invariant ($N_{\text{bones}} = 0$).
   - Ground snapping verification ($|Z_{\min}| \le 0.005\text{m}$).
   - 4-channel PBR texture physical plausibility ($std > 0.02$ albedo, $std > 0.01$ roughness, dielectric metallic $\le 0.05$).
   - Meshy cloud task provenance verification (`source == "meshy"`, valid `task_id`).
   - Pairwise vertex collision verification (< 5%).
6. **Presentation & Delivery Subsystem**:
   - Master `manifest.json` indexing all 35 species with cloud provenance and geometric metrics.
   - Interactive `viewer.html` showcasing 3D cards, metadata, and preview renders.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | Meshy Cloud Provenance | 100% genuine Meshy AI cloud generation with valid `task_id`, `model_type`, `refine_status` in manifest; 0% procedural fallback | M1, M2 | Survey E1, E3 |
| 2 | Validator Polycount Bounds | Update validator budget to 20,000 - 65,000 polygons/vertices | M1 | Survey E1, E3 |
| 3 | File Discovery Hardening | Select specific `<species_id>.glb` rather than `glob("*.glb")[0]` to avoid unnormalized raw GLBs | M1 | Survey E2, E3 |
| 4 | PBR Texture Extraction Fix | Fix `getattr(extracted, f"{attr}_path")` in `generator.py` and unnamed image handling in `post_processor.py` | M1 | Survey E1, E2, E3 |
| 5 | Windows Subprocess UTF-8 Fix | Explicit UTF-8 decoding for CLI summary and subprocess execution | M1 | Survey E1, E2, E3 |
| 6 | Oak Asset Normalization | Normalize existing genuine Meshy Oak asset to pass all QA checks | M1 | Survey E1, E2, E3 |
| 7 | Species-Specific Prompt Tuning | Distinct morphological prompts for Fan Palm, Monstera, Banana Plant, Tree Fern, Bird of Paradise, Saguaro, Scots Pine, etc. | M2 | Survey E1 |
| 8 | Cloud Batch Generation | Live Meshy AI generation for remaining 34 species with queue polling and exponential backoff | M2 | Survey E1 |
| 9 | Pairwise Vertex Divergence | Enforce pairwise vertex count collision rate < 5% across library | M2, M4 | Survey E3 |
| 10 | Metric Scale Normalization | Scale all assets to botanical targets within $\pm 10\%$ tolerance | M3 | Survey E2 |
| 11 | Ground Pivot Snapping & Centering | Snap $Z_{\min} = 0.000\text{m} \pm 0.005\text{m}$ and center base at $(0, 0)$ | M3 | Survey E2, E3 |
| 12 | Static Mesh Invariant | Strictly zero armature bones ($N_{\text{bones}} = 0$) | M3 | Survey E3 |
| 13 | 4-Channel PBR Materials | Valid Albedo, Normal, Roughness, Metallic textures embedded and exported | M3 | Survey E1, E2, E3 |
| 14 | Headless Blender 4-Angle Turntables | Render `turntable_01.png` - `04.png` via Blender 4.5 background engine | M3 | Survey E2 |
| 15 | Contact Sheet Generation | Generate 1024x1024 2x2 montage `thumbnail.png` | M3 | Survey E2 |
| 16 | Master Manifest Aggregation | Re-aggregate `output/manifest.json` with genuine Meshy metrics and provenance | M4 | Survey E2, E3 |
| 17 | Interactive Viewer Synchronization | Update `viewer.html` cards, thumbnails, and model metrics | M4 | Survey E2 |
| 18 | Automated Test Suite 100% Pass | Pass all unit and E2E acceptance tests with 0 failures | M4 | Survey E3 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | Pipeline & Validator Hardening | Fix validator bounds (20k-65k), fix GLB file discovery, fix PBR texture extraction, fix Windows UTF-8 encoding, normalize Oak asset, achieve 255/255 passing tests | none | DONE |
| 2 | Meshy Cloud Batch Generation & Divergence | Live Meshy AI generation for botanical species, prompt tuning for morphological authenticity, pairwise collision < 5%, zero procedural fallbacks | M1 | IN_PROGRESS (26/35 generated, 9 credit-blocked) |
| 3 | Normalization, Ground Snapping & Headless Rendering | Metric scale normalization, ground snapping $Z_{\min} = 0.000\text{m} \pm 0.005\text{m}$, base centering, $N_{\text{bones}} = 0$, 4-channel PBR, Blender 4.5 headless turntable & thumbnail rendering | M2 | IN_PROGRESS (26/35 normalized & rendered) |
| 4 | Manifest Aggregation, Viewer Sync & Final E2E Pass | Aggregate master `manifest.json`, synchronize interactive `viewer.html`, execute 100% automated test suite, forensic audit CLEAN | M3 | IN_PROGRESS (751 tests passing, viewer synced) |

---

## Interface Contracts

### `validator.py` ↔ `generator.py` / `post_processor.py`
- `validate_asset(target_path: Path | str, catalog_species: Optional[BotanicalSpecies] = None) -> ValidationReport`
- Input: path to normalized `<species_id>.glb`
- Assertions:
  * `20000 <= vertex_count <= 65000`
  * `|Z_min| <= 0.005m`
  * `base_centroid_offset <= 0.05m`
  * `n_bones == 0`
  * `albedo_std > 0.02`, `roughness_std > 0.01`
  * `source == "meshy"`, `task_id is not None`

### `generator.py` ↔ Meshy OpenAPI v2
- `POST https://api.meshy.ai/openapi/v2/text-to-3d`
  - Preview: `{"mode": "preview", "prompt": ..., "art_style": "realistic", "ai_model": "meshy-6", "topology": "quad", "target_polycount": 30000, "should_remesh": true}`
  - Refine: `{"mode": "refine", "preview_task_id": ..., "enable_pbr": true, "texture_richness": "high"}`
- `GET https://api.meshy.ai/openapi/v2/text-to-3d/{task_id}`
  - Header: `Authorization: Bearer <MESHY_API_KEY>`
  - Response: `{"status": "SUCCEEDED", "model_urls": {"glb": ...}, "texture_urls": [...]}`

### `post_processor.py` ↔ `renderer.py`
- `process_and_export(raw_glb_path, species_spec, output_dir) -> NormalizationResult`
- Output directory contains:
  * `<species_id>.glb` (normalized, ground-snapped, 4-channel PBR)
  * `<species_id>.obj`, `<species_id>.mtl`
  * `textures/` (`albedo.png`, `normal.png`, `roughness.png`, `metallic.png`)
  * `asset_manifest.json` (metadata + Meshy task provenance)
- `render_species_previews(glb_path, output_dir, species_spec) -> RenderResult`
  * `turntable_01.png` - `04.png` (512x512)
  * `thumbnail.png` (1024x1024 2x2 contact sheet)

---

## Code Layout
- `teamwork_projects/vegetation_library/`
  - `vegetation_pipeline/`
    - `catalog.py`: Botanical species taxonomy, metric specs, conditioned prompts
    - `generator.py`: Meshy AI client (preview + refine), backoff retry, provenance tracking
    - `post_processor.py`: Normalization, ground pivot snapping, PBR texture extraction, OBJ/MTL export
    - `renderer.py`: Headless Blender 4.5 turntable rendering & contact sheet generation
    - `validator.py`: QA validation engine (geometry, static mesh, PBR textures, provenance, collisions)
  - `pipeline.py`: Master CLI runner and manifest aggregator
  - `output/`: 35 species asset folders organized by category
    - `manifest.json`: Master library manifest
    - `viewer.html`: Interactive 3D botanical viewer
  - `tests/`: Automated pytest verification suite
    - `test_catalog.py`, `test_generator.py`, `test_normalization.py`, `test_renderer.py`, `test_validator.py`, `test_vegetation_pipeline.py`
