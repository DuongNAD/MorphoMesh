# Handoff Report: Meshy AI Text-to-3D Generation Engine Architecture (Milestone 2)

- **Author**: Explorer 1 (`m2_explorer_1`)
- **Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\m2_explorer_1`
- **Target File**: `teamwork_projects/vegetation_library/vegetation_pipeline/generator.py`
- **Test File**: `teamwork_projects/vegetation_library/tests/test_generator.py`
- **Parent Conversation ID**: `1f2774e9-3e4e-4a4c-8dc6-f85249e37b16`
- **Date**: 2026-09-10T12:50:00+07:00

---

## 1. Observation

### 1.1 Existing MeshyConnector Analysis (`src/morphomesh/connectors/meshy_connector.py`)
- **Class Definition & Line**: Line 309: `class MeshyConnector(BaseConnector)` is registered under aliases `"meshy"`, `"meshyai"`, `"meshy_ai"`.
- **API Key Resolution**: Lines 344–356:
  ```python
  def _resolve_api_key(self) -> Optional[str]:
      if self.meshy_config.api_key:
          return self.meshy_config.api_key.strip().strip("'\"")
      env_key = os.environ.get("MESHY_API_KEY") or os.environ.get("MESHY_AI_API_KEY")
      if env_key:
          return env_key.strip().strip("'\"")
      return None
  ```
  Active probe confirms `MESHY_API_KEY` in `.env` is valid with a verified balance of 936 credits (`https://api.meshy.ai/openapi/v1/balance`).
- **Endpoint Definitions**:
  - Base URL: `MESHY_API_BASE = "https://api.meshy.ai"` (Line 64).
  - Preview & Refine: `POST /openapi/v2/text-to-3d` (Lines 622, 651, 668).
  - Task Query: `GET /openapi/v2/text-to-3d/{task_id}` (Lines 629, 656, 672).
  - Balance Probe: `GET /openapi/v1/balance` (Line 390).
- **Two-Stage Workflow in Connector**:
  - Lines 635–674: When `boost=True` or `auto_refine=True`, `MeshyConnector` posts a preview task, polls it until completion, and immediately posts a refine task with `preview_task_id`, polling the refine task until completion.
- **Deficiencies of `MeshyConnector` for Botanical Vegetation Pipeline**:
  1. *Lack of Rate Limiting & Retry Backoff on HTTP 429 / 5xx*:
     In `_post_json_task` (Lines 821–828):
     ```python
     except urllib.error.HTTPError as e:
         err_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
         raise MorphoMeshException(
             code=ERR_INFERENCE_FAILED,
             message=f"Meshy task submission failed with HTTP {e.code}: {err_body}",
             details={"http_code": e.code, "error": err_body, "url": url},
         )
     ```
     Any HTTP 429 ("Too Many Requests") or transient 5xx server error immediately aborts the pipeline with an unhandled exception. No exponential backoff or `Retry-After` header inspection exists.
  2. *Absence of Disk Caching*:
     Lines 507–509:
     ```python
     asset_id = f"meshy_{uuid.uuid4().hex[:8]}"
     out_dir = inp.output_dir or os.path.expanduser(f"~/.morphomesh/cache/assets/{asset_id}")
     os.makedirs(out_dir, exist_ok=True)
     ```
     Every call to `execute` generates a brand new random UUID. It does not check if an asset for the same species or prompt already exists on disk, unconditionally triggering cloud generation and burning 20+ API credits per call.
  3. *Unsuitable Mock Fallback for Vegetation*:
     Lines 1119–1145: `_execute_mock` generates an animal/chimera mesh with cylinders for torso/chest/neck, a sphere for head, limbs, horns, and wings. If fallback triggers, it generates a creature instead of vegetation.
  4. *Mismatch with Botanical Contracts*:
     `MeshyConnector` accepts `MeshyInput` and outputs `MeshyOutput`. The Vegetation Library requires inputs from `PlantSpecies` (from `catalog.py`) and must return `RawAsset` conforming to the M2 ↔ M3 contract in `PROJECT.md`.

