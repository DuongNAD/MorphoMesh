# Explorer 2 Handoff Report: Milestone 2 Iteration 2 (Remediation Strategy)

- **Agent**: Explorer 2 (`m2_iter2_veg_explorer_2`)
- **Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\m2_iter2_veg_explorer_2`
- **Parent Conversation ID**: `1f2774e9-3e4e-4a4c-8dc6-f85249e37b16`
- **Mission**: Investigate and design the exact remediation strategy for Meshy API compatibility (`meshy-6`), rate limit backoff delay capping, fast-fail on 4xx errors, static mesh validation enforcement, and input mode validation.
- **Date**: 2026-09-10T13:02:30+07:00

---

## 1. Observation

### 1.1 Live API Model Deprecation (`meshy-4` Rejected with HTTP 400)
- **Code Observation in `generator.py:164`**:
  ```python
  class MeshyGeneratorConfig(BaseModel):
      model_config = ConfigDict(extra="ignore")

      api_key: Optional[str] = None
      base_url: str = "https://api.meshy.ai"
      ai_model: str = "meshy-4"
  ```
- **Code Observation in `catalog.py:103`**:
  ```python
  class MeshyPromptSpec(BaseModel):
      positive_prompt: str = Field(..., min_length=20, description="Conditioned botanical positive prompt")
      negative_prompt: str = Field(..., min_length=20, description="Negative prompt blacklist eliminating pots, stands, humans")
      ai_model: str = Field(default="meshy-4", description="Meshy model tier")
  ```
- **Code Observation in `taxonomy_catalog.json`**:
  Contains exactly 35 instances of `"ai_model": "meshy-4"`, one for each species (lines 117, 168, 219, 270, 321, 372, 423, 474, 525, 576, 627, 678, 729, 780, 831, 882, 933, 984, 1035, 1086, 1137, 1188, 1239, 1290, 1341, 1392, 1443, 1494, 1545, 1596, 1647, 1698, 1749, 1800, 1851).
- **Test Observations in `tests/test_generator.py` and `tests/test_catalog.py`**:
  - `tests/test_generator.py:192`: `assert gen.config.ai_model == "meshy-4"`
  - `tests/test_generator.py:226`: `assert payload["ai_model"] == "meshy-4"`
  - `tests/test_catalog.py:240`: `assert spec.ai_model == "meshy-4"`
- **Verbatim Live Endpoint Response**:
  As documented by the Forensic Auditor and Reviewer 1: Probing `POST https://api.meshy.ai/openapi/v2/text-to-3d` with `ai_model="meshy-4"` returns:
  ```json
  HTTP 400: {"message":"meshy-4 is deprecated, please use meshy-6 instead"}
  ```
  Probing with `ai_model="meshy-6"` returns HTTP 200 with an active task ID:
  ```json
  HTTP 200: {"result":"01a089e2-7a1c-7226-a68b-1ae7bf8df67d"}
  ```

---

### 1.2 Unbounded `Retry-After` Denial-of-Service / Hanging Vulnerability
- **Code Observation in `generator.py:262-267` (`_request_with_retry`)**:
  ```python
  base_delay = self.config.backoff_base_seconds * (2 ** (attempt - 1))
  jitter = random.uniform(0.0, 0.5)
  delay = min(self.config.backoff_max_seconds, base_delay + jitter)
  if retry_after is not None:
      delay = max(delay, retry_after)

  logger.warning(
      "Meshy API returned HTTP %s on %s. Retrying in %.2fs (attempt %d/%d)...",
      e.code, url, delay, attempt, self.config.max_retries,
  )
  time.sleep(delay)
  ```
- **Vulnerability Mechanism**:
  `min(self.config.backoff_max_seconds, ...)` is evaluated on line 264 *prior* to `if retry_after is not None: delay = max(delay, retry_after)`.
  If the server returns `Retry-After: 86400` (e.g. 24 hours) or a corrupted large integer, `delay` becomes `86400.0`. Line 272 executes `time.sleep(86400.0)`.
  This completely ignores `backoff_max_seconds` (default 60s) and freezes the client process indefinitely.

---

