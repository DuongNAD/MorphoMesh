"""
Vegetation Library - Generation Engine & Fallback Harness
File: teamwork_projects/vegetation_library/vegetation_pipeline/generator.py

Provides:
1. RawAsset - Data structure representing un-normalized raw 3D botanical asset.
2. MeshyGenerator - Two-stage Text-to-3D Meshy AI client (preview + refine/boost)
   with resilient polling, exponential backoff on HTTP 429/5xx, species-keyed disk caching,
   and static mesh guarantee.
3. ProceduralBotanicalGenerator - Offline deterministic 3D procedural plant generator
   supporting all 7 botanical categories with authentic morphology, PBR texture synthesis,
   Z_min = 0.0 ground alignment, and vertex budget [3000, 45000].
4. generate_plant - Master dispatch coordinating Meshy AI Text-to-3D and Procedural Fallback.
"""
from __future__ import annotations

import io
import json
import logging
import math
import os
from pathlib import Path
import random
import struct
import time
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from morphomesh.connectors.tripo_connector import extract_glb_textures
from morphomesh.geometry.mesh import MeshGeometry
from morphomesh.geometry.quad_utils import add_quad_cap, add_quad_ellipsoid, compute_quad_metrics
from vegetation_pipeline.catalog import (
    PlantSpecies,
    get_catalog,
    get_species,
    UNIVERSAL_NEGATIVE_BLACKLIST,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("vegetation_pipeline.generator")


# ==============================================================================
# BINARY GLB PARSING & VALIDATION UTILITIES
# ==============================================================================

def unpack_glb_header_and_json(glb_path: Union[str, Path]) -> Tuple[Dict[str, Any], bytes]:
    """Unpacks glTF 2.0 header and JSON chunk from a binary GLB file."""
    with open(glb_path, "rb") as f:
        header = f.read(12)
        if len(header) < 12:
            raise ValueError(f"File too short to be valid GLB container: {glb_path}")
        magic, version, length = struct.unpack_from("<4sII", header, 0)
        if magic != b"glTF" or version != 2:
            raise ValueError(f"Invalid GLB header in {glb_path}: magic={magic}, version={version}")

        chunk0_hdr = f.read(8)
        if len(chunk0_hdr) < 8:
            raise ValueError("Missing JSON chunk header in GLB container")
        chunk0_len, chunk0_type = struct.unpack_from("<I4s", chunk0_hdr, 0)
        if chunk0_type != b"JSON":
            raise ValueError(f"Expected chunk 0 to be JSON, got {chunk0_type}")

        json_bytes = f.read(chunk0_len)
        gltf = json.loads(json_bytes.decode("utf-8"))

        bin_bytes = b""
        chunk1_hdr = f.read(8)
        if len(chunk1_hdr) == 8:
            chunk1_len, chunk1_type = struct.unpack_from("<I4s", chunk1_hdr, 0)
            if chunk1_type.startswith(b"BIN"):
                bin_bytes = f.read(chunk1_len)

    return gltf, bin_bytes


def parse_glb_vertex_and_face_counts(glb_path: Union[str, Path]) -> Tuple[int, int]:
    """Parses total vertex and face count from GLB accessors."""
    try:
        gltf, _ = unpack_glb_header_and_json(glb_path)
        accessors = gltf.get("accessors", [])
        total_verts = 0
        total_faces = 0

        for mesh in gltf.get("meshes", []):
            for prim in mesh.get("primitives", []):
                pos_idx = prim.get("attributes", {}).get("POSITION")
                if pos_idx is not None and pos_idx < len(accessors):
                    total_verts += accessors[pos_idx].get("count", 0)

                idx_idx = prim.get("indices")
                if idx_idx is not None and idx_idx < len(accessors):
                    idx_count = accessors[idx_idx].get("count", 0)
                    total_faces += idx_count // 3
                elif pos_idx is not None:
                    pos_count = accessors[pos_idx].get("count", 0)
                    total_faces += pos_count // 3

        return total_verts, total_faces
    except Exception as e:
        logger.debug("Failed parsing GLB metrics for %s: %s", glb_path, e)
        return 0, 0


# ==============================================================================
# DATA STRUCTURES & CONFIGURATIONS
# ==============================================================================

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

    @property
    def albedo(self) -> Optional[Image.Image]:
        return self.textures.get("albedo") or self.textures.get("baseColor")

    @property
    def normal(self) -> Optional[Image.Image]:
        return self.textures.get("normal")

    @property
    def roughness(self) -> Optional[Image.Image]:
        return self.textures.get("roughness")

    @property
    def metallic(self) -> Optional[Image.Image]:
        return self.textures.get("metallic")


class MeshyGeneratorConfig(BaseModel):
    """Configuration options for MeshyGenerator."""
    model_config = ConfigDict(extra="ignore")

    api_key: Optional[str] = None
    base_url: str = "https://api.meshy.ai"
    ai_model: str = "meshy-6"
    art_style: str = "realistic"
    topology: Literal["quad", "triangle"] = "quad"
    target_polycount: int = 28000
    enable_pbr: bool = True
    texture_richness: str = "high"
    cache_dir: Optional[Path] = None
    use_cache: bool = True
    force_regenerate: bool = False
    preview_timeout_seconds: float = 300.0
    refine_timeout_seconds: float = 450.0
    polling_interval_seconds: float = 2.5
    max_retries: int = 5
    backoff_base_seconds: float = 2.0
    backoff_max_seconds: float = 60.0


class ProceduralGeneratorConfig(BaseModel):
    """Configuration options for ProceduralBotanicalGenerator."""
    model_config = ConfigDict(extra="ignore")

    seed: Optional[Union[int, str]] = None
    texture_resolution: int = 512
    target_vertex_count: int = 8000


# ==============================================================================
# MESHY AI GENERATION ENGINE
# ==============================================================================

class MeshyGenerator:
    """
    Two-stage Meshy AI Text-to-3D client (preview + refine/boost)
    with polling, exponential backoff on HTTP 429/5xx, and species-keyed disk caching.
    """

    def __init__(
        self,
        config: Optional[MeshyGeneratorConfig] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.config = config.model_copy() if config is not None else MeshyGeneratorConfig()
        if api_key:
            self.config.api_key = api_key

    def resolve_api_key(self) -> Optional[str]:
        """Resolves Meshy API key from config or environment."""
        if self.config.api_key:
            return self.config.api_key.strip().strip("'\"")
        env_key = os.environ.get("MESHY_API_KEY") or os.environ.get("MESHY_AI_API_KEY")
        if env_key:
            return env_key.strip().strip("'\"")
        return None

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
        import urllib.error
        import urllib.request

        attempt = 0
        while True:
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=30.0) as resp:
                    body = resp.read().decode("utf-8")
                    return json.loads(body)
            except urllib.error.HTTPError as e:
                # Terminal client errors: fail fast without retry (all 4xx except 429 Rate Limit)
                if 400 <= e.code < 500 and e.code != 429:
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

                retry_after: Optional[float] = None
                if hasattr(e, "headers") and e.headers and "Retry-After" in e.headers:
                    try:
                        retry_after = float(e.headers["Retry-After"])
                    except (ValueError, TypeError):
                        pass

                base_delay = self.config.backoff_base_seconds * (2 ** (attempt - 1))
                jitter = random.uniform(0.0, 0.5)
                delay = base_delay + jitter
                if retry_after is not None:
                    delay = max(delay, retry_after)
                delay = min(self.config.backoff_max_seconds, delay)

                logger.warning(
                    "Meshy API returned HTTP %s on %s. Retrying in %.2fs (attempt %d/%d)...",
                    e.code, url, delay, attempt, self.config.max_retries,
                )
                time.sleep(delay)

            except (urllib.error.URLError, TimeoutError, OSError) as e:
                attempt += 1
                if attempt > self.config.max_retries:
                    raise RuntimeError(
                        f"Meshy API request exceeded max retries ({self.config.max_retries}): network error {e}"
                    )
                base_delay = self.config.backoff_base_seconds * (2 ** (attempt - 1))
                delay = min(self.config.backoff_max_seconds, base_delay)
                logger.warning("Transient network error %s. Retrying in %.2fs...", e, delay)
                time.sleep(delay)

    def _submit_preview(self, species: PlantSpecies, api_key: str) -> str:
        """Submits Stage 1 preview text-to-3d generation task."""
        url = f"{self.config.base_url.rstrip('/')}/openapi/v2/text-to-3d"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "mode": "preview",
            "prompt": species.meshy_spec.positive_prompt,
            "negative_prompt": species.meshy_spec.negative_prompt,
            "art_style": self.config.art_style,
            "ai_model": self.config.ai_model,
            "topology": self.config.topology,
            "target_polycount": species.meshy_spec.target_polycount,
            "should_remesh": True,
        }
        data = json.dumps(payload).encode("utf-8")
        resp = self._request_with_retry("POST", url, headers=headers, data=data)
        task_id = resp.get("result")
        if not task_id:
            raise RuntimeError(f"Meshy preview submission failed to return task ID: {resp}")
        return task_id

    def _submit_refine(self, preview_task_id: str, api_key: str) -> str:
        """Submits Stage 2 refine text-to-3d generation task."""
        url = f"{self.config.base_url.rstrip('/')}/openapi/v2/text-to-3d"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "mode": "refine",
            "preview_task_id": preview_task_id,
            "enable_pbr": self.config.enable_pbr,
            "texture_richness": self.config.texture_richness,
        }
        data = json.dumps(payload).encode("utf-8")
        resp = self._request_with_retry("POST", url, headers=headers, data=data)
        refine_id = resp.get("result")
        if not refine_id:
            raise RuntimeError(f"Meshy refine submission failed to return task ID: {resp}")
        return refine_id

    def _poll_task(self, task_id: str, api_key: str, timeout_seconds: float) -> Dict[str, Any]:
        """Polls a Meshy task until status reaches SUCCEEDED."""
        url = f"{self.config.base_url.rstrip('/')}/openapi/v2/text-to-3d/{task_id}"
        headers = {"Authorization": f"Bearer {api_key}"}
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(f"Meshy task {task_id} timed out after {timeout_seconds}s")

            task = self._request_with_retry("GET", url, headers=headers)
            status = task.get("status")
            if status == "SUCCEEDED":
                return task
            elif status in ("FAILED", "EXPIRED"):
                msg = task.get("task_error", {}).get("message") or task.get("message") or "Unknown error"
                raise RuntimeError(f"Meshy task {task_id} failed with status '{status}': {msg}")

            time.sleep(self.config.polling_interval_seconds)

    def _download_file(self, url: str, target_path: Path) -> None:
        """Downloads a remote binary file from URL to disk."""
        import urllib.request
        target_path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "MorphoMesh-Vegetation-Engine/1.0"})
        with urllib.request.urlopen(req, timeout=60.0) as resp, open(target_path, "wb") as out_f:
            while chunk := resp.read(65536):
                out_f.write(chunk)

    def _verify_static_mesh(self, glb_path: Union[str, Path]) -> bool:
        """Verifies that downloaded GLB contains ZERO skeletal armatures or skinning weights."""
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

    def _download_or_extract_textures(
        self,
        task_data: Dict[str, Any],
        glb_path: Path,
        out_dir: Path,
        species: PlantSpecies,
    ) -> Tuple[Dict[str, Image.Image], Dict[str, Path]]:
        """Downloads textures from task URLs or extracts them from GLB buffer views."""
        tex_dir = out_dir / "textures"
        tex_dir.mkdir(parents=True, exist_ok=True)
        textures: Dict[str, Image.Image] = {}
        texture_paths: Dict[str, Path] = {}

        # 1. Download separate texture URLs if provided by Meshy
        raw_tex_urls = task_data.get("texture_urls", {})
        tex_urls: Dict[str, str] = {}
        if isinstance(raw_tex_urls, dict):
            tex_urls = raw_tex_urls
        elif isinstance(raw_tex_urls, list):
            for item in raw_tex_urls:
                if isinstance(item, dict):
                    tex_urls.update(item)
        url_channel_map = {
            "albedo": ["albedo", "base_color", "baseColor"],
            "normal": ["normal", "bump"],
            "roughness": ["roughness", "rough"],
            "metallic": ["metallic", "metal"],
        }
        for channel, aliases in url_channel_map.items():
            for alias in aliases:
                u = tex_urls.get(alias)
                if u:
                    t_path = tex_dir / f"{channel}.png"
                    try:
                        self._download_file(u, t_path)
                        textures[channel] = Image.open(t_path).convert("RGB" if channel != "roughness" and channel != "metallic" else "L")
                        texture_paths[channel] = t_path
                        break
                    except Exception as e:
                        logger.debug("Failed downloading %s texture: %s", channel, e)

        # 2. Extract embedded GLB textures if any missing
        if len(textures) < 4:
            try:
                extracted = extract_glb_textures(str(glb_path), str(tex_dir), prefix=species.species_id)
                if extracted:
                    for attr in ["albedo", "normal", "roughness", "metallic"]:
                        p = getattr(extracted, f"{attr}_path", getattr(extracted, attr, None))
                        if p and Path(p).is_file() and attr not in textures:
                            try:
                                textures[attr] = Image.open(p)
                                texture_paths[attr] = Path(p)
                            except Exception:
                                pass
            except Exception as e:
                logger.debug("Could not extract embedded textures: %s", e)

        # 3. Procedural fallback for any remaining missing channels
        if len(textures) < 4:
            proc_gen = ProceduralBotanicalGenerator()
            fallback_tex = proc_gen._generate_pbr_textures(species, np.random.RandomState(42))
            for k, img in fallback_tex.items():
                if k not in textures:
                    target_p = tex_dir / f"{k}.png"
                    img.save(target_p)
                    textures[k] = img
                    texture_paths[k] = target_p

        return textures, texture_paths

    def check_cache(
        self,
        species: PlantSpecies,
        target_dir: Optional[Union[str, Path]] = None,
        expected_source: Optional[str] = None,
    ) -> Optional[RawAsset]:
        """
        Checks if a valid, complete generated asset already exists in local disk cache.
        Verifies binary GLB header (magic == b'glTF', version == 2), texture completeness,
        manifest JSON integrity, and source provenance.
        """
        if self.config.force_regenerate or not self.config.use_cache:
            return None

        candidates: List[Path] = []
        if target_dir is not None:
            p = Path(target_dir)
            candidates.append(p)
            candidates.append(p / species.species_id)
        if self.config.cache_dir is not None:
            candidates.append(self.config.cache_dir / species.species_id)
            candidates.append(self.config.cache_dir)
        candidates.append(Path("./teamwork_projects/vegetation_library/.cache/meshy") / species.species_id)

        for cand in candidates:
            glb_path = cand / f"{species.species_id}.glb"
            if not glb_path.is_file():
                continue

            # Binary GLB Header Verification (read 12 bytes, assert magic == b"glTF" and version == 2)
            try:
                file_size = glb_path.stat().st_size
                if file_size < 12:
                    continue
                with open(glb_path, "rb") as f:
                    header = f.read(12)
                if len(header) < 12:
                    continue
                magic, version, total_length = struct.unpack_from("<4sII", header, 0)
                if magic != b"glTF" or version != 2:
                    logger.warning(
                        "Cache GLB at %s has invalid header (magic=%s, version=%s)",
                        glb_path, magic, version
                    )
                    continue
                if total_length > file_size:
                    logger.warning(
                        "Cache GLB at %s is truncated (header length %d > file size %d)",
                        glb_path, total_length, file_size
                    )
                    continue
            except (OSError, struct.error) as e:
                logger.warning("Error verifying GLB header at %s: %s", glb_path, e)
                continue

            # Check texture files
            tex_dir = cand / "textures"
            required_channels = ["albedo", "normal", "roughness", "metallic"]
            loaded_textures: Dict[str, Image.Image] = {}
            loaded_paths: Dict[str, Path] = {}
            all_channels_ok = True

            for ch in required_channels:
                possibilities = [
                    tex_dir / f"{ch}.png",
                    tex_dir / f"{species.species_id}_{ch}.png",
                    cand / f"{ch}.png",
                    cand / f"{species.species_id}_{ch}.png",
                ]
                found = next((f for f in possibilities if f.is_file() and f.stat().st_size > 0), None)
                if found is None:
                    all_channels_ok = False
                    break
                try:
                    img = Image.open(found)
                    img.load()
                    loaded_textures[ch] = img
                    loaded_paths[ch] = found
                except Exception:
                    all_channels_ok = False
                    break

            if not all_channels_ok or len(loaded_textures) != 4:
                continue

            # Read manifest & verify JSON integrity
            manifest_path = cand / "cache_manifest.json"
            manifest_data: Dict[str, Any] = {}
            if manifest_path.is_file():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest_data = json.load(f)
                except Exception as e:
                    logger.warning(
                        "Corrupted or invalid JSON manifest at %s: %s. Treating as cache miss.",
                        manifest_path, e
                    )
                    continue
            elif expected_source is not None:
                # If an expected provenance is required, missing manifest cannot satisfy it
                continue

            # Provenance source check
            if expected_source is not None:
                manifest_source = (
                    manifest_data.get("provenance", {}).get("source")
                    if isinstance(manifest_data.get("provenance"), dict)
                    else None
                ) or manifest_data.get("source")
                if manifest_source != expected_source:
                    logger.debug(
                        "Cache candidate at %s rejected: source '%s' does not match expected '%s'",
                        cand, manifest_source, expected_source
                    )
                    continue

            verts, faces = parse_glb_vertex_and_face_counts(glb_path)
            if verts == 0 and "vertex_count" in manifest_data:
                verts = manifest_data["vertex_count"]
            if faces == 0 and "face_count" in manifest_data:
                faces = manifest_data["face_count"]

            return RawAsset(
                species_id=species.species_id,
                glb_path=glb_path,
                mesh=None,
                textures=loaded_textures,
                texture_paths=loaded_paths,
                source="cached",
                vertex_count=verts,
                face_count=faces,
                metadata=manifest_data,
            )

        return None

    def generate(
        self,
        species: PlantSpecies,
        output_dir: Optional[Union[str, Path]] = None,
        force_regenerate: bool = False,
    ) -> RawAsset:
        """Executes full two-stage Meshy AI Text-to-3D generation workflow."""
        out_path = Path(output_dir) if output_dir is not None else (
            (self.config.cache_dir / species.species_id) if self.config.cache_dir
            else Path("./output") / species.short_category / species.species_id
        )
        out_path.mkdir(parents=True, exist_ok=True)

        # 1. Resolve credentials
        api_key = self.resolve_api_key()
        if not api_key:
            raise RuntimeError("MESHY_API_KEY API key environment variable is not set")

        # 2. Disk caching check (Meshy provenance only)
        if not force_regenerate and not self.config.force_regenerate and self.config.use_cache:
            cached = self.check_cache(species, target_dir=out_path, expected_source="meshy")
            if cached is not None:
                logger.info("Cache hit for species %s at %s", species.species_id, out_path)
                return cached

        # 3. Two-stage Text-to-3D generation
        logger.info("Submitting Meshy preview task for %s...", species.species_id)
        preview_task_id = self._submit_preview(species, api_key=api_key)
        preview_task = self._poll_task(preview_task_id, api_key=api_key, timeout_seconds=self.config.preview_timeout_seconds)

        logger.info("Submitting Meshy refine task for %s (preview=%s)...", species.species_id, preview_task_id)
        refine_task_id = self._submit_refine(preview_task_id, api_key=api_key)
        refine_task = self._poll_task(refine_task_id, api_key=api_key, timeout_seconds=self.config.refine_timeout_seconds)

        # 4. Download 3D Model
        glb_url = refine_task.get("model_urls", {}).get("glb") or preview_task.get("model_urls", {}).get("glb")
        if not glb_url:
            raise RuntimeError(f"Meshy refine task {refine_task_id} completed without model_urls.glb")

        glb_path = out_path / f"{species.species_id}.glb"
        self._download_file(glb_url, glb_path)

        # 5. Static mesh invariant enforcement
        if not self._verify_static_mesh(glb_path):
            raise RuntimeError(
                f"Meshy generated asset at {glb_path} violates static mesh invariant (contains bones, skins, or animations)"
            )

        # 6. Textures download/extract
        textures, texture_paths = self._download_or_extract_textures(refine_task, glb_path, out_path, species)

        verts, faces = parse_glb_vertex_and_face_counts(glb_path)

        # 7. Write manifest
        manifest = {
            "species_id": species.species_id,
            "preview_task_id": preview_task_id,
            "refine_task_id": refine_task_id,
            "vertex_count": verts,
            "face_count": faces,
            "source": "meshy",
            "textures": {k: str(v.relative_to(out_path)) for k, v in texture_paths.items()},
        }
        with open(out_path / "cache_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return RawAsset(
            species_id=species.species_id,
            glb_path=glb_path,
            mesh=None,
            textures=textures,
            texture_paths=texture_paths,
            source="meshy",
            vertex_count=verts,
            face_count=faces,
            metadata=manifest,
        )