### 1.2 Reusable Shared Geometry & Texture Utilities
- Pure Python glTF 2.0 parser & unpacker in `src/morphomesh/connectors/tripo_connector.py`:
  - `parse_glb_metrics(glb_path: str) -> Tuple[int, int]`: Extracts vertex count and face count using pure standard library `struct` and `json` (no `trimesh` or `pygltflib` required).
  - `extract_glb_textures(glb_path: str, out_dir: str, prefix: str) -> PBRTextureMaps`: Extracts embedded PNG/JPEG buffer views and unpacks ORM (Occlusion/Roughness/Metallic) textures into separate PBR channels.
- Pure Python 3D geometry engine in `src/morphomesh/inference_adapter.py`:
  - `MeshGeometry`: `add_cylinder`, `add_sphere`, `add_box`, `export_glb`, `export_obj`.

### 1.3 Milestone 1 Taxonomy Catalog Status (`vegetation_pipeline/catalog.py`)
- Test verification: `uv run pytest teamwork_projects/vegetation_library/tests/test_catalog.py` executes 52 tests, 100% PASS in 0.11s.
- `PlantSpecies` schema provides:
  - `species_id`: canonical identifier (e.g. `"veg_tree_oak_01"`).
  - `meshy_spec.positive_prompt`: botanical prompt tuned with grounding anchors.
  - `meshy_spec.negative_prompt`: includes `UNIVERSAL_NEGATIVE_BLACKLIST` forbidding pots, planters, stands, humans, skeletons, bones, armatures, and rigs.
  - `meshy_spec.ai_model`: `"meshy-4"`.
  - `meshy_spec.topology`: `"quad"`.
  - `meshy_spec.target_polycount`: 28000.
  - `meshy_spec.enable_pbr`: `True`.
  - `meshy_spec.texture_richness`: `"high"`.
  - `meshy_spec.boost`: `True`.

---

## 2. Logic Chain

1. **Architecture & Boundary Decision (Standalone Engine vs Subclassing)**:
   - Observation 1.1 reveals that while `MeshyConnector` has low-level HTTP call patterns, its `execute()` method is bound to random UUID asset IDs, lacks retry logic for HTTP 429, lacks disk caching, and its mock fallback generates creatures.
   - Subclassing `MeshyConnector` would inherit legacy baggage and risk regressions in core `morphomesh` MCP server tools.
   - Therefore, `MeshyGenerator` must be designed as a dedicated, self-contained botanical generation engine in `teamwork_projects/vegetation_library/vegetation_pipeline/generator.py`. It can import low-level utilities (`parse_glb_metrics`, `extract_glb_textures`, `MeshGeometry`) and credential resolution from `morphomesh.connectors.meshy_connector`, while encapsulating specialized rate limiting, species-keyed disk caching, and botanical asset packaging.

2. **Two-Stage Text-to-3D Implementation Logic**:
   - Observation 1.1 and 1.3 confirm that Meshy AI v2 Text-to-3D requires two sequential stages to produce production-grade game-ready vegetation with 4-channel PBR textures:
     - **Stage 1 (Preview)**: Submits prompt, negative blacklist, quad topology, and target polycount. Returns `preview_task_id`. Polled until status is `SUCCEEDED`.
     - **Stage 2 (Refine)**: Submits `preview_task_id`, `enable_pbr=True`, and `texture_richness="high"`. Returns `refine_task_id`. Polled until status is `SUCCEEDED`.
   - The result provides URLs for a high-poly quad GLB and separate PBR texture maps (Albedo, Normal, Roughness, Metallic).

3. **Rate Limiting & Exponential Backoff Logic**:
   - Observation 1.1 shows that HTTP 429 or transient 5xx errors currently cause hard failures.
   - When generating 35 plant species, API rate limits or transient cloud delays can occur.
   - The engine must implement truncated exponential backoff with full jitter:
     $$T_{\text{wait}} = \min\left(T_{\max}, T_{\text{base}} \times 2^{\text{attempt}}\right) + \text{uniform}(0, J)$$
     where $T_{\text{base}} = 2.0\text{s}$, $T_{\max} = 60.0\text{s}$, $J = 1.0\text{s}$, and $\text{max\_retries} = 5$.
   - If the server responds with an HTTP 429 containing a `Retry-After` header, $T_{\text{wait}} = \max(T_{\text{wait}}, \text{int}(\text{header}))$.
   - Terminal client errors (HTTP 400, 401, 402, 403, 404, 422) must fail fast without wasteful retries.