### 1.3 Fast-Fail Classification Gap on Non-429 4xx Client Errors
- **Code Observation in `generator.py:240-254` (`_request_with_retry`)**:
  ```python
  except urllib.error.HTTPError as e:
      # Terminal client errors: fail fast without retry
      if e.code in (400, 401, 402, 403, 404, 422):
          err_text = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
          raise RuntimeError(
              f"Meshy API client error {e.code}: {err_text}"
          )

      # Retriable errors: 429 (Rate Limit) and 5xx (Server Error)
      attempt += 1
      if attempt > self.config.max_retries:
          err_text = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
          raise RuntimeError(
              f"Meshy API request exceeded max retries ({self.config.max_retries}): HTTP {e.code} - {err_text}"
          )
  ```
- **Classification Gap**:
  The whitelist `(400, 401, 402, 403, 404, 422)` omits standard HTTP client error codes:
  - 405 (Method Not Allowed)
  - 408 (Request Timeout)
  - 409 (Conflict)
  - 410 (Gone)
  - 413 (Payload Too Large)
  - 414 (URI Too Long)
  - 415 (Unsupported Media Type)
  - 428 (Precondition Required)
  Because these errors are not 429 and are not in the whitelist, they fall through to the retry loop. They are retried 5 times with exponential sleep delays instead of failing fast immediately.

---

### 1.4 Discarded Static Mesh Verification Result
- **Code Observation in `generator.py:569-571` (`MeshyGenerator.generate`)**:
  ```python
  # 5. Static mesh invariant enforcement
  self._verify_static_mesh(glb_path)

  # 6. Textures download/extract
  textures, texture_paths = self._download_or_extract_textures(refine_task, glb_path, out_path, species)
  ```
- **Code Observation in `generator.py:360-373` (`MeshyGenerator._verify_static_mesh`)**:
  ```python
  def _verify_static_mesh(self, glb_path: Path) -> bool:
      """Verifies that the downloaded GLB contains zero skeletal armatures, joints, or skinning."""
      try:
          gltf, _ = unpack_glb_header_and_json(glb_path)
          if gltf.get("skins") or gltf.get("animations"):
              raise ValueError(f"GLB at {glb_path} contains skins or animations")
          for mesh in gltf.get("meshes", []):
              for prim in mesh.get("primitives", []):
                  attrs = prim.get("attributes", {})
                  for k in attrs:
                      if k.startswith("JOINTS_") or k.startswith("WEIGHTS_"):
                          raise ValueError(f"GLB contains skeletal skinning attribute {k}")
          return True
      except Exception as e:
          logger.warning("Static mesh verification warning for %s: %s", glb_path, e)
          return False
  ```
- **Defect Mechanism**:
  `_verify_static_mesh` returns `bool` (`True` if valid static mesh without bones/skins/animations, `False` otherwise).
  At line 570, `self._verify_static_mesh(glb_path)` is called as a bare expression. Its return value is completely discarded.
  If an asset returned from Meshy contains bones, skeletal skinning attributes, or animations, the warning is logged, but execution continues, packaging and returning the non-static asset.

---

### 1.5 Silent Treatment of Invalid Generation Modes in `generate_plant`
- **Code Observation in `generator.py:1365-1415`**:
  ```python
  def generate_plant(
      species: Union[PlantSpecies, str],
      mode: Literal["auto", "meshy", "procedural"] = "auto",
      output_dir: Optional[Union[str, Path]] = None,
      seed: Optional[int] = None,
      force_regenerate: bool = False,
      generator_config: Optional[MeshyGeneratorConfig] = None,
      **kwargs: Any,
  ) -> RawAsset:
      # 1. Resolve species input
      if isinstance(species, str):
          ...
      # 2. Mode: Explicit Procedural
      if mode == "procedural":
          proc_gen = ProceduralBotanicalGenerator(seed=seed)
          return proc_gen.generate(species_obj, output_dir=out_path, seed=seed)
      ...
      # 5. Mode: Explicit Meshy
      if mode == "meshy":
          ...
      # 6. Mode: Auto (Meshy with graceful Procedural Fallback)
  ```
