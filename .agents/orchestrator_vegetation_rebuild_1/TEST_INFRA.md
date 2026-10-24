# E2E Test Infra: Vegetation Library Rebuild

## Test Philosophy
- Opaque-box, requirement-driven. Derived from `ORIGINAL_REQUEST.md` (## 2026-09-10T11:11:31Z).
- Verification channels: GLB binary parsing, manifest schema assertions, image pixel analysis, CLI execution codes.
- Zero reliance on internal procedural fallback mocks.

## Feature Inventory & Test Coverage

| # | Feature | Requirement | Tier 1 Tests | Tier 2 Tests | Tier 3 Tests |
|---|---|---|---|---|---|
| 1 | Meshy Cloud Provenance | `source == "meshy"`, non-empty `task_id`, `model_type` | 5 | 5 | ✓ |
| 2 | Static Mesh Invariant | Strictly zero armature bones, joints, skinning weights | 5 | 5 | ✓ |
| 3 | Ground Pivot Snapping | Base contact at $Z_{\min} = 0.000\text{m} \pm 0.005\text{m}$, centered $(0, 0)$ | 5 | 5 | ✓ |
| 4 | Metric Scale Bounds | Height within $\pm 10\%$ of catalog target | 5 | 5 | ✓ |
| 5 | Polygon Budget Detail | Vertex and face counts within 20,000 to 65,000 | 5 | 5 | ✓ |
| 6 | 4-Channel PBR Textures | Albedo ($\sigma > 0.02$), Normal, Roughness ($\sigma > 0.01$), Metallic ($\le 0.05$) | 5 | 5 | ✓ |
| 7 | Pairwise Vertex Divergence | Pairwise vertex count collision rate < 5% across library | 5 | 5 | ✓ |
| 8 | Headless Previews & Montages | 4 turntables (512x512) and 1 thumbnail montage (1024x1024) | 5 | 5 | ✓ |
| 9 | Master Manifest Integrity | Valid JSON, 35 species records, matching disk counts | 5 | 5 | ✓ |
| 10 | Interactive Viewer Display | Synchronized data cards and thumbnail links | 5 | 5 | ✓ |

## Test Architecture
- **Test Runner**: `uv run pytest teamwork_projects/vegetation_library/tests/ -v`
- **Verification Harnesses**:
  - `vegetation_pipeline.validator.validate_asset()`
  - `vegetation_pipeline.validator.validate_directory()`
  - `tests/test_vegetation_pipeline.py`
  - `tests/test_validator.py`
  - `tests/test_normalization.py`
  - `tests/test_generator.py`
  - `tests/test_renderer.py`
  - `tests/test_catalog.py`

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Pipeline End-to-End Run | Meshy generation, normalization, rendering, manifest generation | High |
| 2 | Full Library Cross-Species Divergence Audit | Vertex collision across all 595 species pairs, morphology check | High |
| 3 | Multi-Biome Studio Showcase Verification | All 7 biomes render correctly under Blender 4.5 lighting | Medium |
| 4 | Viewer Interactive Model Inspection | Verification that viewer cards accurately render metrics and previews | Medium |
| 5 | Headless CLI Summary Inspection | Verifies `pipeline.py --summary` outputs cleanly without character encoding failures | Low |

## Coverage Thresholds
- Tier 1: 5 tests per feature (>= 50 test cases)
- Tier 2: 5 tests per feature (>= 50 test cases)
- Tier 3: Pairwise combinations across features (>= 15 test cases)
- Tier 4: 5 realistic application scenarios
- **Total test cases in suite: >= 255 passing tests**