4. **Disk Caching & Credit Conservation Logic**:
   - The active account has 936 credits; refining 35 species consumes ~700 credits (~20 credits per model).
   - Once a species has been successfully generated and stored on disk, repeated invocations (e.g. during testing, pipeline reruns, or post-processing development) must NOT re-call the remote API.
   - Caching must be keyed deterministically by `species.species_id` and verified via content integrity:
     - GLB file exists and size $> 1024$ bytes.
     - `cache_manifest.json` exists with matching species ID and prompt hash.
     - All 4 PBR texture maps (albedo, normal, roughness, metallic) exist and are valid readable images.
     - Parsed vertex count is within botanical bounds ($3,000 \le V \le 45,000$).
   - A `--force-regenerate` / `force_regenerate=True` flag must be provided to bypass cache when explicitly requested.

5. **Static Mesh & Zero-Armature Enforcement Logic**:
   - Requirement R2 mandates static meshes with zero skeletal armatures or skinning.
   - Prompt-level mitigation: `species.meshy_spec.negative_prompt` includes `"skeleton, bones, armature, rig, rigged, rigging, skinning, joints"`.
   - Structural validation: `MeshyGenerator` inspects the glTF JSON chunk of the downloaded GLB for the presence of `"skins"` or primitive attributes (`"JOINTS_0"`, `"WEIGHTS_0"`). If found, it flags a warning and strips them to guarantee an unrigged static mesh.

6. **Contract Fulfillment (`RawAsset`)**:
   - The M2 ↔ M3 contract in `PROJECT.md` specifies `generate_plant(species, mode, output_dir) -> RawAsset`.
   - `RawAsset` must contain:
     - `species_id: str`
     - `glb_path: Path`
     - `mesh: Optional[MeshGeometry]`
     - `textures: Dict[str, Image.Image]`
     - `texture_paths: Dict[str, Path]`
     - `source: Literal["meshy", "procedural", "cached"]`
     - `vertex_count: int`
     - `face_count: int`
     - `metadata: Dict[str, Any]`

---

## 3. Caveats

1. **Network Connectivity & Mocking in Tests**:
   - Unit tests in `tests/test_generator.py` MUST NOT call the live Meshy API during routine testing to avoid consuming credits and failing in offline CI environments.
   - All network calls (`urllib.request.urlopen` or `httpx`) must be mocked using deterministic fixtures in unit tests, verifying the backoff algorithm, state transitions, and caching logic.
   - Live integration smoke tests must be gated with `@pytest.mark.skipif(not os.environ.get("MESHY_API_KEY"), reason="No MESHY_API_KEY")` and enabled only on demand.
2. **Third-Party Dependencies**:
   - `trimesh`, `pygltflib`, `requests`, and `scipy` are NOT installed in `.venv`. All glTF inspection, texture extraction, and HTTP requests must use standard library modules (`struct`, `json`, `urllib.request`), `httpx`, `numpy`, and `PIL`.
3. **Procedural Fallback Interlock**:
   - `MeshyGenerator` focuses on Meshy AI Text-to-3D generation. Peer Explorer 2 (`m2_explorer_2`) designs `ProceduralBotanicalGenerator`. Both are unified under `generate_plant(species, mode="auto")` in `generator.py`.

---

## 4. Conclusion & Architectural Specification

### 4.1 Module Architecture in `vegetation_pipeline/generator.py`