- **Defect Mechanism**:
  Passing an invalid string such as `mode="mesh"`, `mode="custom"`, or `mode=""` does not raise an error. Because `mode != "procedural"` and `mode != "meshy"`, execution silently proceeds to Step 6 (`mode == "auto"`), concealing typos and caller errors.

---

## 2. Logic Chain

1. **Step 1 (API Compatibility)**:
   - Observation 1.1 confirms that live Meshy API v2 rejects `meshy-4` with HTTP 400 (`"meshy-4 is deprecated, please use meshy-6 instead"`).
   - In `generator.py`, `_request_with_retry` treats HTTP 400 as a terminal client error.
   - Therefore, default generation requests to the live Meshy API fail 100% of the time.
   - Upgrading `MeshyGeneratorConfig.ai_model`, `MeshyPromptSpec.ai_model`, and all 35 records in `taxonomy_catalog.json` to `"meshy-6"` aligns the code with the live API.

2. **Step 2 (Rate Limit Backoff Safety)**:
   - Observation 1.2 demonstrates that `delay = max(delay, retry_after)` overrides `delay = min(self.config.backoff_max_seconds, ...)`.
   - Any external header `Retry-After: N` with $N > \text{backoff\_max\_seconds}$ causes the application thread to sleep for $N$ seconds.
   - Applying `delay = min(self.config.backoff_max_seconds, delay)` after resolving `retry_after` mathematically guarantees that $0 \le \text{delay} \le \text{backoff\_max\_seconds}$, preventing unhandled hanging.

3. **Step 3 (Error Fast-Fail Completeness)**:
   - Observation 1.3 shows that client errors outside `(400, 401, 402, 403, 404, 422)` (such as 405, 409, 413, 415) fall through to the retry loop.
   - By RFC specifications, client errors indicate request deficiencies that cannot be resolved by repeating the identical request.
   - Changing the condition to `if 400 <= e.code < 500 and e.code != 429:` ensures all non-429 client errors terminate immediately on attempt 1 without sleeping or retrying.

4. **Step 4 (Static Mesh Invariant Enforcement)**:
   - Observation 1.4 confirms that `self._verify_static_mesh(glb_path)` return value is discarded.
   - Requirement R2 and Feature 9 mandate that plant assets have zero armatures, skins, joints, or animations.
   - Enforcing `if not self._verify_static_mesh(glb_path): raise RuntimeError(...)` ensures invalid rigged models are blocked at the engine boundary. In `mode="auto"`, this exception triggers graceful procedural fallback.

5. **Step 5 (Mode Validation Contract)**:
   - Observation 1.5 shows `Literal` types do not enforce runtime validation.
   - Adding `if mode not in ("auto", "meshy", "procedural"): raise ValueError(...)` at the entry point of `generate_plant` ensures invalid modes fail immediately with descriptive feedback.

---

## 3. Caveats

- **Test Suite Isolation Synergy**: While Explorer 1 is designing the fix for cache pollution and test isolation in `test_dispatch_mode_meshy_explicit_without_key_raises`, our changes to `MeshyGenerator` error handling, model tier, and mode validation are completely orthogonal, robust, and synergistic.
- **Credit Conservation**: Testing with `meshy-6` on live endpoints consumes user cloud credits; tests in `tests/test_generator.py` must continue using mocks with `ai_model="meshy-6"` payloads.
- **Root morphomesh connectors**: `src/morphomesh/connectors/meshy_connector.py` is part of the root repository connector framework outside the `teamwork_projects/vegetation_library` milestone boundary. However, updating it to recognize `meshy-6` is recommended as an optional consistency improvement.

---

## 4. Conclusion & Concrete Implementation Specification

### Action Summary for Worker 2