# ==============================================================================
# PROCEDURAL BOTANICAL GENERATOR (OFFLINE DETERMINISTIC FALLBACK)
# ==============================================================================

class ProceduralBotanicalGenerator:
    """
    Offline deterministic 3D procedural botanical generator.
    Produces unrigged, grounded static botanical assets across all 7 biomes.
    """

    def __init__(
        self,
        config: Optional[ProceduralGeneratorConfig] = None,
        seed: Optional[Union[int, str]] = None,
        texture_resolution: int = 512,
    ) -> None:
        self.config = config.model_copy() if config is not None else ProceduralGeneratorConfig()
        if seed is not None:
            self.config.seed = seed
        if texture_resolution:
            self.config.texture_resolution = texture_resolution

    def generate(
        self,
        species: PlantSpecies,
        output_dir: Optional[Union[str, Path]] = None,
        seed: Optional[Union[int, str]] = None,
    ) -> RawAsset:
        """Generates static 3D mesh and 4-channel PBR textures for a botanical species."""
        raw_seed = seed if seed is not None else self.config.seed
        if raw_seed is not None:
            if isinstance(raw_seed, (int, np.integer)):
                active_seed = abs(int(raw_seed)) % (2**32)
            elif isinstance(raw_seed, (float, np.floating)):
                active_seed = abs(int(raw_seed)) % (2**32)
            else:
                try:
                    active_seed = abs(int(raw_seed)) % (2**32)
                except (ValueError, TypeError):
                    active_seed = abs(hash(str(raw_seed))) % (2**32)
        else:
            active_seed = abs(hash(species.species_id)) % (2**31 - 1)

        rng = np.random.RandomState(active_seed)

        # 1. Dispatch procedural mesh generation by botanical category
        mesh = self._generate_category_mesh(species, rng)

        # 2. Enforce strict invariants: ground contact Z_min = 0.0 and base centering at origin
        mesh = self._enforce_mesh_invariants(mesh, target_height=species.dimensions.height_m)

        # 3. Procedural 4-channel PBR texture synthesis
        textures = self._generate_pbr_textures(species, rng, resolution=self.config.texture_resolution)

        # 4. Save to output directory
        out_path = Path(output_dir) if output_dir is not None else Path("./output") / species.short_category / species.species_id
        out_path.mkdir(parents=True, exist_ok=True)

        glb_path = out_path / f"{species.species_id}.glb"
        mesh.export_glb(str(glb_path))

        tex_dir = out_path / "textures"
        tex_dir.mkdir(parents=True, exist_ok=True)
        texture_paths: Dict[str, Path] = {}
        for name, img in textures.items():
            tp = tex_dir / f"{name}.png"
            img.save(tp)
            texture_paths[name] = tp

        # 5. Build telemetry metadata
        quad_count, tri_count, quad_ratio = compute_quad_metrics(mesh)
        metadata = {
            "species_id": species.species_id,
            "category_id": species.category_id,
            "source": "procedural",
            "seed": active_seed,
            "vertex_count": len(mesh.vertices),
            "face_count": len(mesh.faces),
            "quad_count": quad_count,
            "tri_count": tri_count,
            "quad_ratio": quad_ratio,
        }

        # Write cache manifest
        manifest = {
            "species_id": species.species_id,
            "source": "procedural",
            "seed": active_seed,
            "vertex_count": len(mesh.vertices),
            "face_count": len(mesh.faces),
            "textures": {k: f"textures/{k}.png" for k in textures},
        }
        with open(out_path / "cache_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return RawAsset(
            species_id=species.species_id,
            glb_path=glb_path,
            mesh=mesh,
            textures=textures,
            texture_paths=texture_paths,
            source="procedural",
            vertex_count=len(mesh.vertices),
            face_count=len(mesh.faces),
            metadata=metadata,
        )

    def _generate_category_mesh(self, species: PlantSpecies, rng: np.random.RandomState) -> MeshGeometry:
        cat = species.short_category
        if cat in ("broadleaf_trees", "broadleaf_deciduous_trees", "broadleaf"):
            return self._build_broadleaf_tree(species, rng)
        elif cat in ("conifers", "conifers_evergreens"):
            return self._build_conifer(species, rng)
        elif cat in ("tropical", "tropical_foliage_palms"):
            return self._build_tropical(species, rng)
        elif cat in ("shrubs", "flowering_shrubs_ornamentals"):
            return self._build_shrub(species, rng)
        elif cat in ("groundcover", "ferns_grasses_groundcover"):
            return self._build_groundcover(species, rng)
        elif cat in ("succulents", "succulents_cacti"):
            return self._build_succulent(species, rng)
        elif cat in ("vines", "climbing_vines_epiphytes"):
            return self._build_vine(species, rng)
        else:
            return self._build_broadleaf_tree(species, rng)

    def _build_broadleaf_tree(self, species: PlantSpecies, rng: np.random.RandomState) -> MeshGeometry:
        """Category 1: Broadleaf Trees (trunk + primary boughs + quad-ellipsoid crowns + leaf cards)."""
        mesh = MeshGeometry()
        H = species.dimensions.height_m
        R_base = 0.5 * species.dimensions.trunk_stem_diameter_m
        trunk_h = 0.35 * H

        # 1. Trunk cylinder with basal flare
        n_rings = 16
        n_radial = 16
        ring_indices: List[List[int]] = []
        for r in range(n_rings):
            t = r / (n_rings - 1)
            z = t * trunk_h
            r_z = R_base * (1.0 - 0.35 * t + 0.15 * math.exp(-z / max(0.1, 0.5 * trunk_h)))
            cring = []
            for s in range(n_radial):
                ang = 2.0 * math.pi * s / n_radial
                px = r_z * math.cos(ang)
                py = r_z * math.sin(ang)
                idx = mesh.add_vertex((px, py, z), (math.cos(ang), math.sin(ang), 0.0), (s / n_radial, t * 0.4))
                cring.append(idx)
            ring_indices.append(cring)
            if r > 0:
                for s in range(n_radial):
                    ns = (s + 1) % n_radial
                    mesh.add_quad(ring_indices[r-1][s], ring_indices[r-1][ns], ring_indices[r][ns], ring_indices[r][s])
        add_quad_cap(mesh, ring_indices[0], flip_normal=True)

        # 2. Primary Boughs
        num_boughs = 6
        for b in range(num_boughs):
            theta = 2.0 * math.pi * b / num_boughs + rng.uniform(-0.15, 0.15)
            spread = species.dimensions.canopy_spread_m * 0.45
            p0 = (0.0, 0.0, trunk_h)
            p1 = (spread * 0.5 * math.cos(theta), spread * 0.5 * math.sin(theta), trunk_h + 0.3 * (H - trunk_h))
            p2 = (spread * math.cos(theta), spread * math.sin(theta), trunk_h + 0.65 * (H - trunk_h))

            b_rings = 8
            b_radial = 8
            b_indices = []
            for br in range(b_rings):
                t = br / (b_rings - 1)
                bx = (1 - t)**2 * p0[0] + 2 * t * (1 - t) * p1[0] + t**2 * p2[0]
                by = (1 - t)**2 * p0[1] + 2 * t * (1 - t) * p1[1] + t**2 * p2[1]
                bz = (1 - t)**2 * p0[2] + 2 * t * (1 - t) * p1[2] + t**2 * p2[2]
                rad = R_base * (0.35 * (1 - t) + 0.12)
                cring = []
                for bs in range(b_radial):
                    bang = 2.0 * math.pi * bs / b_radial
                    cring.append(mesh.add_vertex(
                        (bx + rad * math.cos(bang), by + rad * math.sin(bang), bz),
                        (math.cos(bang), math.sin(bang), 0.0),
                        (bs / b_radial, t),
                    ))
                b_indices.append(cring)
                if br > 0:
                    for bs in range(b_radial):
                        nbs = (bs + 1) % b_radial
                        mesh.add_quad(b_indices[br-1][bs], b_indices[br-1][nbs], b_indices[br][nbs], b_indices[br][bs])

        # 3. Volumetric Quad Subcrowns
        canopy_spread = max(0.01, getattr(species.dimensions, "canopy_spread_m", 1.0))
        num_subcrowns = 22
        for sc in range(num_subcrowns):
            theta = sc * (2.0 * math.pi / num_subcrowns) + rng.uniform(-0.2, 0.2)
            dist = rng.uniform(0.3, 0.9) * canopy_spread * 0.5
            cz = trunk_h + rng.uniform(0.3, 0.9) * (H - trunk_h)
            cx = dist * math.cos(theta)
            cy = dist * math.sin(theta)
            cr = rng.uniform(0.08, 0.15) * canopy_spread
            add_quad_ellipsoid(mesh, (cx, cy, cz), (cr, cr, cr * 0.8), rings=5, sectors=8)

        # 4. Crossed Foliage Leaf Cards
        num_cards = 700
        for _ in range(num_cards):
            phi = rng.uniform(-math.pi / 3, math.pi / 2)
            theta = rng.uniform(0, 2 * math.pi)
            cr_xy = species.dimensions.canopy_spread_m * 0.5 * math.cos(phi) * rng.uniform(0.6, 1.05)
            cz = trunk_h + (H - trunk_h) * (0.5 + 0.5 * math.sin(phi)) * rng.uniform(0.7, 1.02)
            cx = cr_xy * math.cos(theta)
            cy = cr_xy * math.sin(theta)
            lw = rng.uniform(0.25, 0.45)
            lh = rng.uniform(0.35, 0.6)

            nx, ny = math.cos(theta), math.sin(theta)
            ux, uy = -ny, nx
            v0 = mesh.add_vertex((cx - 0.5 * lw * ux, cy - 0.5 * lw * uy, cz), (nx, ny, 0.0), (0.55, 0.1))
            v1 = mesh.add_vertex((cx + 0.5 * lw * ux, cy + 0.5 * lw * uy, cz), (nx, ny, 0.0), (0.95, 0.1))
            v2 = mesh.add_vertex((cx + 0.5 * lw * ux, cy + 0.5 * lw * uy, cz + lh), (nx, ny, 0.0), (0.95, 0.9))
            v3 = mesh.add_vertex((cx - 0.5 * lw * ux, cy - 0.5 * lw * uy, cz + lh), (nx, ny, 0.0), (0.55, 0.9))
            mesh.add_quad(v0, v1, v2, v3)

        return mesh

    def _build_conifer(self, species: PlantSpecies, rng: np.random.RandomState) -> MeshGeometry:
        """Category 2: Conifers (central vertical spire + tiered whorls + needle cards)."""
        mesh = MeshGeometry()
        H = species.dimensions.height_m
        R_base = 0.5 * species.dimensions.trunk_stem_diameter_m
        max_spread = species.dimensions.canopy_spread_m * 0.5

        # 1. Central Spire Trunk
        t_rings = 24
        t_rad = 12
        ring_indices: List[List[int]] = []
        for r in range(t_rings):
            t = r / (t_rings - 1)
            z = t * 0.98 * H
            rz = R_base * ((1.0 - t)**0.8 + 0.05)
            cring = []
            for s in range(t_rad):
                ang = 2.0 * math.pi * s / t_rad
                idx = mesh.add_vertex((rz * math.cos(ang), rz * math.sin(ang), z), (math.cos(ang), math.sin(ang), 0.0), (s / t_rad, t * 0.5))
                cring.append(idx)
            ring_indices.append(cring)
            if r > 0:
                for s in range(t_rad):
                    ns = (s + 1) % t_rad
                    mesh.add_quad(ring_indices[r-1][s], ring_indices[r-1][ns], ring_indices[r][ns], ring_indices[r][s])
        add_quad_cap(mesh, ring_indices[0], flip_normal=True)

        # 2. Tiered Descending Whorls
        num_tiers = 12
        for tier in range(num_tiers):
            t_pos = 0.2 + 0.75 * (tier / (num_tiers - 1))
            tz = t_pos * H
            tier_r = max_spread * ((1.0 - (tier / num_tiers))**0.75 + 0.1)
            branches = 8
            for b in range(branches):
                ang = 2.0 * math.pi * b / branches + (tier * 0.3)
                bx = tier_r * math.cos(ang)
                by = tier_r * math.sin(ang)
                bz = tz - 0.15 * tier_r
                b_indices: List[List[int]] = []
                for seg in range(4):
                    st = (seg + 1) / 4.0
                    px = st * bx
                    py = st * by
                    pz = tz + st * (bz - tz)
                    brad = R_base * 0.15 * (1.0 - 0.7 * st)
                    cring: List[int] = []
                    for s in range(4):
                        sa = 2.0 * math.pi * s / 4
                        idx = mesh.add_vertex(
                            (px + brad * math.cos(sa), py + brad * math.sin(sa), pz),
                            (math.cos(sa), math.sin(sa), 0.0),
                            (0.1, st),
                        )
                        cring.append(idx)
                    b_indices.append(cring)
                    if seg > 0:
                        for s in range(4):
                            ns = (s + 1) % 4
                            mesh.add_quad(
                                b_indices[seg - 1][s],
                                b_indices[seg - 1][ns],
                                b_indices[seg][ns],
                                b_indices[seg][s],
                            )
                add_quad_cap(mesh, b_indices[0], flip_normal=True)
                add_quad_cap(mesh, b_indices[-1], flip_normal=False)

        # 3. Needle Sprays
        num_cards = 800
        for _ in range(num_cards):
            tier_frac = rng.uniform(0.18, 0.96)
            tz = tier_frac * H
            tier_r = max_spread * ((1.0 - ((tier_frac - 0.18) / 0.8))**0.75 + 0.1) * rng.uniform(0.6, 1.05)
            ang = rng.uniform(0, 2 * math.pi)
            cx = tier_r * math.cos(ang)
            cy = tier_r * math.sin(ang)
            cz = tz - rng.uniform(0.0, 0.2 * tier_r)

            card_w = rng.uniform(0.3, 0.5)
            card_h = rng.uniform(0.4, 0.7)
            nx, ny = math.cos(ang), math.sin(ang)
            ux, uy = -ny, nx
            v0 = mesh.add_vertex((cx - 0.5 * card_w * ux, cy - 0.5 * card_w * uy, cz), (nx, ny, 0.0), (0.55, 0.1))
            v1 = mesh.add_vertex((cx + 0.5 * card_w * ux, cy + 0.5 * card_w * uy, cz), (nx, ny, 0.0), (0.95, 0.1))
            v2 = mesh.add_vertex((cx + 0.5 * card_w * ux, cy + 0.5 * card_w * uy, cz + card_h), (nx, ny, 0.0), (0.95, 0.9))
            v3 = mesh.add_vertex((cx - 0.5 * card_w * ux, cy - 0.5 * card_w * uy, cz + card_h), (nx, ny, 0.0), (0.55, 0.9))
            mesh.add_quad(v0, v1, v2, v3)

        return mesh

    def _build_tropical(self, species: PlantSpecies, rng: np.random.RandomState) -> MeshGeometry:
        """Category 3: Tropical & Palms (curved pseudostem + radiating compound fronds)."""
        mesh = MeshGeometry()
        H = species.dimensions.height_m
        R_base = 0.5 * species.dimensions.trunk_stem_diameter_m
        spread = species.dimensions.canopy_spread_m * 0.5

        # 1. Curved Trunk / Pseudostem
        t_rings = 20
        t_rad = 16
        ring_indices: List[List[int]] = []
        curve_x = 0.15 * spread
        curve_y = 0.10 * spread
        for r in range(t_rings):
            t = r / (t_rings - 1)
            z = t * 0.90 * H
            cx = curve_x * (t**1.8)
            cy = curve_y * (t**1.8)
            rz = R_base * (1.0 - 0.25 * t)
            cring = []
            for s in range(t_rad):
                ang = 2.0 * math.pi * s / t_rad
                px = cx + rz * math.cos(ang)
                py = cy + rz * math.sin(ang)
                idx = mesh.add_vertex((px, py, z), (math.cos(ang), math.sin(ang), 0.0), (s / t_rad, t * 0.4))
                cring.append(idx)
            ring_indices.append(cring)
            if r > 0:
                for s in range(t_rad):
                    ns = (s + 1) % t_rad
                    mesh.add_quad(ring_indices[r-1][s], ring_indices[r-1][ns], ring_indices[r][ns], ring_indices[r][s])
        add_quad_cap(mesh, ring_indices[0], flip_normal=True)

        # 2. Radiating Compound Fronds
        crown_x = curve_x
        crown_y = curve_y
        crown_z = 0.90 * H
        num_fronds = 18
        for f in range(num_fronds):
            f_theta = f * 2.39996 + rng.uniform(-0.1, 0.1)
            f_len = spread * rng.uniform(0.85, 1.15)
            num_segs = 12
            r_points = []
            for s in range(num_segs + 1):
                st = s / num_segs
                rx = crown_x + st * f_len * math.cos(f_theta)
                ry = crown_y + st * f_len * math.sin(f_theta)
                rz = crown_z + 0.3 * f_len * st - 0.7 * f_len * (st**2)
                r_points.append((rx, ry, rz))

            for s in range(2, num_segs):
                px, py, pz = r_points[s]
                st = s / num_segs
                leaf_l = 0.6 * (1.0 - 0.5 * st)
                dx = math.cos(f_theta + math.pi / 2)
                dy = math.sin(f_theta + math.pi / 2)
                for side in (-1, 1):
                    lx = px + side * leaf_l * dx
                    ly = py + side * leaf_l * dy
                    lz = pz - 0.15 * leaf_l
                    v0 = mesh.add_vertex((px, py, pz), (0, 0, 1), (0.6, 0.2))
                    v1 = mesh.add_vertex((lx, ly, lz), (0, 0, 1), (0.9, 0.2))
                    v2 = mesh.add_vertex((lx + 0.1 * math.cos(f_theta), ly + 0.1 * math.sin(f_theta), lz), (0, 0, 1), (0.9, 0.8))
                    v3 = mesh.add_vertex((px + 0.1 * math.cos(f_theta), py + 0.1 * math.sin(f_theta), pz), (0, 0, 1), (0.6, 0.8))
                    mesh.add_quad(v0, v1, v2, v3)

        # 3. Paddle/Fan Leaf Fill Cards
        num_cards = 550
        for _ in range(num_cards):
            phi = rng.uniform(-0.4, 0.6)
            ang = rng.uniform(0, 2 * math.pi)
            cr_xy = spread * math.cos(phi) * rng.uniform(0.4, 1.0)
            cz = crown_z + spread * math.sin(phi) * rng.uniform(0.3, 0.9)
            cx = crown_x + cr_xy * math.cos(ang)
            cy = crown_y + cr_xy * math.sin(ang)
            lw = rng.uniform(0.25, 0.45)
            lh = rng.uniform(0.4, 0.7)
            nx, ny = math.cos(ang), math.sin(ang)
            ux, uy = -ny, nx
            v0 = mesh.add_vertex((cx - 0.5 * lw * ux, cy - 0.5 * lw * uy, cz), (nx, ny, 0.0), (0.55, 0.1))
            v1 = mesh.add_vertex((cx + 0.5 * lw * ux, cy + 0.5 * lw * uy, cz), (nx, ny, 0.0), (0.95, 0.1))
            v2 = mesh.add_vertex((cx + 0.5 * lw * ux, cy + 0.5 * lw * uy, cz + lh), (nx, ny, 0.0), (0.95, 0.9))
            v3 = mesh.add_vertex((cx - 0.5 * lw * ux, cy - 0.5 * lw * uy, cz + lh), (nx, ny, 0.0), (0.55, 0.9))
            mesh.add_quad(v0, v1, v2, v3)

        return mesh

    def _build_shrub(self, species: PlantSpecies, rng: np.random.RandomState) -> MeshGeometry:
        """Category 4: Flowering Shrubs & Ornamentals (multi-stemmed base + dense mound + blossoms)."""
        mesh = MeshGeometry()
        H = species.dimensions.height_m
        spread = species.dimensions.canopy_spread_m * 0.5
        stem_r = max(0.015, 0.5 * species.dimensions.trunk_stem_diameter_m)

        # 1. Multi-stemmed woody base (10 stems)
        num_stems = 10
        for s in range(num_stems):
            ang = 2.0 * math.pi * s / num_stems + rng.uniform(-0.15, 0.15)
            flare_r = spread * rng.uniform(0.3, 0.6)
            s_rings = 8
            s_rad = 6
            r_indices = []
            for r in range(s_rings):
                t = r / (s_rings - 1)
                sz = t * H * 0.5
                sx = flare_r * t * math.cos(ang)
                sy = flare_r * t * math.sin(ang)
                rad = stem_r * (1.0 - 0.4 * t)
                cring = []
                for sr in range(s_rad):
                    sa = 2.0 * math.pi * sr / s_rad
                    cring.append(mesh.add_vertex((sx + rad * math.cos(sa), sy + rad * math.sin(sa), sz), (math.cos(sa), math.sin(sa), 0.0), (sr / s_rad, t)))
                r_indices.append(cring)
                if r > 0:
                    for sr in range(s_rad):
                        nsr = (sr + 1) % s_rad
                        mesh.add_quad(r_indices[r-1][sr], r_indices[r-1][nsr], r_indices[r][nsr], r_indices[r][sr])

        # 2. Dense foliage subcrowns
        for sc in range(16):
            theta = sc * (2.0 * math.pi / 16) + rng.uniform(-0.2, 0.2)
            dist = spread * rng.uniform(0.3, 0.8)
            cz = H * rng.uniform(0.35, 0.85)
            cx = dist * math.cos(theta)
            cy = dist * math.sin(theta)
            cr = rng.uniform(0.4, 0.8)
            add_quad_ellipsoid(mesh, (cx, cy, cz), (cr, cr, cr * 0.7), rings=4, sectors=8)

        # 3. Foliage leaf cards
        for _ in range(750):
            phi = rng.uniform(-0.3, math.pi / 2)
            theta = rng.uniform(0, 2 * math.pi)
            cr_xy = spread * math.cos(phi) * rng.uniform(0.5, 1.05)
            cz = max(0.05, H * (0.3 + 0.68 * math.sin(phi)) * rng.uniform(0.7, 1.05))
            cx = cr_xy * math.cos(theta)
            cy = cr_xy * math.sin(theta)
            lw = rng.uniform(0.18, 0.32)
            lh = rng.uniform(0.22, 0.38)
            nx, ny = math.cos(theta), math.sin(theta)
            ux, uy = -ny, nx
            v0 = mesh.add_vertex((cx - 0.5 * lw * ux, cy - 0.5 * lw * uy, cz), (nx, ny, 0.0), (0.55, 0.1))
            v1 = mesh.add_vertex((cx + 0.5 * lw * ux, cy + 0.5 * lw * uy, cz), (nx, ny, 0.0), (0.95, 0.1))
            v2 = mesh.add_vertex((cx + 0.5 * lw * ux, cy + 0.5 * lw * uy, cz + lh), (nx, ny, 0.0), (0.95, 0.9))
            v3 = mesh.add_vertex((cx - 0.5 * lw * ux, cy - 0.5 * lw * uy, cz + lh), (nx, ny, 0.0), (0.55, 0.9))
            mesh.add_quad(v0, v1, v2, v3)

        # 4. Flower Blossoms
        for _ in range(35):
            ang = rng.uniform(0, 2 * math.pi)
            dist = spread * rng.uniform(0.5, 1.0)
            fz = H * rng.uniform(0.4, 0.95)
            fx = dist * math.cos(ang)
            fy = dist * math.sin(ang)
            pw = 0.08
            pl = 0.12
            for p in range(4):
                pa = ang + p * math.pi / 2
                dx, dy = math.cos(pa), math.sin(pa)
                v0 = mesh.add_vertex((fx, fy, fz), (0, 0, 1), (0.8, 0.8))
                v1 = mesh.add_vertex((fx + pl * dx - 0.5 * pw * dy, fy + pl * dy + 0.5 * pw * dx, fz + 0.02), (0, 0, 1), (0.95, 0.8))
                v2 = mesh.add_vertex((fx + pl * dx + 0.5 * pw * dy, fy + pl * dy - 0.5 * pw * dx, fz + 0.02), (0, 0, 1), (0.95, 0.95))
                v3 = mesh.add_vertex((fx + 0.5 * pl * dx, fy + 0.5 * pl * dy, fz + 0.04), (0, 0, 1), (0.8, 0.95))
                mesh.add_quad(v0, v1, v2, v3)

        return mesh

    def _build_groundcover(self, species: PlantSpecies, rng: np.random.RandomState) -> MeshGeometry:
        """Category 5: Ferns, Grasses & Groundcover (arching rosette fronds / weeping tussock blades)."""
        mesh = MeshGeometry()
        H = species.dimensions.height_m
        spread = species.dimensions.canopy_spread_m * 0.5

        # 42 arching fronds radiating in Fibonacci spiral
        num_fronds = 42
        for f in range(num_fronds):
            theta = f * 2.39996 + rng.uniform(-0.08, 0.08)
            f_len = spread * rng.uniform(0.75, 1.1)
            num_segs = 10
            r_points = []
            for s in range(num_segs + 1):
                st = s / num_segs
                rx = st * f_len * math.cos(theta)
                ry = st * f_len * math.sin(theta)
                rz = max(0.0, 0.8 * H * st - 0.75 * H * (st**1.8))
                r_points.append((rx, ry, rz))

            # Pinnate leaflets (12 pairs per frond)
            for s in range(1, num_segs):
                px, py, pz = r_points[s]
                st = s / num_segs
                leaf_l = 0.22 * spread * (1.0 - 0.5 * st)
                dx = math.cos(theta + math.pi / 2)
                dy = math.sin(theta + math.pi / 2)
                for side in (-1, 1):
                    lx = px + side * leaf_l * dx
                    ly = py + side * leaf_l * dy
                    lz = pz - 0.05 * leaf_l
                    v0 = mesh.add_vertex((px, py, pz), (0, 0, 1), (0.6, 0.2))
                    v1 = mesh.add_vertex((lx, ly, lz), (0, 0, 1), (0.9, 0.2))
                    v2 = mesh.add_vertex((lx + 0.05 * math.cos(theta), ly + 0.05 * math.sin(theta), lz), (0, 0, 1), (0.9, 0.8))
                    v3 = mesh.add_vertex((px + 0.05 * math.cos(theta), py + 0.05 * math.sin(theta), pz), (0, 0, 1), (0.6, 0.8))
                    mesh.add_quad(v0, v1, v2, v3)

        # Basal rosette cluster
        add_quad_ellipsoid(mesh, (0, 0, 0.08 * H), (0.15 * spread, 0.15 * spread, 0.08 * H), rings=4, sectors=8)

        # Weeping accent blade ribbons (150 blades)
        for _ in range(150):
            ang = rng.uniform(0, 2 * math.pi)
            bl = spread * rng.uniform(0.5, 0.9)
            bx = bl * math.cos(ang)
            by = bl * math.sin(ang)
            bz = rng.uniform(0.02, 0.3 * H)
            v0 = mesh.add_vertex((0, 0, 0.02), (0, 0, 1), (0.6, 0.1))
            v1 = mesh.add_vertex((0.5 * bx, 0.5 * by, 0.5 * H), (0, 0, 1), (0.8, 0.5))
            v2 = mesh.add_vertex((bx, by, bz), (0, 0, 1), (0.9, 0.9))
            v3 = mesh.add_vertex((0.8 * bx, 0.8 * by, bz + 0.05), (0, 0, 1), (0.7, 0.8))
            mesh.add_quad(v0, v1, v2, v3)

        return mesh

    def _build_succulent(self, species: PlantSpecies, rng: np.random.RandomState) -> MeshGeometry:
        """Category 6: Succulents & Cacti (ribbed vertical columns + lateral arms + spine areoles)."""
        mesh = MeshGeometry()
        H = species.dimensions.height_m
        R_base = 0.5 * species.dimensions.trunk_stem_diameter_m

        # 1. Main ribbed vertical column
        c_rings = 32
        c_rad = 32
        num_ribs = 16
        ring_indices: List[List[int]] = []
        for r in range(c_rings):
            t = r / (c_rings - 1)
            z = t * 0.95 * H
            top_factor = math.sin(t * math.pi) if t > 0.85 else 1.0
            cring = []
            for s in range(c_rad):
                ang = 2.0 * math.pi * s / c_rad
                r_ang = R_base * (1.0 + 0.18 * math.cos(num_ribs * ang)) * (0.8 + 0.2 * top_factor)
                px = r_ang * math.cos(ang)
                py = r_ang * math.sin(ang)
                idx = mesh.add_vertex((px, py, z), (math.cos(ang), math.sin(ang), 0.0), (s / c_rad, t * 0.5))
                cring.append(idx)
            ring_indices.append(cring)
            if r > 0:
                for s in range(c_rad):
                    ns = (s + 1) % c_rad
                    mesh.add_quad(ring_indices[r-1][s], ring_indices[r-1][ns], ring_indices[r][ns], ring_indices[r][s])
        add_quad_cap(mesh, ring_indices[0], flip_normal=True)
        add_quad_cap(mesh, ring_indices[-1], flip_normal=False)

        # 2. Upward curved lateral arms (2 arms)
        num_arms = 2
        for a in range(num_arms):
            ang = a * math.pi + rng.uniform(-0.2, 0.2)
            arm_z = H * rng.uniform(0.4, 0.55)
            arm_len = R_base * 2.2
            arm_up = H * 0.35
            a_rings = 16
            a_rad = 16
            a_indices = []
            for ar in range(a_rings):
                at = ar / (a_rings - 1)
                if at < 0.4:
                    frac = at / 0.4
                    ax = (R_base * 0.8 + frac * arm_len) * math.cos(ang)
                    ay = (R_base * 0.8 + frac * arm_len) * math.sin(ang)
                    az = arm_z
                else:
                    frac = (at - 0.4) / 0.6
                    ax = (R_base * 0.8 + arm_len) * math.cos(ang)
                    ay = (R_base * 0.8 + arm_len) * math.sin(ang)
                    az = arm_z + frac * arm_up
                arad = R_base * 0.65
                cring = []
                for asr in range(a_rad):
                    as_ang = 2.0 * math.pi * asr / a_rad
                    as_r = arad * (1.0 + 0.15 * math.cos(8 * as_ang))
                    px = ax + as_r * math.cos(as_ang)
                    py = ay + as_r * math.sin(as_ang)
                    pz = az
                    idx = mesh.add_vertex((px, py, pz), (math.cos(as_ang), math.sin(as_ang), 0.0), (asr / a_rad, at))
                    cring.append(idx)
                a_indices.append(cring)
                if ar > 0:
                    for asr in range(a_rad):
                        nasr = (asr + 1) % a_rad
                        mesh.add_quad(a_indices[ar-1][asr], a_indices[ar-1][nasr], a_indices[ar][nasr], a_indices[ar][asr])
            add_quad_cap(mesh, a_indices[-1], flip_normal=False)

        # 3. Spine Areoles (450 clusters)
        for sp in range(450):
            rib = sp % num_ribs
            ang = 2.0 * math.pi * rib / num_ribs
            z_frac = (sp // num_ribs) / (450 // num_ribs + 1)
            sz = 0.05 * H + z_frac * 0.85 * H
            sr = R_base * (1.0 + 0.18)
            sx = sr * math.cos(ang)
            sy = sr * math.sin(ang)
            sl = 0.08
            v0 = mesh.add_vertex((sx, sy, sz), (math.cos(ang), math.sin(ang), 0.0), (0.7, 0.7))
            v1 = mesh.add_vertex((sx + sl * math.cos(ang), sy + sl * math.sin(ang), sz + 0.02), (math.cos(ang), math.sin(ang), 0.0), (0.7, 0.9))
            v2 = mesh.add_vertex((sx + sl * math.cos(ang), sy + sl * math.sin(ang), sz - 0.02), (math.cos(ang), math.sin(ang), 0.0), (0.9, 0.9))
            v3 = mesh.add_vertex((sx, sy, sz - 0.01), (math.cos(ang), math.sin(ang), 0.0), (0.9, 0.7))
            mesh.add_quad(v0, v1, v2, v3)

        return mesh

    def _build_vine(self, species: PlantSpecies, rng: np.random.RandomState) -> MeshGeometry:
        """Category 7: Climbing Vines & Epiphytes (intertwined helical stems + cascading leaf plates)."""
        mesh = MeshGeometry()
        H = species.dimensions.height_m
        spread = species.dimensions.canopy_spread_m * 0.5
        stem_r = 0.02

        # 1. 3 intertwined helical stems
        num_helices = 3
        h_rings = 36
        h_rad = 8
        helix_r = spread * 0.4
        for h in range(num_helices):
            phase = h * 2.0 * math.pi / num_helices
            r_indices = []
            for r in range(h_rings):
                t = r / (h_rings - 1)
                z = t * 0.95 * H
                theta = 4.0 * math.pi * t + phase
                hx = helix_r * (1.0 - 0.2 * t) * math.cos(theta)
                hy = helix_r * (1.0 - 0.2 * t) * math.sin(theta)
                cring = []
                for s in range(h_rad):
                    sa = 2.0 * math.pi * s / h_rad
                    px = hx + stem_r * math.cos(sa)
                    py = hy + stem_r * math.sin(sa)
                    idx = mesh.add_vertex((px, py, z), (math.cos(sa), math.sin(sa), 0.0), (s / h_rad, t))
                    cring.append(idx)
                r_indices.append(cring)
                if r > 0:
                    for s in range(h_rad):
                        ns = (s + 1) % h_rad
                        mesh.add_quad(r_indices[r-1][s], r_indices[r-1][ns], r_indices[r][ns], r_indices[r][s])

        # 2. Cascading Leaf Planes (800 cards)
        for _ in range(800):
            t = rng.uniform(0.05, 0.95)
            h = rng.randint(0, num_helices)
            phase = h * 2.0 * math.pi / num_helices
            theta = 4.0 * math.pi * t + phase + rng.uniform(-0.4, 0.4)
            dist = helix_r * (1.0 - 0.2 * t) + rng.uniform(-0.1, 0.2) * spread
            cz = t * 0.95 * H + rng.uniform(-0.1, 0.1)
            cx = dist * math.cos(theta)
            cy = dist * math.sin(theta)
            lw = rng.uniform(0.12, 0.24)
            lh = rng.uniform(0.15, 0.28)
            nx, ny = math.cos(theta), math.sin(theta)
            ux, uy = -ny, nx
            v0 = mesh.add_vertex((cx - 0.5 * lw * ux, cy - 0.5 * lw * uy, cz), (nx, ny, 0.0), (0.55, 0.1))
            v1 = mesh.add_vertex((cx + 0.5 * lw * ux, cy + 0.5 * lw * uy, cz), (nx, ny, 0.0), (0.95, 0.1))
            v2 = mesh.add_vertex((cx + 0.5 * lw * ux, cy + 0.5 * lw * uy, cz + lh), (nx, ny, 0.0), (0.95, 0.9))
            v3 = mesh.add_vertex((cx - 0.5 * lw * ux, cy - 0.5 * lw * uy, cz + lh), (nx, ny, 0.0), (0.55, 0.9))
            mesh.add_quad(v0, v1, v2, v3)

        return mesh

    def _enforce_mesh_invariants(self, mesh: MeshGeometry, target_height: float) -> MeshGeometry:
        """Enforces ground root pivot Z_min = 0.0 and base contact centering at origin (0, 0)."""
        if not mesh.vertices:
            return mesh

        # 1. Ground contact alignment (lowest vertex at z = 0.0)
        z_min = min(v[2] for v in mesh.vertices)
        mesh.vertices = [(v[0], v[1], v[2] - z_min) for v in mesh.vertices]

        # 2. Base contact centering (bottom 5% height centered at x=0, y=0)
        current_h = max(v[2] for v in mesh.vertices)
        if current_h > 1e-4:
            base_verts = [v for v in mesh.vertices if v[2] <= 0.05 * current_h]
            if base_verts:
                cx = sum(v[0] for v in base_verts) / len(base_verts)
                cy = sum(v[1] for v in base_verts) / len(base_verts)
                mesh.vertices = [(v[0] - cx, v[1] - cy, v[2]) for v in mesh.vertices]

        # 3. Analytical re-check to guarantee exact Z_min = 0.0
        z_min2 = min(v[2] for v in mesh.vertices)
        if abs(z_min2) > 1e-7:
            mesh.vertices = [(v[0], v[1], v[2] - z_min2) for v in mesh.vertices]

        return mesh

    def _generate_pbr_textures(
        self,
        species: PlantSpecies,
        rng: np.random.RandomState,
        resolution: int = 512,
    ) -> Dict[str, Image.Image]:
        """Synthesizes authentic 4-channel PBR textures (Albedo, Normal, Roughness, Metallic)."""
        W = H = resolution
        y_coords, x_coords = np.mgrid[0:H, 0:W].astype(np.float32)
        u = x_coords / float(W)
        v = y_coords / float(H)
        is_bark = u < 0.5
        cat = species.short_category

        # 1. BaseColor / Albedo
        albedo = np.zeros((H, W, 3), dtype=np.float32)
        if "birch" in species.species_id:
            bark_rgb = np.array([210.0, 205.0, 195.0], dtype=np.float32)
        elif cat in ("succulents", "succulents_cacti"):
            bark_rgb = np.array([55.0, 95.0, 45.0], dtype=np.float32)
        else:
            bark_rgb = np.array([72.0, 52.0, 36.0], dtype=np.float32)

        if cat in ("conifers", "conifers_evergreens"):
            foliage_rgb = np.array([25.0, 65.0, 25.0], dtype=np.float32)
        elif cat in ("tropical", "tropical_foliage_palms"):
            foliage_rgb = np.array([22.0, 85.0, 35.0], dtype=np.float32)
        elif cat in ("succulents", "succulents_cacti"):
            foliage_rgb = np.array([75.0, 120.0, 95.0], dtype=np.float32)
        else:
            foliage_rgb = np.array([55.0, 115.0, 40.0], dtype=np.float32)

        albedo[is_bark] = bark_rgb
        albedo[~is_bark] = foliage_rgb

        # Micro-fissures and organic texture noise
        noise_bark = 12.0 * np.sin(x_coords * (2.0 * np.pi / 24.0)) + 6.0 * np.cos(y_coords * (2.0 * np.pi / 64.0))
        noise_foliage = 10.0 * np.sin(x_coords * (2.0 * np.pi / 16.0)) + 10.0 * np.cos(y_coords * (2.0 * np.pi / 16.0))

        albedo[is_bark, 0] += noise_bark[is_bark]
        albedo[is_bark, 1] += noise_bark[is_bark] * 0.7
        albedo[is_bark, 2] += noise_bark[is_bark] * 0.5

        albedo[~is_bark, 0] += noise_foliage[~is_bark] * 0.5
        albedo[~is_bark, 1] += noise_foliage[~is_bark]
        albedo[~is_bark, 2] += noise_foliage[~is_bark] * 0.4

        # Floral accent in foliage quadrant if shrub/rose/flowering
        if cat in ("shrubs", "flowering_shrubs_ornamentals") or "rose" in species.species_id or "azalea" in species.species_id:
            is_flower = (u >= 0.75) & (v >= 0.75)
            albedo[is_flower] = [185.0, 35.0, 55.0]

        albedo = np.clip(albedo, 0.0, 255.0).astype(np.uint8)
        albedo_img = Image.fromarray(albedo, mode="RGB")

        # 2. Normal Map (tangent-space OpenGL: +X right, +Y up, +Z outward dominant)
        nx = np.zeros((H, W), dtype=np.float32)
        ny = np.zeros((H, W), dtype=np.float32)
        nx[is_bark] = 0.20 * np.sin(x_coords[is_bark] * (2.0 * np.pi / 28.0))
        ny[is_bark] = 0.08 * np.cos(y_coords[is_bark] * (2.0 * np.pi / 56.0))
        nx[~is_bark] = 0.15 * np.sin(x_coords[~is_bark] * (2.0 * np.pi / 18.0))
        ny[~is_bark] = 0.15 * np.cos(y_coords[~is_bark] * (2.0 * np.pi / 18.0))

        nz = np.sqrt(np.clip(1.0 - (nx**2 + ny**2), 0.01, 1.0))
        normal_arr = np.clip((np.dstack([nx, ny, nz]) + 1.0) * 127.5, 0, 255).astype(np.uint8)
        normal_img = Image.fromarray(normal_arr, mode="RGB")

        # 3. Roughness Map (matte bark, semi-gloss foliage)
        rough_arr = np.where(is_bark, 0.82, 0.48)
        rough_noise = 0.04 * np.sin(x_coords * (2.0 * np.pi / 32.0))
        rough_arr = np.clip((rough_arr + rough_noise) * 255.0, 0, 255).astype(np.uint8)
        roughness_img = Image.fromarray(rough_arr, mode="L")

        # 4. Metallic Map (strictly dielectric non-metal foliage tissue <= 0.05)
        metallic_arr = np.zeros((H, W), dtype=np.uint8)
        metallic_img = Image.fromarray(metallic_arr, mode="L")

        return {
            "albedo": albedo_img,
            "normal": normal_img,
            "roughness": roughness_img,
            "metallic": metallic_img,
        }


# ==============================================================================
# MASTER GENERATION ENTRY POINT
# ==============================================================================

def generate_plant(
    species: Union[PlantSpecies, str],
    mode: Literal["auto", "meshy", "procedural"] = "auto",
    output_dir: Optional[Union[str, Path]] = None,
    seed: Optional[Union[int, str]] = None,
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
        raise ValueError(f"Invalid generation mode: '{mode}'")

    # 1. Resolve species input
    if isinstance(species, str):
        cat = get_catalog()
        species_obj = cat[species]
    elif isinstance(species, PlantSpecies):
        species_obj = species
    else:
        raise TypeError(f"Expected PlantSpecies or str, got {type(species).__name__}")

    out_path = Path(output_dir) if output_dir is not None else Path("./output") / species_obj.short_category / species_obj.species_id

    # 2. Mode: Explicit Procedural
    if mode == "procedural":
        proc_gen = ProceduralBotanicalGenerator(seed=seed)
        return proc_gen.generate(species_obj, output_dir=out_path, seed=seed)

    # 3. Initialize Meshy engine
    meshy_gen = MeshyGenerator(config=generator_config)

    # 4. Mode: Explicit Meshy
    if mode == "meshy":
        api_key = meshy_gen.resolve_api_key()
        if not api_key:
            raise RuntimeError("MESHY_API_KEY API key environment variable is not set")
        if not force_regenerate and not meshy_gen.config.force_regenerate and meshy_gen.config.use_cache:
            cached_asset = meshy_gen.check_cache(species_obj, target_dir=out_path, expected_source="meshy")
            if cached_asset is not None:
                return cached_asset
        return meshy_gen.generate(species_obj, output_dir=out_path, force_regenerate=force_regenerate)

    # 5. Mode: Auto (Meshy with graceful Procedural Fallback)
    if not force_regenerate and not meshy_gen.config.force_regenerate and meshy_gen.config.use_cache:
        cached_asset = meshy_gen.check_cache(species_obj, target_dir=out_path)
        if cached_asset is not None:
            return cached_asset

    api_key = meshy_gen.resolve_api_key()
    if not api_key:
        logger.info("No MESHY_API_KEY found. Falling back to ProceduralBotanicalGenerator.")
        proc_gen = ProceduralBotanicalGenerator(seed=seed)
        return proc_gen.generate(species_obj, output_dir=out_path, seed=seed)

    try:
        return meshy_gen.generate(species_obj, output_dir=out_path, force_regenerate=force_regenerate)
    except Exception as e:
        logger.warning("Meshy generation failed (%s). Gracefully falling back to ProceduralBotanicalGenerator.", e)
        proc_gen = ProceduralBotanicalGenerator(seed=seed)
        return proc_gen.generate(species_obj, output_dir=out_path, seed=seed)


__all__ = [
    "RawAsset",
    "MeshyGenerator",
    "MeshyGeneratorConfig",
    "ProceduralBotanicalGenerator",
    "ProceduralGeneratorConfig",
    "generate_plant",
]