```
vegetation_pipeline/generator.py
├── RawAsset (Pydantic Schema)
├── MeshyGeneratorConfig (Pydantic Schema)
├── MeshyGenerator (Class)
│   ├── resolve_api_key() -> Optional[str]
│   ├── check_health() -> Dict[str, Any]
│   ├── check_cache(species, target_dir) -> Optional[RawAsset]
│   ├── save_cache(raw_asset, species, cache_dir) -> None
│   ├── generate(species, output_dir, force_regenerate) -> RawAsset
│   ├── _submit_preview(species, api_key) -> str (preview_task_id)
│   ├── _poll_preview(task_id, api_key) -> Dict[str, Any]
│   ├── _submit_refine(preview_task_id, api_key) -> str (refine_task_id)
│   ├── _poll_refine(task_id, api_key) -> Dict[str, Any]
│   ├── _request_with_retry(method, url, headers, data) -> Dict[str, Any]
│   ├── _download_file(url, target_path) -> None
│   ├── _download_or_extract_textures(task_data, glb_path, target_dir) -> Dict[str, Path]
│   └── _verify_static_mesh(glb_path) -> bool
├── ProceduralBotanicalGenerator (M2 Peer Explorer 2)
└── generate_plant(species, mode, output_dir, force_regenerate, config) -> RawAsset
```

### 4.2 Data Schemas & API Contract

```python
from __future__ import annotations
from pathlib import Path
from typing import Any, Callable, Dict, Literal, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field
from PIL import Image
from morphomesh.inference_adapter import MeshGeometry

class RawAsset(BaseModel):
    """
    Un-normalized raw 3D botanical asset emitted by generator.
    Conforms to M2 <-> M3 Interface Contract.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    species_id: str = Field(..., description="Canonical species ID (e.g. 'veg_tree_oak_01')")
    glb_path: Path = Field(..., description="Path to raw generated .glb file")
    mesh: Optional[MeshGeometry] = Field(default=None, description="In-memory MeshGeometry if available")
    textures: Dict[str, Image.Image] = Field(
        default_factory=dict,
        description="Loaded PIL Images for 'albedo', 'normal', 'roughness', 'metallic'"
    )
    texture_paths: Dict[str, Path] = Field(
        default_factory=dict,
        description="Paths on disk for 'albedo', 'normal', 'roughness', 'metallic'"
    )
    source: Literal["meshy", "procedural", "cached"] = Field(..., description="Source engine")
    vertex_count: int = Field(default=0, ge=0, description="Total vertex count")
    face_count: int = Field(default=0, ge=0, description="Total triangle/face count")
    thumbnail_path: Optional[Path] = Field(default=None, description="Local thumbnail preview image")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Generation metadata and task IDs")


class MeshyGeneratorConfig(BaseModel):
    """Configuration options for MeshyGenerator."""
    model_config = ConfigDict(extra="ignore")

    api_key: Optional[str] = None
    base_url: str = "https://api.meshy.ai"
    ai_model: str = "meshy-4"
    topology: str = "quad"
    target_polycount: int = 28000
    texture_richness: str = "high"
    enable_pbr: bool = True
    cache_dir: Optional[Path] = None
    use_cache: bool = True
    force_regenerate: bool = False
    preview_timeout_seconds: float = 300.0
    refine_timeout_seconds: float = 450.0
    polling_interval_seconds: float = 2.5
    max_retries: int = 5
    backoff_base_seconds: float = 2.0
    backoff_max_seconds: float = 60.0
```

### 4.3 Detailed Two-Stage Protocol & Payloads

#### Stage 1: Preview Submission
- **HTTP Request**: `POST {base_url}/openapi/v2/text-to-3d`
- **Payload**:
  ```json
  {
    "mode": "preview",
    "prompt": "<species.meshy_spec.positive_prompt>",
    "negative_prompt": "<species.meshy_spec.negative_prompt>",
    "art_style": "realistic",
    "ai_model": "meshy-4",
    "topology": "quad",
    "target_polycount": 28000,
    "should_remesh": true,
    "seed": -1
  }
  ```
- **Response**: `{"result": "<task_id>"}`.
- **Polling**: `GET {base_url}/openapi/v2/text-to-3d/{preview_task_id}`.
- **Completion Criteria**: `status == "SUCCEEDED"`.

#### Stage 2: Refine Submission
- **HTTP Request**: `POST {base_url}/openapi/v2/text-to-3d`
- **Payload**:
  ```json
  {
    "mode": "refine",
    "preview_task_id": "<preview_task_id>",
    "texture_richness": "high",
    "enable_pbr": true
  }
  ```