| Component | Target File & Lines | Current State | Remediated State | Rationale |
|---|---|---|---|---|
| **AI Model Default** | `vegetation_pipeline/generator.py:164` | `ai_model: str = "meshy-4"` | `ai_model: str = "meshy-6"` | Meshy API deprecates `meshy-4` with HTTP 400; `meshy-6` is active. |
| **Catalog Spec Model** | `vegetation_pipeline/catalog.py:103` | `ai_model: str = Field(default="meshy-4", ...)` | `ai_model: str = Field(default="meshy-6", ...)` | Consistent model tier specification across Pydantic schemas. |
| **Taxonomy JSON Records** | `vegetation_pipeline/taxonomy_catalog.json` | 35 instances of `"ai_model": "meshy-4"` | 35 instances of `"ai_model": "meshy-6"` | Consistent taxonomy catalog data across all 35 species. |
| **Backoff Delay Capping** | `vegetation_pipeline/generator.py:262-267` | `min(...)` evaluated before `max(..., retry_after)` | `delay = min(self.config.backoff_max_seconds, delay)` applied after `max(...)` | Eliminates DoS / indefinite process freezing from large `Retry-After`. |
| **Fast-Fail 4xx Errors** | `vegetation_pipeline/generator.py:241` | Whitelist `(400, 401, 402, 403, 404, 422)` | `if 400 <= e.code < 500 and e.code != 429:` | All client errors (405, 409, 413, 415, etc.) fail fast without retries. |
| **Enforce Static Mesh** | `vegetation_pipeline/generator.py:570` | `self._verify_static_mesh(glb_path)` return discarded | `if not self._verify_static_mesh(glb_path): raise RuntimeError(...)` | Enforces zero armatures/skins contract; triggers fallback in auto mode. |
| **Mode Validation** | `vegetation_pipeline/generator.py:1378` | No runtime check on `mode` | `if mode not in ("auto", "meshy", "procedural"): raise ValueError(...)` | Rejects typo/invalid modes with immediate actionable exception. |
| **Test Assertions** | `tests/test_generator.py:192, 226` | Asserts `"meshy-4"` | Asserts `"meshy-6"` | Unit test alignment with updated default model tier. |
| **Test Assertions** | `tests/test_catalog.py:240` | Asserts `"meshy-4"` | Asserts `"meshy-6"` | Catalog test alignment with updated taxonomy catalog. |

---

### Precise Code Diffs for Worker 2

#### Diff 1: `vegetation_pipeline/generator.py`
```python
<<<<
    ai_model: str = "meshy-4"
====
    ai_model: str = "meshy-6"
>>>>

<<<<
            except urllib.error.HTTPError as e:
                # Terminal client errors: fail fast without retry
                if e.code in (400, 401, 402, 403, 404, 422):
                    err_text = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
                    raise RuntimeError(
                        f"Meshy API client error {e.code}: {err_text}"
                    )
====
            except urllib.error.HTTPError as e:
                # Terminal client errors: fail fast without retry (all 4xx except 429 Rate Limit)
                if 400 <= e.code < 500 and e.code != 429:
                    err_text = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
                    raise RuntimeError(
                        f"Meshy API client error {e.code}: {err_text}"
                    )
>>>>

<<<<
                base_delay = self.config.backoff_base_seconds * (2 ** (attempt - 1))
                jitter = random.uniform(0.0, 0.5)
                delay = min(self.config.backoff_max_seconds, base_delay + jitter)
                if retry_after is not None:
                    delay = max(delay, retry_after)
====
                base_delay = self.config.backoff_base_seconds * (2 ** (attempt - 1))
                jitter = random.uniform(0.0, 0.5)
                delay = base_delay + jitter
                if retry_after is not None:
                    delay = max(delay, retry_after)
                delay = min(self.config.backoff_max_seconds, delay)
>>>>

<<<<
        # 5. Static mesh invariant enforcement
        self._verify_static_mesh(glb_path)
====
        # 5. Static mesh invariant enforcement
        if not self._verify_static_mesh(glb_path):
            raise RuntimeError(
                f"Meshy generated asset {glb_path} violates static mesh invariant: "
                f"armatures, skins, animations, or skeletal weights detected"
            )
>>>>

<<<<
def generate_plant(
    species: Union[PlantSpecies, str],
    mode: Literal["auto", "meshy", "procedural"] = "auto",
    output_dir: Optional[Union[str, Path]] = None,
    seed: Optional[int] = None,
    force_regenerate: bool = False,
    generator_config: Optional[MeshyGeneratorConfig] = None,
    **kwargs: Any,
) -> RawAsset:
    """
    Master generation entry point coordinating Meshy AI Text-to-3D
    and Procedural Botanical Fallback.
    """
    # 1. Resolve species input
====
def generate_plant(
    species: Union[PlantSpecies, str],
    mode: Literal["auto", "meshy", "procedural"] = "auto",
    output_dir: Optional[Union[str, Path]] = None,
    seed: Optional[int] = None,
    force_regenerate: bool = False,
    generator_config: Optional[MeshyGeneratorConfig] = None,
    **kwargs: Any,
) -> RawAsset:
    """
    Master generation entry point coordinating Meshy AI Text-to-3D
    and Procedural Botanical Fallback.
    """
    # 0. Validate generation mode
    if mode not in ("auto", "meshy", "procedural"):
        raise ValueError(
            f"Invalid generation mode '{mode}'. Expected one of: 'auto', 'meshy', 'procedural'"
        )

    # 1. Resolve species input
>>>>
```

