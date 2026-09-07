"""
MorphoMesh: Google Gemini & Imagen 3 Image Connector.

Integrates Google Gemini / Imagen 3 foundation models for:
  1. 2D Anatomical Concept Art Generation (clean foreground silhouette & alpha extraction).
  2. Character Turnaround Model Sheets (synchronized front, side, and back orthographic views).
  3. PBR Texture Reference Synthesis (Albedo, Normal, Roughness, and Metallic maps).

Supports execution via:
  - Official `google-genai` SDK (when installed and API key provided)
  - Direct Google AI HTTP REST API (Imagen 3 predict endpoint)
  - Zero-VRAM deterministic offline procedural fallback (when API key is absent or network fails)
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pydantic import BaseModel, ConfigDict, Field, field_validator

from morphomesh.connectors.base import (
    BaseConnector,
    CircuitBreakerState,
    DependencyCheckResult,
    HealthCheckResult,
    PBRTextureMaps,
)
from morphomesh.models import (
    ERR_BACKEND_UNAVAILABLE,
    ERR_IMAGE_NOT_FOUND,
    ERR_INFERENCE_FAILED,
    ERR_INVALID_ARGUMENT,
    GenerateConceptInput,
    GenerateConceptOutput,
    MorphoMeshException,
)

logger = logging.getLogger(__name__)

# Optional google-genai SDK import
try:
    from google import genai
    from google.genai import types as genai_types
    _HAS_GOOGLE_GENAI = True
except ImportError:
    _HAS_GOOGLE_GENAI = False
    genai = None  # type: ignore
    genai_types = None  # type: ignore


# ==============================================================================
# PYDANTIC V2 DATA SCHEMAS
# ==============================================================================

class GeminiImageConfig(BaseModel):
    """Configuration for Google Gemini and Imagen 3 connector."""
    model_config = ConfigDict(extra="ignore")

    api_key: Optional[str] = None
    model_name: str = "imagen-3.0-generate-002"
    mode: Literal["auto", "sdk", "rest", "mock"] = "auto"
    endpoint_url: str = "https://generativelanguage.googleapis.com/v1beta"
    timeout_seconds: float = Field(default=60.0, ge=5.0, le=300.0)
    aspect_ratio: str = "1:1"
    person_generation: str = "ALLOW_ADULT"
    safety_filter_level: str = "block_medium_and_above"
    number_of_images: int = 1
    fallback_to_mock: bool = True


class GeminiImageInput(BaseModel):
    """Workload request parameters for Gemini / Imagen 3 generation."""
    model_config = ConfigDict(extra="ignore")

    prompt: str = Field(..., min_length=1, max_length=4000, description="Creature concept description or texture specification")
    negative_prompt: str = Field(default="", max_length=2000, description="Negative prompt constraints")
    task_type: Literal["concept", "turnaround", "texture"] = Field(
        default="concept",
        description="Task: 'concept' (2D creature), 'turnaround' (3-angle model sheet), 'texture' (PBR maps)"
    )
    view_mode: str = Field(default="front", description="Perspective: front, side, turnaround_sheet, etc.")
    creature_type: str = Field(default="custom", description="Creature anatomical archetype")
    pose: str = Field(default="standing_neutral", description="Rest pose specification")
    style: str = Field(default="realistic", description="Visual aesthetic rendering style")
    background: str = Field(default="white_neutral", description="Background color guidance")
    width: int = Field(default=1024, ge=256, le=4096, description="Output image width")
    height: int = Field(default=1024, ge=256, le=4096, description="Output image height")
    aspect_ratio: str = Field(default="1:1", description="Aspect ratio ('1:1', '3:4', '4:3', '16:9', '9:16')")
    seed: int = Field(default=-1, description="Deterministic seed (-1 for randomized)")
    output_format: str = Field(default="png", description="File format on disk")
    output_dir: Optional[str] = Field(default=None, description="Custom output directory")
    extract_alpha: bool = Field(default=True, description="Extract clean RGBA mask with isolated background")
    texture_type: Optional[str] = Field(default=None, description="Texture map type when task_type='texture'")

    @field_validator("prompt")
    @classmethod
    def validate_prompt_not_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Prompt must not be empty or whitespace only.")
        return s

    @field_validator("aspect_ratio")
    @classmethod
    def normalize_aspect_ratio(cls, v: Optional[str]) -> str:
        if not v:
            return "1:1"
        v_str = str(v).strip().lower()
        mapping = {
            "1:1": "1:1", "square": "1:1",
            "16:9": "16:9", "landscape": "16:9", "wide": "16:9",
            "9:16": "9:16", "portrait": "9:16",
            "4:3": "4:3",
            "3:4": "3:4",
        }
        return mapping.get(v_str, "1:1")


class GeminiImageOutput(BaseModel):
    """Result payload from Gemini / Imagen 3 image generation."""
    model_config = ConfigDict(extra="ignore")

    asset_id: str = Field(..., description="Unique generation UUID")
    image_path: str = Field(..., description="Primary generated image path on disk")
    rgba_image_path: Optional[str] = Field(default=None, description="Alpha-isolated RGBA image path")
    task_type: str = Field(default="concept")
    prompt_enhanced: str = Field(default="", description="Augmented prompt with anatomical and model-sheet priors")
    width: int = 1024
    height: int = 1024
    views: Dict[str, str] = Field(default_factory=dict, description="Segmented view paths for turnaround sheets (front, side, back)")
    pbr_textures: Optional[PBRTextureMaps] = Field(default=None, description="PBR texture suite when task_type='texture'")
    backend_used: str = Field(default="gemini")
    execution_mode: str = Field(default="mock", description="Effective mode: 'sdk', 'rest', or 'mock'")
    duration_seconds: float = Field(default=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# GEMINI IMAGE CONNECTOR IMPLEMENTATION
# ==============================================================================

class GeminiImageConnector(BaseConnector):
    """
    Google Gemini and Imagen 3 foundation connector for MorphoMesh.

    Provides high-fidelity 2D concept generation, multi-angle character turnaround
    model sheets, and decoupled PBR texture maps with automatic graceful fallback
    to zero-VRAM offline procedural synthesis.
    """

    connector_id: str = "gemini_image"
    display_name: str = "Google Gemini & Imagen 3 Image Connector"
    version: str = "3.0.0"
    stage: int = 1
    description: str = (
        "Google Gemini & Imagen 3 connector for 2D concept art, multi-view "
        "character turnaround model sheets, and PBR texture map synthesis"
    )

    def __init__(
        self,
        config: Optional[Union[GeminiImageConfig, Dict[str, Any]]] = None,
        circuit_breaker: Optional[Any] = None,
    ) -> None:
        if isinstance(config, GeminiImageConfig):
            self.gemini_config = config
            cfg_dict = config.model_dump()
        elif isinstance(config, dict):
            self.gemini_config = GeminiImageConfig(**config)
            cfg_dict = config
        else:
            self.gemini_config = GeminiImageConfig()
            cfg_dict = self.gemini_config.model_dump()

        super().__init__(config=cfg_dict, circuit_breaker=circuit_breaker)
        self._sdk_client: Any = None
        self.register_fallback(self._execute_mock_fallback)

    def _resolve_api_key(self) -> Optional[str]:
        """Look up active API key from config or environment variables."""
        raw = (
            self.gemini_config.api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if raw and str(raw).strip():
            return str(raw).strip()
        return None

    def initialize(self) -> bool:
        """Initialize connector credentials and warm client handles."""
        api_key = self._resolve_api_key()
        if api_key and _HAS_GOOGLE_GENAI and self.gemini_config.mode in ("auto", "sdk"):
            try:
                self._sdk_client = genai.Client(api_key=api_key)
                logger.info("Initialized Google GenAI SDK client for GeminiImageConnector.")
            except Exception as e:
                logger.debug("Failed initializing GenAI SDK client (%s). Will use REST or mock fallback.", e)
                self._sdk_client = None
        elif not api_key:
            logger.info("No GEMINI_API_KEY or GOOGLE_API_KEY found. Operating in offline mock mode.")

        self.is_initialized = True
        return True

    def health_check(self) -> HealthCheckResult:
        """Evaluate operational readiness and endpoint latency."""
        start_time = time.time()
        api_key = self._resolve_api_key()
        circuit_state = getattr(self.circuit_breaker, "state", "CLOSED")
        if hasattr(circuit_state, "value"):
            circuit_state = circuit_state.value

        if self.gemini_config.mode == "mock" or not api_key:
            latency = (time.time() - start_time) * 1000.0
            return HealthCheckResult(
                status="degraded" if not api_key else "healthy",
                latency_ms=round(latency, 2),
                message=(
                    "Operating in zero-VRAM procedural mock mode (API key absent or mock configured)"
                    if not api_key
                    else "Gemini mock mode active"
                ),
                details={
                    "mode": "mock",
                    "api_key_configured": bool(api_key),
                    "model_name": self.gemini_config.model_name,
                },
                circuit_state=str(circuit_state),
                dependencies_met=True,
            )

        # In live mode with API key
        latency = (time.time() - start_time) * 1000.0
        return HealthCheckResult(
            status="healthy",
            latency_ms=round(latency, 2),
            message="Google Gemini image generator ready",
            details={
                "mode": self.gemini_config.mode,
                "api_key_configured": True,
                "sdk_installed": _HAS_GOOGLE_GENAI,
                "model_name": self.gemini_config.model_name,
            },
            circuit_state=str(circuit_state),
            dependencies_met=True,
        )

    def check_dependencies(self) -> DependencyCheckResult:
        """Audit Python SDK availability and system dependencies."""
        missing = []
        if not _HAS_GOOGLE_GENAI:
            missing.append("google-genai")

        return DependencyCheckResult(
            satisfied=True,  # Fully satisfied because REST & mock procedural fallbacks are built-in
            missing_packages=missing,
            hardware_supported=True,
            details={
                "has_google_genai_sdk": _HAS_GOOGLE_GENAI,
                "has_pillow": True,
                "has_numpy": True,
                "rest_supported": True,
                "mock_supported": True,
            },
        )

    def close(self) -> None:
        """Release allocated resources and SDK client handles."""
        self._sdk_client = None
        self.is_initialized = False

    # ==========================================================================
    # WORKLOAD EXECUTION & DISPATCH
    # ==========================================================================

    def _execute_mock_fallback(self, request: Any, **kwargs: Any) -> GeminiImageOutput:
        """Deterministic zero-VRAM procedural mock fallback handler."""
        start_time = time.time()
        inp = self._normalize_request(request, **kwargs)
        out_dir = inp.output_dir or os.path.expanduser("~/.morphomesh/cache/concepts")
        os.makedirs(out_dir, exist_ok=True)
        asset_id = f"gemini-{uuid.uuid4().hex[:8]}"
        enhanced_prompt = self._build_enhanced_prompt(inp)
        base_img = self._generate_mock_image(inp, enhanced_prompt)
        return self._process_and_save_workload(
            inp=inp,
            base_img=base_img,
            asset_id=asset_id,
            out_dir=out_dir,
            enhanced_prompt=enhanced_prompt,
            effective_mode="mock",
            duration=round(time.time() - start_time, 4),
        )

    def _execute_live(self, request: Any, **kwargs: Any) -> GeminiImageOutput:
        """
        Attempt live network generation (SDK or REST).
        Raises MorphoMeshException on live failure so CircuitBreaker records failure and routes to fallback.
        """
        start_time = time.time()
        inp = self._normalize_request(request, **kwargs)
        out_dir = inp.output_dir or os.path.expanduser("~/.morphomesh/cache/concepts")
        os.makedirs(out_dir, exist_ok=True)
        asset_id = f"gemini-{uuid.uuid4().hex[:8]}"

        api_key = self._resolve_api_key()
        enhanced_prompt = self._build_enhanced_prompt(inp)

        if self.gemini_config.mode == "mock" or not api_key:
            base_img = self._generate_mock_image(inp, enhanced_prompt)
            return self._process_and_save_workload(
                inp=inp,
                base_img=base_img,
                asset_id=asset_id,
                out_dir=out_dir,
                enhanced_prompt=enhanced_prompt,
                effective_mode="mock",
                duration=round(time.time() - start_time, 4),
            )

        base_img: Optional[Image.Image] = None
        effective_mode = "mock"
        last_err: Optional[Exception] = None

        if _HAS_GOOGLE_GENAI and self.gemini_config.mode in ("auto", "sdk"):
            try:
                base_img = self._generate_via_sdk(inp, enhanced_prompt, api_key)
                effective_mode = "sdk"
            except Exception as e:
                logger.warning("Google GenAI SDK call failed (%s). Attempting REST fallback.", e)
                last_err = e

        if base_img is None and self.gemini_config.mode in ("auto", "rest"):
            try:
                base_img = self._generate_via_rest(inp, enhanced_prompt, api_key)
                effective_mode = "rest"
            except Exception as e:
                logger.warning("Google AI REST API call failed (%s).", e)
                last_err = e

        if base_img is None:
            raise MorphoMeshException(
                code=ERR_BACKEND_UNAVAILABLE,
                message=f"Google Gemini image generation failed: {last_err}",
                details={"error": str(last_err), "model": self.gemini_config.model_name},
            )

        return self._process_and_save_workload(
            inp=inp,
            base_img=base_img,
            asset_id=asset_id,
            out_dir=out_dir,
            enhanced_prompt=enhanced_prompt,
            effective_mode=effective_mode,
            duration=round(time.time() - start_time, 4),
        )

    def execute_with_resilience(self, request: Any, **kwargs: Any) -> GeminiImageOutput:
        """
        Execute workload with circuit-breaker protection and automatic fallback to procedural mock.
        """
        fallback_fn = self._fallback_handler or self._execute_mock_fallback
        if self.circuit_breaker is not None and hasattr(self.circuit_breaker, "call"):
            return self.circuit_breaker.call(
                self._execute_live,
                request,
                fallback=fallback_fn,
                **kwargs,
            )
        try:
            return self._execute_live(request, **kwargs)
        except Exception as e:
            if fallback_fn is not None:
                logger.warning("Gemini execution failed (%s). Routing to resilient fallback.", e)
                return fallback_fn(request, **kwargs)
            raise

    def execute(
        self,
        request: Union[GeminiImageInput, GenerateConceptInput, Dict[str, Any], str],
        **kwargs: Any,
    ) -> GeminiImageOutput:
        """
        Execute image generation across Concept Art, Turnaround Sheets, or Textures.

        Args:
            request: Typed request model, GenerateConceptInput, dict, or prompt string.
            **kwargs: Overrides or supplemental arguments.

        Returns:
            GeminiImageOutput: Generated image path, alpha mask, and view crops.
        """
        raise_on_failure = kwargs.pop("raise_on_failure", not self.gemini_config.fallback_to_mock)
        try:
            if (
                self.circuit_breaker is not None
                and not self.circuit_breaker.can_attempt()
                and self._resolve_api_key()
                and self.gemini_config.mode != "mock"
            ):
                if raise_on_failure:
                    raise MorphoMeshException(
                        code=ERR_BACKEND_UNAVAILABLE,
                        message="Circuit breaker is OPEN. Target Gemini connector backend unavailable.",
                    )
                return self._execute_mock_fallback(request, **kwargs)

            out = self._execute_live(request, **kwargs)
            if self.circuit_breaker and out.execution_mode in ("sdk", "rest"):
                self.circuit_breaker.record_success()
            return out
        except Exception as e:
            if self.circuit_breaker and self._resolve_api_key() and self.gemini_config.mode != "mock":
                self.circuit_breaker.record_failure(e)

            if raise_on_failure:
                if isinstance(e, MorphoMeshException):
                    raise
                raise MorphoMeshException(
                    code=ERR_BACKEND_UNAVAILABLE,
                    message=f"Gemini execution failed: {e}",
                    details={"error": str(e)},
                ) from e

            logger.warning("Gemini live execution failed (%s). Falling back to procedural mock.", e)
            return self._execute_mock_fallback(request, **kwargs)

    # ==========================================================================
    # REQUEST NORMALIZATION & PROMPT EXPANSION
    # ==========================================================================

    def _normalize_request(
        self,
        request: Union[GeminiImageInput, GenerateConceptInput, Dict[str, Any], str],
        **kwargs: Any,
    ) -> GeminiImageInput:
        """Convert heterogeneous request types into a uniform GeminiImageInput."""
        if isinstance(request, GeminiImageInput):
            if kwargs:
                filtered_kw = {k: v for k, v in kwargs.items() if hasattr(request, k) and v is not None}
                if filtered_kw:
                    return request.model_copy(update=filtered_kw)
            return request

        if isinstance(request, GenerateConceptInput):
            task_type = "concept"
            view_mode_str = str(request.view_mode).lower()
            if any(vm in view_mode_str for vm in ("turnaround", "orthographic", "turntable")):
                task_type = "turnaround"

            aspect_ratio = "1:1"
            if task_type == "turnaround":
                aspect_ratio = "16:9"

            return GeminiImageInput(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                task_type=kwargs.get("task_type", task_type),
                view_mode=str(request.view_mode),
                creature_type=str(request.creature_type),
                pose=str(request.pose),
                style=str(request.style),
                background=request.background,
                width=request.width,
                height=request.height,
                aspect_ratio=kwargs.get("aspect_ratio", aspect_ratio),
                seed=request.seed,
                output_format=request.output_format,
                output_dir=kwargs.get("output_dir"),
                extract_alpha=True,
            )

        if isinstance(request, dict):
            combined = dict(request)
            combined.update(kwargs)
            return GeminiImageInput(**combined)

        if isinstance(request, str):
            clean_kwargs = dict(kwargs)
            task_type = clean_kwargs.pop("task_type", "concept")
            return GeminiImageInput(prompt=request, task_type=task_type, **clean_kwargs)

        raise MorphoMeshException(
            code=ERR_INVALID_ARGUMENT,
            message=f"Unsupported request type for GeminiImageConnector: {type(request)}",
        )

    def _build_enhanced_prompt(self, inp: GeminiImageInput) -> str:
        """Expand prompt with specialized anatomical conditioning and model priors."""
        if inp.task_type == "turnaround" or any(
            vm in inp.view_mode.lower() for vm in ("turnaround", "orthographic", "turntable")
        ):
            return (
                f"Professional character turnaround model sheet of {inp.prompt}, "
                f"{inp.creature_type} anatomical archetype, showing three synchronized "
                f"orthographic views side-by-side: orthographic front view, orthographic side profile view, "
                f"and orthographic back view. Perfectly aligned at matching height and scale, "
                f"symmetrical {inp.pose} rest pose, clean solid neutral {inp.background} background, "
                f"flat studio lighting, {inp.style} production model sheet for 3D digital sculptors, "
                f"orthographic projection, no perspective distortion, zero ground clutter, sharp 8k clarity."
            )

        if inp.task_type == "texture":
            tex_kind = inp.texture_type or "albedo"
            return (
                f"High-resolution seamless flat PBR {tex_kind} texture map of {inp.prompt}, "
                f"surface material detail, diffuse base color without baked directional shadows or specular highlights, "
                f"uniform illumination, tileable texture pattern, photorealistic creature skin/scales/fur, 8k resolution."
            )

        # Standard 2D Concept Art
        return (
            f"Masterpiece full-body anatomical concept art of {inp.prompt}, "
            f"{inp.creature_type} creature archetype, {inp.pose} anatomical rest pose, "
            f"{inp.style} style, clean isolated solid {inp.background} background with high contrast silhouette, "
            f"even three-point neutral studio lighting, centered composition, entire creature in frame with zero cropping, "
            f"production concept art for 3D reconstruction, 8k resolution."
        )

    # ==========================================================================
    # SDK & REST GENERATION ENGINES
    # ==========================================================================

    def _generate_via_sdk(
        self,
        inp: GeminiImageInput,
        enhanced_prompt: str,
        api_key: str,
    ) -> Image.Image:
        """Generate image using the official Google GenAI SDK."""
        if not _HAS_GOOGLE_GENAI:
            raise RuntimeError("google-genai SDK is not installed")

        client = self._sdk_client or genai.Client(api_key=api_key)
        aspect = inp.aspect_ratio or self.gemini_config.aspect_ratio or "1:1"

        config_args: Dict[str, Any] = {
            "number_of_images": 1,
            "output_mime_type": "image/png",
            "aspect_ratio": aspect,
        }
        if self.gemini_config.person_generation:
            config_args["person_generation"] = self.gemini_config.person_generation
        if inp.negative_prompt:
            config_args["negative_prompt"] = inp.negative_prompt

        types_mod = getattr(genai, "types", genai_types)
        if types_mod is not None and hasattr(types_mod, "GenerateImagesConfig"):
            config = types_mod.GenerateImagesConfig(**config_args)
        else:
            config = config_args

        response = client.models.generate_images(
            model=self.gemini_config.model_name,
            prompt=enhanced_prompt,
            config=config,
        )

        if not response or not getattr(response, "generated_images", None):
            raise RuntimeError("Google GenAI returned zero generated images.")

        first_img = response.generated_images[0]
        image_bytes: Any = None
        if hasattr(first_img, "image"):
            img_obj = first_img.image
            if hasattr(img_obj, "image_bytes"):
                image_bytes = img_obj.image_bytes
            elif hasattr(img_obj, "bytes"):
                image_bytes = img_obj.bytes
            elif isinstance(img_obj, (bytes, bytearray)):
                image_bytes = img_obj
        elif hasattr(first_img, "image_bytes"):
            image_bytes = first_img.image_bytes
        elif isinstance(first_img, (bytes, bytearray)):
            image_bytes = first_img

        if image_bytes is None:
            raise RuntimeError("Could not extract image bytes from Google GenAI response.")

        if isinstance(image_bytes, str):
            image_bytes = base64.b64decode(image_bytes)

        return Image.open(io.BytesIO(image_bytes))

    def _generate_via_rest(
        self,
        inp: GeminiImageInput,
        enhanced_prompt: str,
        api_key: str,
    ) -> Image.Image:
        """Generate image using direct Google AI HTTP REST API."""
        url = f"{self.gemini_config.endpoint_url.rstrip('/')}/models/{self.gemini_config.model_name}:predict?key={api_key}"
        aspect = inp.aspect_ratio or self.gemini_config.aspect_ratio or "1:1"

        parameters: Dict[str, Any] = {
            "sampleCount": 1,
            "aspectRatio": aspect,
            "outputOptions": {
                "mimeType": "image/png"
            }
        }
        if inp.negative_prompt:
            parameters["negativePrompt"] = inp.negative_prompt
        if self.gemini_config.person_generation:
            parameters["personGeneration"] = self.gemini_config.person_generation

        payload = {
            "instances": [
                {"prompt": enhanced_prompt}
            ],
            "parameters": parameters,
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
            "User-Agent": "MorphoMesh-GeminiImageConnector/3.0",
        }

        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.gemini_config.timeout_seconds) as resp:
                body = resp.read().decode("utf-8")
                result = json.loads(body)
        except urllib.error.HTTPError as http_err:
            err_body = ""
            try:
                err_body = http_err.read().decode("utf-8")
            except Exception:
                pass
            logger.error("Google AI REST HTTP %d error: %s. Response body: %s", http_err.code, http_err.reason, err_body)
            raise RuntimeError(f"Google AI REST HTTP {http_err.code} ({http_err.reason}): {err_body}") from http_err

        b64_str: Optional[str] = None
        if "predictions" in result and len(result["predictions"]) > 0:
            pred = result["predictions"][0]
            b64_str = pred.get("bytesBase64Encoded") or pred.get("image", {}).get("imageBytes")
        elif "candidates" in result and len(result["candidates"]) > 0:
            parts = result["candidates"][0].get("content", {}).get("parts", [])
            for p in parts:
                if "inlineData" in p:
                    b64_str = p["inlineData"].get("data")
                    break

        if not b64_str:
            raise RuntimeError(f"Unexpected Google AI REST response structure: {list(result.keys())}")

        img_bytes = base64.b64decode(b64_str)
        return Image.open(io.BytesIO(img_bytes))

    # ==========================================================================
    # DETERMINISTIC OFFLINE MOCK GENERATOR
    # ==========================================================================

    def _generate_mock_image(self, inp: GeminiImageInput, enhanced_prompt: str) -> Image.Image:
        """Synthesize visually sound procedural artwork using PIL & numpy."""
        if inp.seed >= 0:
            np.random.seed(inp.seed)

        w, h = inp.width, inp.height
        is_light_bg = "white" in inp.background.lower() or "light" in inp.background.lower()
        bg_rgb = (255, 255, 255) if is_light_bg else (24, 24, 28)
        body_rgb = (48, 54, 68) if is_light_bg else (215, 222, 235)
        accent_rgb = (95, 120, 160) if is_light_bg else (160, 190, 230)

        # 1. Turnaround Sheet Mock
        if inp.task_type == "turnaround" or any(
            vm in inp.view_mode.lower() for vm in ("turnaround", "orthographic", "turntable")
        ):
            # Render wide canvas for 3-view sheet (e.g. 1536x512)
            sheet_w = max(w, int(h * 2.5))
            sheet_h = h
            img = Image.new("RGB", (sheet_w, sheet_h), bg_rgb)
            draw = ImageDraw.Draw(img)

            col_w = sheet_w // 3
            cy = sheet_h // 2

            # Section 1: Front View (Symmetric)
            c1_x = col_w // 2
            draw.ellipse([c1_x - 70, cy - 80, c1_x + 70, cy + 90], fill=body_rgb)  # Torso
            draw.ellipse([c1_x - 45, cy - 160, c1_x + 45, cy - 85], fill=body_rgb)  # Head
            draw.rectangle([c1_x - 60, cy + 80, c1_x - 25, cy + 200], fill=body_rgb)  # Left leg
            draw.rectangle([c1_x + 25, cy + 80, c1_x + 60, cy + 200], fill=body_rgb)  # Right leg
            draw.line([(c1_x - 65, cy - 40), (c1_x - 110, cy + 40)], fill=accent_rgb, width=16)  # Left arm
            draw.line([(c1_x + 65, cy - 40), (c1_x + 110, cy + 40)], fill=accent_rgb, width=16)  # Right arm

            # Section 2: Side Profile View
            c2_x = col_w + col_w // 2
            draw.ellipse([c2_x - 85, cy - 75, c2_x + 60, cy + 85], fill=body_rgb)  # Lateral torso
            draw.ellipse([c2_x + 20, cy - 155, c2_x + 95, cy - 85], fill=body_rgb)  # Head
            draw.polygon([(c2_x + 80, cy - 135), (c2_x + 125, cy - 115), (c2_x + 80, cy - 95)], fill=accent_rgb)  # Snout
            draw.rectangle([c2_x - 40, cy + 80, c2_x - 10, cy + 200], fill=body_rgb)  # Front leg
            draw.rectangle([c2_x + 15, cy + 80, c2_x + 45, cy + 200], fill=accent_rgb)  # Back leg
            draw.line([(c2_x - 80, cy + 10), (c2_x - 150, cy + 70)], fill=body_rgb, width=16)  # Tail

            # Section 3: Back View
            c3_x = 2 * col_w + col_w // 2
            draw.ellipse([c3_x - 70, cy - 80, c3_x + 70, cy + 90], fill=body_rgb)  # Dorsal torso
            draw.ellipse([c3_x - 45, cy - 160, c3_x + 45, cy - 85], fill=body_rgb)  # Back of head
            draw.line([(c3_x, cy - 70), (c3_x, cy + 80)], fill=accent_rgb, width=8)  # Spine ridge
            draw.rectangle([c3_x - 60, cy + 80, c3_x - 25, cy + 200], fill=body_rgb)  # Left leg
            draw.rectangle([c3_x + 25, cy + 80, c3_x + 60, cy + 200], fill=body_rgb)  # Right leg
            draw.line([(c3_x, cy + 80), (c3_x, cy + 170)], fill=body_rgb, width=14)  # Tail downward

            return img

        # 2. Texture Map Mock
        if inp.task_type == "texture":
            img = Image.new("RGB", (w, h), (140, 120, 100))
            arr = np.zeros((h, w, 3), dtype=np.uint8)
            # Procedural multi-scale cellular noise pattern
            x = np.linspace(0, 8 * np.pi, w)
            y = np.linspace(0, 8 * np.pi, h)
            xx, yy = np.meshgrid(x, y)
            pattern = (np.sin(xx) * np.cos(yy) * 64 + 128).astype(np.uint8)
            arr[:, :, 0] = np.clip(pattern + 20, 0, 255)
            arr[:, :, 1] = np.clip(pattern, 0, 255)
            arr[:, :, 2] = np.clip(pattern - 20, 0, 255)
            return Image.fromarray(arr, mode="RGB")

        # 3. Standard Concept Silhouette Mock
        img = Image.new("RGB", (w, h), bg_rgb)
        draw = ImageDraw.Draw(img)
        cx, cy = w // 2, h // 2
        ctype = inp.creature_type.lower()

        if "biped" in ctype or "humanoid" in ctype:
            draw.ellipse([cx - 90, cy - 120, cx + 90, cy + 120], fill=body_rgb)
            draw.ellipse([cx - 60, cy - 240, cx + 60, cy - 130], fill=body_rgb)
            draw.line([(cx - 80, cy - 80), (cx - 180, cy + 60)], fill=accent_rgb, width=30)
            draw.line([(cx + 80, cy - 80), (cx + 180, cy + 60)], fill=accent_rgb, width=30)
            draw.rectangle([cx - 70, cy + 100, cx - 20, cy + 300], fill=body_rgb)
            draw.rectangle([cx + 20, cy + 100, cx + 70, cy + 300], fill=body_rgb)
        else:
            # Quadruped / Chimera
            draw.ellipse([cx - 200, cy - 70, cx + 180, cy + 80], fill=body_rgb)
            draw.polygon([(cx + 120, cy - 20), (cx + 220, cy - 140), (cx + 260, cy - 90), (cx + 160, cy + 20)], fill=body_rgb)
            draw.ellipse([cx + 200, cy - 160, cx + 290, cy - 80], fill=body_rgb)
            draw.rectangle([cx + 100, cy + 40, cx + 140, cy + 220], fill=body_rgb)
            draw.rectangle([cx + 60, cy + 40, cx + 90, cy + 200], fill=accent_rgb)
            draw.rectangle([cx - 160, cy + 40, cx - 120, cy + 220], fill=body_rgb)
            draw.rectangle([cx - 200, cy + 40, cx - 170, cy + 200], fill=accent_rgb)
            draw.line([(cx - 200, cy - 10), (cx - 320, cy + 60)], fill=body_rgb, width=20)

        return img

    # ==========================================================================
    # ASSET POST-PROCESSING & SEGMENTATION
    # ==========================================================================

    @staticmethod
    def _extract_clean_alpha(img: Image.Image, background: str) -> Image.Image:
        """Extract clean RGBA alpha mask based on color distance from neutral background."""
        rgba = img.convert("RGBA")
        arr = np.array(rgba, dtype=np.float32)
        rgb = arr[:, :, :3]

        if "white" in background.lower() or "light" in background.lower():
            target = np.array([255.0, 255.0, 255.0], dtype=np.float32)
        else:
            target = np.array([24.0, 24.0, 28.0], dtype=np.float32)

        dist = np.linalg.norm(rgb - target, axis=-1)
        # Soft transition between distance 15.0 and 45.0
        alpha = np.clip((dist - 15.0) / 30.0, 0.0, 1.0) * 255.0
        arr[:, :, 3] = alpha.astype(np.uint8)
        return Image.fromarray(arr.astype(np.uint8), mode="RGBA")

    @staticmethod
    def _derive_pbr_from_albedo(albedo_img: Image.Image, res: int) -> Tuple[Image.Image, Image.Image, Image.Image]:
        """Compute Normal, Roughness, and Metallic texture maps from BaseColor."""
        resized = albedo_img.convert("L").resize((res, res), Image.Resampling.BILINEAR)
        gray_arr = np.array(resized, dtype=np.float32) / 255.0

        # Sobel operator for Tangent Normal map
        dy, dx = np.gradient(gray_arr)
        strength = 4.0
        nx = -dx * strength
        ny = -dy * strength
        nz = np.ones_like(nx)
        norm = np.sqrt(nx**2 + ny**2 + nz**2)
        nx, ny, nz = nx / norm, ny / norm, nz / norm

        normal_arr = np.zeros((res, res, 3), dtype=np.uint8)
        normal_arr[:, :, 0] = np.clip((nx * 0.5 + 0.5) * 255.0, 0, 255).astype(np.uint8)
        normal_arr[:, :, 1] = np.clip((ny * 0.5 + 0.5) * 255.0, 0, 255).astype(np.uint8)
        normal_arr[:, :, 2] = np.clip((nz * 0.5 + 0.5) * 255.0, 0, 255).astype(np.uint8)
        normal_img = Image.fromarray(normal_arr, mode="RGB")

        # Roughness map: dielectric organic distribution [0.35, 0.85]
        roughness_arr = np.clip(0.85 - (gray_arr * 0.4), 0.2, 0.95) * 255.0
        roughness_img = Image.fromarray(roughness_arr.astype(np.uint8), mode="L")

        # Metallic map: black dielectric for organic creature surfaces
        metallic_arr = np.zeros((res, res), dtype=np.uint8)
        metallic_img = Image.fromarray(metallic_arr, mode="L")

        return normal_img, roughness_img, metallic_img

    def _process_and_save_workload(
        self,
        inp: GeminiImageInput,
        base_img: Image.Image,
        asset_id: str,
        out_dir: str,
        enhanced_prompt: str,
        effective_mode: str,
        duration: float,
    ) -> GeminiImageOutput:
        """Save files and segment turnaround views or compute PBR textures."""
        ext = inp.output_format.lower().lstrip(".")
        img_filename = f"{asset_id}.{ext}"
        primary_path = os.path.join(out_dir, img_filename)
        base_img.save(primary_path)

        rgba_path: Optional[str] = None
        if inp.extract_alpha:
            rgba_img = self._extract_clean_alpha(base_img, inp.background)
            rgba_filename = f"{asset_id}_rgba.png"
            rgba_path = os.path.join(out_dir, rgba_filename)
            rgba_img.save(rgba_path)

        views_map: Dict[str, str] = {}
        pbr_suite: Optional[PBRTextureMaps] = None

        # Turnaround Sheet Slicing: Crop front, side, and back views
        if inp.task_type == "turnaround" or any(
            vm in inp.view_mode.lower() for vm in ("turnaround", "orthographic", "turntable")
        ):
            views_map["turnaround_sheet"] = primary_path
            sw, sh = base_img.width, base_img.height
            col_w = sw // 3

            crops = {
                "front": base_img.crop((0, 0, col_w, sh)),
                "side": base_img.crop((col_w, 0, 2 * col_w, sh)),
                "back": base_img.crop((2 * col_w, 0, sw, sh)),
            }

            for view_name, c_img in crops.items():
                c_path = os.path.join(out_dir, f"{asset_id}_view_{view_name}.png")
                c_img.save(c_path)
                views_map[view_name] = c_path

                # Extract alpha for view crop
                if inp.extract_alpha:
                    c_rgba = self._extract_clean_alpha(c_img, inp.background)
                    c_rgba_path = os.path.join(out_dir, f"{asset_id}_view_{view_name}_rgba.png")
                    c_rgba.save(c_rgba_path)
                    views_map[f"{view_name}_rgba"] = c_rgba_path

        # Texture Synthesis: Bake Albedo, Normal, Roughness, Metallic
        if inp.task_type == "texture":
            res = min(base_img.width, base_img.height)
            albedo_path = os.path.join(out_dir, f"{asset_id}_albedo.png")
            base_img.convert("RGB").resize((res, res)).save(albedo_path)

            normal_img, roughness_img, metallic_img = self._derive_pbr_from_albedo(base_img, res)
            normal_path = os.path.join(out_dir, f"{asset_id}_normal.png")
            roughness_path = os.path.join(out_dir, f"{asset_id}_roughness.png")
            metallic_path = os.path.join(out_dir, f"{asset_id}_metallic.png")

            normal_img.save(normal_path)
            roughness_img.save(roughness_path)
            metallic_img.save(metallic_path)

            pbr_suite = PBRTextureMaps(
                albedo_path=albedo_path,
                normal_path=normal_path,
                roughness_path=roughness_path,
                metallic_path=metallic_path,
                resolution=res,
            )

        return GeminiImageOutput(
            asset_id=asset_id,
            image_path=primary_path,
            rgba_image_path=rgba_path,
            task_type=inp.task_type,
            prompt_enhanced=enhanced_prompt,
            width=base_img.width,
            height=base_img.height,
            views=views_map,
            pbr_textures=pbr_suite,
            backend_used="gemini",
            execution_mode=effective_mode,
            duration_seconds=duration,
            metadata={
                "model_name": self.gemini_config.model_name,
                "aspect_ratio": inp.aspect_ratio,
                "has_alpha": bool(rgba_path),
                "view_count": len(views_map),
                "is_mock": effective_mode == "mock",
            },
        )