- **Response**: `{"result": "<refine_task_id>"}`.
- **Polling**: `GET {base_url}/openapi/v2/text-to-3d/{refine_task_id}`.
- **Completion Criteria**: `status == "SUCCEEDED"` and `model_urls.glb` is present.

### 4.4 Rate Limiting with Exponential Backoff Algorithm

```python
def _request_with_retry(
    self,
    method: str,
    url: str,
    headers: Dict[str, str],
    data: Optional[bytes] = None,
) -> Dict[str, Any]:
    """
    Executes HTTP request with truncated exponential backoff, jitter,
    and Retry-After support for HTTP 429 and transient 5xx errors.
    """
    attempt = 0
    while True:
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            # Terminal client errors: fail fast
            if e.code in (400, 401, 402, 403, 404, 422):
                err_text = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
                raise MorphoMeshException(
                    code=ERR_INFERENCE_FAILED,
                    message=f"Meshy API client error {e.code}: {err_text}",
                    details={"http_code": e.code, "url": url},
                )

            # Retriable errors: 429 (Rate Limit) and 5xx (Server Error)
            attempt += 1
            if attempt > self.config.max_retries:
                err_text = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
                raise MorphoMeshException(
                    code=ERR_INFERENCE_FAILED,
                    message=f"Meshy API request exceeded max retries ({self.config.max_retries}): HTTP {e.code}",
                    details={"http_code": e.code, "url": url, "error": err_text},
                )

            # Check for Retry-After header
            retry_after = None
            if "Retry-After" in e.headers:
                try:
                    retry_after = float(e.headers["Retry-After"])
                except (ValueError, TypeError):
                    pass

            # Calculate backoff with jitter
            base_delay = self.config.backoff_base_seconds * (2 ** (attempt - 1))
            jitter = random.uniform(0.0, 1.0)
            delay = min(self.config.backoff_max_seconds, base_delay) + jitter
            if retry_after is not None:
                delay = max(delay, retry_after)

            logger.warning(
                "Meshy API returned HTTP %s on %s. Retrying in %.2fs (attempt %d/%d)...",
                e.code, url, delay, attempt, self.config.max_retries
            )
            time.sleep(delay)

        except (urllib.error.URLError, TimeoutError, OSError) as e:
            attempt += 1
            if attempt > self.config.max_retries:
                raise MorphoMeshException(
                    code=ERR_BACKEND_UNAVAILABLE,
                    message=f"Meshy network error after {self.config.max_retries} retries: {e}",
                    details={"url": url, "error": str(e)},
                )
            delay = min(self.config.backoff_max_seconds, self.config.backoff_base_seconds * (2 ** (attempt - 1)))
            logger.warning("Transient network error %s. Retrying in %.2fs...", e, delay)
            time.sleep(delay)
```

### 4.5 Disk Caching Architecture & Manifest

- **Default Cache Directory**:
  `teamwork_projects/vegetation_library/.cache/meshy/<species_id>/`
- **Cache Files**:
  - `<species_id>.glb`: Primary 3D model.
  - `<species_id>_preview.jpg`: Remote thumbnail preview.
  - `textures/`: Unpacked 4-channel PBR textures (`albedo.png`, `normal.png`, `roughness.png`, `metallic.png`).
  - `cache_manifest.json`: Metadata record:
    ```json
    {
      "species_id": "veg_tree_oak_01",
      "prompt_hash": "a1b2c3d4e5f6...",
      "preview_task_id": "018e47b2-xxxx",
      "refine_task_id": "018e47c5-yyyy",
      "vertex_count": 27840,
      "face_count": 28120,
      "created_at": "2026-09-10T12:00:00Z",
      "textures": {
        "albedo": "textures/albedo.png",
        "normal": "textures/normal.png",
        "roughness": "textures/roughness.png",
        "metallic": "textures/metallic.png"
      }
    }
    ```
- **Integrity Validation Logic**:
  `check_cache(species, target_dir) -> Optional[RawAsset]`:
  1. Locates candidate directory (either `target_dir/<species_id>` or `cache_dir/<species_id>`).
  2. Verifies `<species_id>.glb` exists and size $> 1024$ bytes.
  3. Verifies `cache_manifest.json` exists and matches `species_id`.
  4. Verifies prompt hash matches `sha256(species.meshy_spec.positive_prompt)`.
  5. Verifies all 4 texture files exist and are readable images.
  6. If all checks pass, returns `RawAsset(..., source="cached")`.