#### Diff 2: `vegetation_pipeline/catalog.py`
```python
<<<<
    ai_model: str = Field(default="meshy-4", description="Meshy model tier")
====
    ai_model: str = Field(default="meshy-6", description="Meshy model tier")
>>>>
```

#### Diff 3: `vegetation_pipeline/taxonomy_catalog.json`
Replace all 35 occurrences:
```json
<<<<
        "ai_model": "meshy-4",
====
        "ai_model": "meshy-6",
>>>>
```

#### Diff 4: `tests/test_generator.py`
```python
<<<<
        assert gen.config.ai_model == "meshy-4"
====
        assert gen.config.ai_model == "meshy-6"
>>>>

<<<<
            assert payload["ai_model"] == "meshy-4"
====
            assert payload["ai_model"] == "meshy-6"
>>>>
```

#### Diff 5: `tests/test_catalog.py`
```python
<<<<
            assert spec.ai_model == "meshy-4"
====
            assert spec.ai_model == "meshy-6"
>>>>
```

---

### New Unit Tests to Add to `tests/test_generator.py`

```python
    def test_meshy_retry_after_strictly_capped_at_backoff_max_seconds(self):
        """Verifies that large Retry-After values (e.g. 86400s) are clamped to backoff_max_seconds."""
        cfg = MeshyGeneratorConfig(api_key="msy_test", backoff_max_seconds=15.0, max_retries=2)
        gen = MeshyGenerator(config=cfg)
        sleep_intervals = []
        err_429 = urllib.error.HTTPError(
            "https://api.meshy.ai", 429, "Too Many Requests",
            {"Retry-After": "86400"}, io.BytesIO(b'{"message": "Rate limit exceeded"}')
        )
        calls = [0]

        def mock_urlopen(req, **kwargs):
            calls[0] += 1
            if calls[0] == 1:
                raise err_429
            resp = MagicMock()
            resp.read.return_value = json.dumps({"result": "ok"}).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), \
             patch("time.sleep", side_effect=sleep_intervals.append):
            res = gen._request_with_retry("POST", "https://api.meshy.ai/test", headers={})
            assert res["result"] == "ok"
            assert len(sleep_intervals) == 1
            assert sleep_intervals[0] == 15.0  # Strictly capped at backoff_max_seconds

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 405, 409, 413, 415, 422])
    def test_meshy_all_non_429_client_errors_fail_fast(self, status_code):
        """Verifies that all 4xx client errors except 429 fail fast on attempt 1 without sleeping."""
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", max_retries=5))
        sleep_mock = MagicMock()
        err = urllib.error.HTTPError(
            "https://api.meshy.ai", status_code, f"Client Error {status_code}",
            {}, io.BytesIO(f'{{"error": "{status_code}"}}'.encode("utf-8"))
        )
        with patch("urllib.request.urlopen", side_effect=err), patch("time.sleep", sleep_mock):
            with pytest.raises(RuntimeError) as exc_info:
                gen._request_with_retry("POST", "https://api.meshy.ai/test", headers={})
            assert str(status_code) in str(exc_info.value)
            sleep_mock.assert_not_called()

    def test_meshy_generate_raises_on_armature_or_skinning_violation(self, sample_oak_species, tmp_path):
        """Verifies that MeshyGenerator.generate() raises RuntimeError if downloaded GLB contains skins or bones."""
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test"))
        out_dir = tmp_path / "rigged_test"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Create a synthetic GLB with a 'skins' entry
        gltf_dict = {
            "asset": {"version": "2.0"},
            "skins": [{"joints": [0]}],
            "nodes": [{"name": "RootJoint"}],
            "meshes": [],
        }
        json_bytes = json.dumps(gltf_dict).encode("utf-8")
        pad = (4 - (len(json_bytes) % 4)) % 4
        json_bytes += b" " * pad

        total_len = 12 + 8 + len(json_bytes)
        header = struct.pack("<4sII", b"glTF", 2, total_len)
        chunk0_header = struct.pack("<II", len(json_bytes), 0x4E4F534A)
        mock_rigged_glb = header + chunk0_header + json_bytes

        def mock_urlopen(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            resp = MagicMock()
            if "/openapi/v2/text-to-3d" in url and getattr(req, "method", "GET") == "POST":
                resp.read.return_value = json.dumps({"result": "task_prev"}).encode("utf-8")
            elif "/openapi/v2/text-to-3d/task_prev" in url:
                resp.read.return_value = json.dumps({
                    "status": "SUCCEEDED",
                    "model_urls": {"glb": "https://assets.meshy.ai/model.glb"},
                }).encode("utf-8")
            elif "model.glb" in url:
                resp.read.side_effect = [mock_rigged_glb, b""]
            else:
                resp.read.return_value = b"{}"
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            with pytest.raises(RuntimeError) as exc_info:
                gen.generate(sample_oak_species, output_dir=out_dir)
            assert "static mesh invariant" in str(exc_info.value).lower()

    @pytest.mark.parametrize("invalid_mode", ["invalid", "mesh", "procedurial", "hybrid", ""])
    def test_generate_plant_invalid_mode_raises_value_error(self, sample_oak_species, invalid_mode):
        """Verifies that invalid mode arguments raise ValueError with an informative message."""
        with pytest.raises(ValueError) as exc_info:
            generate_plant(sample_oak_species, mode=invalid_mode)
        assert "invalid generation mode" in str(exc_info.value).lower()
```

---

## 5. Verification Method

To independently verify the implementation after Worker 2 applies the changes:

1. **Verify Catalog Model Tier Consistency**:
   ```powershell
   uv run pytest teamwork_projects/vegetation_library/tests/test_catalog.py -v
   ```
   *Expected*: All 52 tests pass (including `test_meshy_inference_parameters` asserting `meshy-6`).

2. **Verify Generator Test Suite**:
   ```powershell
   uv run pytest teamwork_projects/vegetation_library/tests/test_generator.py -v
   ```
   *Expected*: All generator unit and integration tests pass cleanly.

3. **Verify Rate Limit Capping & Error Fast-Fail Specifically**:
   ```powershell
   uv run pytest teamwork_projects/vegetation_library/tests/test_generator.py -k "test_meshy_retry_after_strictly_capped_at_backoff_max_seconds or test_meshy_all_non_429_client_errors_fail_fast or test_meshy_generate_raises_on_armature_or_skinning_violation or test_generate_plant_invalid_mode_raises_value_error" -v
   ```
   *Expected*: All targeted tests pass with zero sleep hangs or unhandled retries.

4. **Verify Whole Vegetation Library Suite**:
   ```powershell
   uv run pytest teamwork_projects/vegetation_library/tests/ -v
   ```
   *Expected*: 100% tests pass (exit code 0).

5. **Invalidation Conditions**:
   - Any reference to `meshy-4` remaining in `generator.py`, `catalog.py`, `taxonomy_catalog.json`, or test files.
   - `Retry-After: 86400` causing `sleep` $> \text{backoff\_max\_seconds}$.
   - Non-429 4xx status codes triggering retries instead of immediate fast-fail.
   - Rigged or skinned GLB files passing through `MeshyGenerator.generate()` without raising `RuntimeError`.
   - Invalid mode arguments passing silently to auto fallback without raising `ValueError`.