### 4.6 Master Pipeline Entry Point (`generate_plant`)

```python
def generate_plant(
    species: PlantSpecies,
    mode: Literal["auto", "meshy", "procedural"] = "auto",
    output_dir: Optional[Union[str, Path]] = None,
    force_regenerate: bool = False,
    generator_config: Optional[MeshyGeneratorConfig] = None,
) -> RawAsset:
    """
    Master generation entry point coordinating Meshy AI Text-to-3D
    and Procedural Botanical Fallback.
    """
    out_path = Path(output_dir) if output_dir else Path("./output") / species.short_category / species.species_id
    out_path.mkdir(parents=True, exist_ok=True)

    meshy_gen = MeshyGenerator(config=generator_config)

    # 1. Check disk cache if regeneration not forced
    if not force_regenerate:
        cached_asset = meshy_gen.check_cache(species, target_dir=out_path)
        if cached_asset:
            logger.info("Cache hit for species %s at %s", species.species_id, out_path)
            return cached_asset

    # 2. Mode: Explicit Procedural
    if mode == "procedural":
        proc_gen = ProceduralBotanicalGenerator()
        return proc_gen.generate(species, output_dir=out_path)

    # 3. Mode: Explicit Meshy AI
    if mode == "meshy":
        return meshy_gen.generate(species, output_dir=out_path, force_regenerate=force_regenerate)

    # 4. Mode: Auto (Meshy with graceful Procedural Fallback)
    api_key = meshy_gen.resolve_api_key()
    if not api_key:
        logger.warning("No MESHY_API_KEY found. Falling back to ProceduralBotanicalGenerator.")
        proc_gen = ProceduralBotanicalGenerator()
        return proc_gen.generate(species, output_dir=out_path)

    try:
        return meshy_gen.generate(species, output_dir=out_path, force_regenerate=force_regenerate)
    except Exception as e:
        logger.warning("Meshy generation failed (%s). Engaging procedural fallback.", e)
        proc_gen = ProceduralBotanicalGenerator()
        return proc_gen.generate(species, output_dir=out_path)
```

---

## 5. Verification Method

To independently verify the architecture and specifications in this report:

1. **Verify Existing MeshyConnector Unit Tests (Baseline Integrity)**:
   ```powershell
   uv run pytest tests/test_meshy_connector.py -v
   ```
   Must pass 100% (49 passed).

2. **Verify Catalog Prompt & Blacklist Alignment**:
   ```powershell
   uv run pytest teamwork_projects/vegetation_library/tests/test_catalog.py -k "Meshy" -v
   ```
   Must pass 100% (5 passed).

3. **Verify Planned Generator Test Suite Structure**:
   Implementer will write `teamwork_projects/vegetation_library/tests/test_generator.py` testing:
   - `test_meshy_generator_config_defaults()`: validates polling interval, timeouts, and backoff parameters.
   - `test_rate_limiting_exponential_backoff_on_429()`: mocks HTTP 429 with `Retry-After` header and asserts retry intervals.
   - `test_transient_5xx_retries()`: mocks HTTP 500/503 and asserts success after 2 retries.
   - `test_terminal_4xx_fail_fast()`: mocks HTTP 401/403 and asserts immediate `MorphoMeshException`.
   - `test_disk_caching_hit_and_miss()`: validates cache creation, cache hit return, and `--force-regenerate`.
   - `test_two_stage_api_workflow_mocked()`: simulates preview task followed by refine task, validating payload schemas.
   - `test_static_mesh_zero_armatures_assertion()`: verifies GLB structure inspection detecting and forbidding armatures.
   - `test_generate_plant_contract_compliance()`: asserts `RawAsset` fields, types, and invariants across `"meshy"`, `"procedural"`, and `"cached"` modes.
   Execute command:
   ```powershell
   uv run pytest teamwork_projects/vegetation_library/tests/test_generator.py -v
   ```
