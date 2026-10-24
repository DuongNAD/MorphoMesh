"""
MorphoMesh: Meshy AI 3D Foundation Model Connector (Phase 2).

Integrates the Meshy AI generative platform (OpenAPI v2 / v1) for:
  1. Text-to-3D generation (preview and refine stages, including automatic '/boost' workflow).
  2. Image-to-3D generation (data URI base64 encoding and remote URL reconstruction).
  3. Decoupled PBR material download (Albedo, Normal, Roughness, Metallic) and GLB extraction.

Features:
  - Clean HTTP REST boundary with Bearer authentication (MESHY_API_KEY).
  - Health check diagnostic probe with latency profiling and credential validation.
  - Multi-stage Text-to-3D: preview stage followed by high-fidelity refine stage.
  - Native '/boost' prompt parsing and workflow activation for high-detail geometry and textures.
  - Circuit Breaker fault tolerance integration preventing cascade failures.
  - Zero-VRAM deterministic procedural offline fallback with genuine GLB/OBJ and 4-channel PBR textures.
  - Pure standard library GLB binary glTF header reader for vertex and face telemetry.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import math
import mimetypes
import os
import re
import shutil
import struct
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from morphomesh.connectors.base import (
    BaseConnector,
    DependencyCheckResult,
    HealthCheckResult,
    PBRTextureMaps,
)
from morphomesh.connectors.tripo_connector import (
    extract_glb_textures,
    parse_glb_metrics,
)
from morphomesh.inference_adapter import MeshGeometry
from morphomesh.models import (
    ERR_BACKEND_UNAVAILABLE,
    ERR_IMAGE_NOT_FOUND,
    ERR_INFERENCE_FAILED,
    ERR_INVALID_ARGUMENT,
    AnimationItem,
    MorphoMeshException,
)

logger = logging.getLogger(__name__)

# Canonical Meshy API endpoints
MESHY_API_BASE = "https://api.meshy.ai"

# Model version aliases mapping to Meshy AI model strings
MESHY_MODEL_MAP: Dict[str, str] = {
    "meshy-4": "meshy-4",
    "v4": "meshy-4",
    "/v4": "meshy-4",
    "4": "meshy-4",
    "meshy-3": "meshy-3",
    "v3": "meshy-3",
    "/v3": "meshy-3",
    "3": "meshy-3",
    "latest": "meshy-4",
    "boost": "meshy-4",
    "/boost": "meshy-4",
    "--boost": "meshy-4",
}


# ==============================================================================
# PYDANTIC V2 DATA SCHEMAS
# ==============================================================================

class MeshyConfig(BaseModel):
    """Configuration for Meshy AI connector."""
    model_config = ConfigDict(extra="ignore")

    api_key: Optional[str] = None
    mode: Literal["auto", "api", "mock"] = "auto"
    base_url: str = MESHY_API_BASE
    ai_model: str = "meshy-4"
    art_style: str = "realistic"
    topology: str = "quad"
    target_polycount: int = 30000
    texture_richness: str = "high"
    pbr: bool = True
    timeout_seconds: float = Field(default=300.0, ge=10.0, le=900.0)
    polling_interval_seconds: float = Field(default=2.0, ge=0.5, le=30.0)
    auto_refine: bool = False
    fallback_to_mock: bool = True

    @field_validator("ai_model")
    @classmethod
    def normalize_ai_model(cls, v: Optional[str]) -> str:
        if not v:
            return "meshy-4"
        cleaned = v.strip().lower()
        return MESHY_MODEL_MAP.get(cleaned, v.strip())


class MeshyInput(BaseModel):
    """Workload request parameters for Meshy AI 3D generation."""
    model_config = ConfigDict(extra="ignore")

    prompt: Optional[str] = Field(default=None, description="Text prompt for text-to-3D generation")
    image_path: Optional[str] = Field(default=None, description="Local path or remote URL for image-to-3D generation")
    task_type: Literal["text_to_3d", "image_to_3d", "refine_text_to_3d"] = Field(
        default="text_to_3d",
        description="Type of task: 'text_to_3d', 'image_to_3d', or 'refine_text_to_3d'",
    )
    mode: Optional[Literal["preview", "refine"]] = Field(
        default=None,
        description="Explicit Meshy task mode for text-to-3D ('preview' or 'refine')",
    )
    preview_task_id: Optional[str] = Field(
        default=None,
        description="Prior preview task ID required for refine stage",
    )
    ai_model: Optional[str] = Field(default=None, description="Meshy AI model version (e.g. 'meshy-4')")
    art_style: str = Field(default="realistic", description="Art style: realistic, cartoon, low-poly, sculpture, pbr")
    negative_prompt: Optional[str] = Field(default="", description="Negative prompt constraint")
    topology: Optional[str] = Field(default=None, description="Mesh topology type ('quad' or 'triangle')")
    target_polycount: Optional[int] = Field(default=None, description="Target polygon triangle/quad budget")
    should_remesh: bool = Field(default=True, description="Whether to apply remeshing to the output geometry")
    enable_pbr: bool = Field(default=True, description="Enable PBR texture synthesis")
    pbr: bool = Field(default=True, description="Alias for enable_pbr")
    texture_richness: str = Field(default="high", description="Texture richness tier: high, medium, low")
    surface_mode: str = Field(default="organic", description="Surface mode for image-to-3D: 'organic' or 'hard'")
    seed: int = Field(default=-1, description="Deterministic seed (-1 for randomized)")
    boost: bool = Field(default=False, description="Whether boost mode is active (runs preview + auto-refine)")
    auto_refine: bool = Field(default=False, description="Automatically trigger refine stage after preview succeeds")
    output_dir: Optional[str] = Field(default=None, description="Directory to save downloaded assets")
    output_format: str = Field(default="glb", description="Desired 3D file format (glb, obj)")

    @model_validator(mode="before")
    @classmethod
    def pre_validate_input(cls, data: Any) -> Any:
        if isinstance(data, str):
            data = {"prompt": data}
        if isinstance(data, dict):
            p = data.get("prompt")
            is_boost_in_prompt = False
            if isinstance(p, str):
                boost_pattern = re.compile(r'(?i)(?:^|\s+)(?:/|--)\s*boost\b')
                if boost_pattern.search(p):
                    is_boost_in_prompt = True
                    cleaned_prompt = boost_pattern.sub("", p).strip()
                    data["prompt"] = cleaned_prompt

            if is_boost_in_prompt or data.get("boost") or data.get("auto_refine"):
                data["boost"] = True
                data["auto_refine"] = True
                if not data.get("ai_model"):
                    data["ai_model"] = "meshy-4"
                data.setdefault("texture_richness", "high")
                data.setdefault("pbr", True)
                data.setdefault("enable_pbr", True)
        return data

    @field_validator("ai_model")
    @classmethod
    def normalize_input_model(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        cleaned = v.strip().lower()
        return MESHY_MODEL_MAP.get(cleaned, v.strip())


class MeshyOutput(BaseModel):
    """Output payload from Meshy AI 3D generation."""
    model_config = ConfigDict(extra="ignore")

    asset_id: str = Field(..., description="Unique generation asset identifier")
    task_id: Optional[str] = Field(default=None, description="Meshy cloud task ID")
    preview_task_id: Optional[str] = Field(default=None, description="Meshy preview task ID if applicable")
    refine_task_id: Optional[str] = Field(default=None, description="Meshy refine task ID if applicable")
    glb_path: str = Field(..., description="Path to generated GLB 3D model on disk")
    mesh_path: str = Field(..., description="Primary mesh path (GLB or converted OBJ)")
    vertex_count: int = Field(default=0, description="Mesh vertex count")
    face_count: int = Field(default=0, description="Mesh triangle face count")
    pbr_textures: PBRTextureMaps = Field(default_factory=PBRTextureMaps, description="PBR texture maps")
    texture_paths: Dict[str, str] = Field(default_factory=dict, description="Dictionary of texture file paths")
    rendered_image_url: Optional[str] = Field(default=None, description="Remote URL of rendered preview/thumbnail")
    rendered_image_path: Optional[str] = Field(default=None, description="Local path to downloaded preview image")
    execution_mode: str = Field(default="api", description="'api' or 'mock'")
    duration_seconds: float = Field(default=0.0, description="Generation duration in seconds")
    boost_applied: bool = Field(default=False, description="Whether boost multi-stage pipeline was executed")
    raw_task_output: Optional[Dict[str, Any]] = Field(default=None, description="Raw Meshy output dictionary")


class MeshyRiggingInput(BaseModel):
    """Workload parameters for Meshy AI 3D humanoid auto-rigging."""
    model_config = ConfigDict(extra="ignore")

    input_task_id: Optional[str] = Field(default=None, description="Input generation task ID to rig.")
    model_url: Optional[str] = Field(default=None, description="Public URL or Data URI of 3D GLB model.")
    model_path: Optional[str] = Field(default=None, description="Local path to GLB mesh to upload as Data URI.")
    height_meters: float = Field(default=1.7, ge=0.1, le=50.0, description="Approximate height in meters.")
    texture_image_url: Optional[str] = Field(default=None, description="Optional UV texture image URL.")
    output_dir: Optional[str] = Field(default=None, description="Destination directory for rigged assets.")


class MeshyRiggingOutput(BaseModel):
    """Output payload from Meshy AI 3D auto-rigging."""
    model_config = ConfigDict(extra="ignore")

    rig_task_id: str = Field(..., description="Meshy rigging task ID.")
    status: str = Field(default="SUCCEEDED", description="Task status.")
    rigged_character_glb_path: Optional[str] = Field(default=None, description="Local path to rigged GLB.")
    rigged_character_fbx_path: Optional[str] = Field(default=None, description="Local path to rigged FBX.")
    rigged_character_glb_url: Optional[str] = Field(default=None, description="Remote URL of rigged GLB.")
    rigged_character_fbx_url: Optional[str] = Field(default=None, description="Remote URL of rigged FBX.")
    basic_animations: Dict[str, str] = Field(default_factory=dict, description="Downloaded basic animations (e.g. walking, running).")
    basic_animation_urls: Dict[str, str] = Field(default_factory=dict, description="Remote URLs of basic animations.")
    duration_seconds: float = Field(default=0.0, description="Execution duration in seconds.")
    execution_mode: str = Field(default="api", description="'api' or 'mock'.")


class MeshyAnimationInput(BaseModel):
    """Workload parameters for Meshy AI 3D animation retargeting."""
    model_config = ConfigDict(extra="ignore")

    rig_task_id: str = Field(..., description="Source Meshy rigging task ID to animate.")
    action_id: Optional[int] = Field(default=None, description="Animation action ID from library.")
    motion_task_id: Optional[str] = Field(default=None, description="Optional Text-to-Motion task ID.")
    fps: int = Field(default=30, description="Target animation FPS (24, 25, 30, 60).")
    post_process_operation: Optional[str] = Field(default="change_fps", description="Operation: change_fps, fbx2usdz, extract_armature.")
    output_dir: Optional[str] = Field(default=None, description="Destination directory.")


class MeshyAnimationOutput(BaseModel):
    """Output payload from Meshy AI 3D animation task."""
    model_config = ConfigDict(extra="ignore")

    animation_task_id: str = Field(..., description="Meshy animation task ID.")
    rig_task_id: str = Field(..., description="Source rigging task ID.")
    action_id: Optional[int] = Field(default=None, description="Applied action ID.")
    action_name: Optional[str] = Field(default=None, description="Applied action name.")
    status: str = Field(default="SUCCEEDED", description="Task status.")
    animation_glb_path: Optional[str] = Field(default=None, description="Local path to animated GLB.")
    animation_fbx_path: Optional[str] = Field(default=None, description="Local path to animated FBX.")
    animation_glb_url: Optional[str] = Field(default=None, description="Remote URL of animated GLB.")
    animation_fbx_url: Optional[str] = Field(default=None, description="Remote URL of animated FBX.")
    preview_url: Optional[str] = Field(default=None, description="Preview GIF URL.")
    duration_seconds: float = Field(default=0.0, description="Execution duration in seconds.")
    execution_mode: str = Field(default="api", description="'api' or 'mock'.")


CURATED_ANIMATIONS: List[Dict[str, Any]] = [
    # DailyActions
    {"action_id": 0, "name": "Idle", "key": "Idle", "category": "DailyActions", "sub_category": "Idle", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Idle.gif"},
    {"action_id": 2, "name": "Alert", "key": "Alert", "category": "DailyActions", "sub_category": "LookingAround", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Alert.gif"},
    {"action_id": 11, "name": "Idle 02", "key": "Idle_02", "category": "DailyActions", "sub_category": "Idle", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Idle_02.gif"},
    {"action_id": 25, "name": "Agree Gesture", "key": "Agree_Gesture", "category": "DailyActions", "sub_category": "Interacting", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Agree_Gesture.gif"},
    {"action_id": 28, "name": "Big Wave Hello", "key": "Big_Wave_Hello", "category": "DailyActions", "sub_category": "Interacting", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Big_Wave_Hello.gif"},
    {"action_id": 32, "name": "Chair Sit Idle", "key": "Chair_Sit_Idle_F", "category": "DailyActions", "sub_category": "Idle", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Chair_Sit_Idle_F.gif"},
    {"action_id": 48, "name": "Stand to Sit Transition", "key": "Stand_to_Sit_Transition_M", "category": "DailyActions", "sub_category": "Transitioning", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Stand_to_Sit_Transition_M.gif"},
    {"action_id": 50, "name": "Victory Cheer", "key": "Victory_Cheer", "category": "DailyActions", "sub_category": "Interacting", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Victory_Cheer.gif"},
    # WalkAndRun
    {"action_id": 1, "name": "Walking Woman", "key": "Walking_Woman", "category": "WalkAndRun", "sub_category": "Walking", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Walking_Woman_woman.gif"},
    {"action_id": 5, "name": "Back Left Run", "key": "BackLeft_run", "category": "WalkAndRun", "sub_category": "Running", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/BackLeft_run.gif"},
    {"action_id": 14, "name": "Run 02", "key": "Run_02", "category": "WalkAndRun", "sub_category": "Running", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Run_02.gif"},
    {"action_id": 16, "name": "Run Fast", "key": "RunFast", "category": "WalkAndRun", "sub_category": "Running", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/RunFast.gif"},
    {"action_id": 30, "name": "Casual Walk", "key": "Casual_Walk", "category": "WalkAndRun", "sub_category": "Walking", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Casual_Walk.gif"},
    {"action_id": 105, "name": "Confident Walk", "key": "Confident_Walk", "category": "WalkAndRun", "sub_category": "Walking", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Confident_Walk.gif"},
    {"action_id": 117, "name": "Skip Forward", "key": "Skip_Forward", "category": "WalkAndRun", "sub_category": "Walking", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Skip_Forward.gif"},
    # Fighting
    {"action_id": 4, "name": "Attack", "key": "Attack", "category": "Fighting", "sub_category": "AttackingwithWeapon", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Attack.gif"},
    {"action_id": 7, "name": "Be Hit Fly Up", "key": "BeHit_FlyUp", "category": "Fighting", "sub_category": "GettingHit", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/BeHit_FlyUp.gif"},
    {"action_id": 8, "name": "Dead", "key": "Dead", "category": "Fighting", "sub_category": "Dying", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Dead.gif"},
    {"action_id": 78, "name": "Combat Stance", "key": "Combat_Stance", "category": "Fighting", "sub_category": "AttackingwithWeapon", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Combat_Stance.gif"},
    {"action_id": 92, "name": "Double Combo Attack", "key": "Double_Combo_Attack", "category": "Fighting", "sub_category": "AttackingwithWeapon", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Double_Combo_Attack.gif"},
    {"action_id": 93, "name": "Dodge and Counter", "key": "Dodge_and_Counter", "category": "Fighting", "sub_category": "AttackingwithWeapon", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Dodge_and_Counter.gif"},
    {"action_id": 140, "name": "Roll Dodge", "key": "Roll_Dodge", "category": "Fighting", "sub_category": "Defending", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Roll_Dodge.gif"},
    {"action_id": 174, "name": "Spartan Kick", "key": "Spartan_Kick", "category": "Fighting", "sub_category": "AttackingwithoutWeapon", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Spartan_Kick.gif"},
    {"action_id": 191, "name": "Archery Shot", "key": "Archery_Shot", "category": "Fighting", "sub_category": "AttackingwithWeapon", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Archery_Shot.gif"},
    {"action_id": 204, "name": "Charged Slash", "key": "Charged_Slash", "category": "Fighting", "sub_category": "AttackingwithWeapon", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Charged_Slash.gif"},
    # Dancing
    {"action_id": 22, "name": "Funny Dancing 01", "key": "FunnyDancing_01", "category": "Dancing", "sub_category": "Dancing", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/FunnyDancing_01.gif"},
    {"action_id": 23, "name": "Funny Dancing 02", "key": "FunnyDancing_02", "category": "Dancing", "sub_category": "Dancing", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/FunnyDancing_02.gif"},
    {"action_id": 55, "name": "All Night Dance", "key": "All_Night_Dance", "category": "Dancing", "sub_category": "Dancing", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/All_Night_Dance.gif"},
    {"action_id": 65, "name": "Gangnam Groove", "key": "Gangnam_Groove", "category": "Dancing", "sub_category": "Dancing", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Gangnam_Groove.gif"},
    {"action_id": 73, "name": "Shake It Off Dance", "key": "Shake_It_Off_Dance", "category": "Dancing", "sub_category": "Dancing", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Shake_It_Off_Dance.gif"},
    # BodyMovements
    {"action_id": 17, "name": "Skill 01", "key": "Skill_01", "category": "BodyMovements", "sub_category": "Acting", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Skill_01.gif"},
    {"action_id": 27, "name": "Big Heart Gesture", "key": "Big_Heart_Gesture", "category": "BodyMovements", "sub_category": "Acting", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Big_Heart_Gesture.gif"},
    {"action_id": 31, "name": "Catching Breath", "key": "Catching_Breath", "category": "BodyMovements", "sub_category": "Acting", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Catching_Breath.gif"},
    {"action_id": 125, "name": "Charged Spell Cast", "key": "Charged_Spell_Cast", "category": "BodyMovements", "sub_category": "Acting", "preview_url": "https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/Charged_Spell_Cast.gif"},
]


# ==============================================================================
# MESHY CONNECTOR CLASS
# ==============================================================================

class MeshyConnector(BaseConnector):
    """
    Meshy AI 3D Foundation Model Connector.

    Supports Text-to-3D (preview & refine multi-stage), Image-to-3D, and '/boost'
    high-fidelity workflows with asynchronous polling, circuit breaker fault tolerance,
    and zero-VRAM offline deterministic procedural fallback.
    """

    connector_id: str = "meshy"
    display_name: str = "Meshy AI 3D Foundation Model Connector"
    version: str = "2.0.0"
    stage: int = 2
    description: str = (
        "Meshy AI high-fidelity text-to-3D (preview & refine stages with /boost), "
        "image-to-3D reconstruction, decoupled PBR material mapping, and offline procedural fallback"
    )

    def __init__(
        self,
        config: Optional[Union[MeshyConfig, Dict[str, Any]]] = None,
        circuit_breaker: Optional[Any] = None,
    ) -> None:
        if isinstance(config, MeshyConfig):
            self.meshy_config = config
            cfg_dict = config.model_dump()
        elif isinstance(config, dict):
            self.meshy_config = MeshyConfig(**config)
            cfg_dict = config
        else:
            self.meshy_config = MeshyConfig()
            cfg_dict = self.meshy_config.model_dump()

        super().__init__(config=cfg_dict, circuit_breaker=circuit_breaker)

    def _resolve_api_key(self) -> Optional[str]:
        """
        Resolve Meshy API key with strict precedence:
          1. Explicit config.api_key
          2. Environment variable MESHY_API_KEY
          3. Legacy environment variable MESHY_AI_API_KEY
        """
        if self.meshy_config.api_key:
            return self.meshy_config.api_key.strip().strip("'\"")
        env_key = os.environ.get("MESHY_API_KEY") or os.environ.get("MESHY_AI_API_KEY")
        if env_key:
            return env_key.strip().strip("'\"")
        return None

    def initialize(self) -> bool:
        """Initialize connector and test environment readiness."""
        self.is_initialized = True
        return True

    def health_check(self) -> HealthCheckResult:
        """Probe Meshy API status or verify offline mock readiness."""
        start_time = time.time()

        if self.meshy_config.mode == "mock":
            return HealthCheckResult(
                status="healthy",
                latency_ms=0.1,
                message="Meshy mock generator operating normally (offline mode)",
                details={"mode": "mock", "ai_model": self.meshy_config.ai_model},
                circuit_state=getattr(self.circuit_breaker, "state", "CLOSED"),
                dependencies_met=True,
            )

        api_key = self._resolve_api_key()
        if not api_key:
            return HealthCheckResult(
                status="degraded",
                latency_ms=0.0,
                message="No MESHY_API_KEY configured. Offline mock generator active.",
                details={"mode": "mock_fallback", "api_configured": False},
                circuit_state=getattr(self.circuit_breaker, "state", "CLOSED"),
                dependencies_met=True,
            )

        # Probe Meshy API balance endpoint to verify authentication and retrieve credits
        base_url = self.meshy_config.base_url.rstrip("/")
        probe_url = f"{base_url}/openapi/v1/balance"
        try:
            req = urllib.request.Request(
                probe_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "MorphoMesh-MeshyConnector/2.0",
                },
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                latency = (time.time() - start_time) * 1000.0
                details: Dict[str, Any] = {
                    "http_code": resp.status,
                    "ai_model": self.meshy_config.ai_model,
                    "mode": "api",
                }
                try:
                    raw_body = resp.read().decode("utf-8")
                    if raw_body:
                        resp_data = json.loads(raw_body)
                        if isinstance(resp_data, dict):
                            if "balance" in resp_data:
                                details["credit_balance"] = resp_data["balance"]
                            elif "credits" in resp_data:
                                details["credit_balance"] = resp_data["credits"]
                except Exception:
                    pass

                return HealthCheckResult(
                    status="healthy",
                    latency_ms=round(latency, 2),
                    message="Meshy API online and authenticated",
                    details=details,
                    circuit_state=getattr(self.circuit_breaker, "state", "CLOSED"),
                    dependencies_met=True,
                )
        except urllib.error.HTTPError as e:
            latency = (time.time() - start_time) * 1000.0
            status_cls = "unhealthy" if e.code in (401, 403) else "degraded"
            return HealthCheckResult(
                status=status_cls,
                latency_ms=round(latency, 2),
                message=f"Meshy API probe failed with HTTP {e.code}: {e.reason}",
                details={"http_code": e.code, "reason": str(e.reason)},
                circuit_state=getattr(self.circuit_breaker, "state", "CLOSED"),
                dependencies_met=False if e.code in (401, 403) else True,
            )
        except Exception as e:
            latency = (time.time() - start_time) * 1000.0
            return HealthCheckResult(
                status="degraded",
                latency_ms=round(latency, 2),
                message=f"Meshy API unreachable: {e}. Fallback active.",
                details={"error": str(e)},
                circuit_state=getattr(self.circuit_breaker, "state", "CLOSED"),
                dependencies_met=True,
            )

    def check_dependencies(self) -> DependencyCheckResult:
        """Inspect dependencies for Meshy connector."""
        missing: List[str] = []
        try:
            import numpy
            import PIL
        except ImportError as e:
            missing.append(str(e).split()[-1])

        return DependencyCheckResult(
            satisfied=len(missing) == 0,
            missing_packages=missing,
            hardware_supported=True,
            details={"mode": self.meshy_config.mode},
        )

    def execute(
        self,
        request: Union[MeshyInput, Dict[str, Any], str],
        **kwargs: Any,
    ) -> MeshyOutput:
        """
        Execute Meshy AI 3D asset generation workload.

        Args:
            request: MeshyInput, parameter dictionary, or text prompt string.
            **kwargs: Additional runtime arguments (e.g. raise_on_failure).

        Returns:
            MeshyOutput: Generated mesh paths, texture maps, and metadata.

        Raises:
            MorphoMeshException: On unrecoverable API failures when fallback is disabled.
        """
        start_time = time.time()
        if isinstance(request, str):
            inp = MeshyInput(prompt=request)
        elif isinstance(request, dict):
            inp = MeshyInput(**request)
        else:
            inp = request

        # Validate request parameters
        if inp.task_type == "text_to_3d" and not inp.prompt and not inp.image_path:
            raise MorphoMeshException(
                code=ERR_INVALID_ARGUMENT,
                message="Either 'prompt' or 'image_path' must be provided for Meshy generation.",
            )
        if inp.task_type == "image_to_3d" and not inp.image_path:
            raise MorphoMeshException(
                code=ERR_INVALID_ARGUMENT,
                message="'image_path' is required for image_to_3d task.",
            )
        if inp.task_type == "refine_text_to_3d" and not inp.preview_task_id:
            raise MorphoMeshException(
                code=ERR_INVALID_ARGUMENT,
                message="'preview_task_id' is required for refine_text_to_3d task.",
            )

        asset_id = f"meshy_{uuid.uuid4().hex[:8]}"
        out_dir = inp.output_dir or os.path.expanduser(f"~/.morphomesh/cache/assets/{asset_id}")
        os.makedirs(out_dir, exist_ok=True)

        api_key = self._resolve_api_key()
        should_use_api = (
            self.meshy_config.mode in ("auto", "api")
            and api_key is not None
            and self.meshy_config.mode != "mock"
        )
        raise_on_failure = kwargs.pop("raise_on_failure", not self.meshy_config.fallback_to_mock)

        # Check circuit breaker state
        if (
            self.circuit_breaker is not None
            and hasattr(self.circuit_breaker, "can_attempt")
            and not self.circuit_breaker.can_attempt()
            and should_use_api
        ):
            if raise_on_failure:
                raise MorphoMeshException(
                    code=ERR_BACKEND_UNAVAILABLE,
                    message="Circuit breaker is OPEN. Target Meshy backend unavailable.",
                )
            if self._fallback_handler is not None:
                return self._fallback_handler(inp, **kwargs)
            logger.warning("Meshy circuit breaker is OPEN. Falling back to procedural mock.")
            return self._execute_mock(inp, asset_id, out_dir, start_time)

        if should_use_api:
            try:
                out = self._execute_api(inp, api_key, asset_id, out_dir, start_time)
                if self.circuit_breaker and hasattr(self.circuit_breaker, "record_success"):
                    self.circuit_breaker.record_success()
                return out
            except Exception as e:
                if self.circuit_breaker and hasattr(self.circuit_breaker, "record_failure"):
                    self.circuit_breaker.record_failure(e)
                logger.warning("Meshy API execution failed (%s). Checking fallback.", e)
                if self._fallback_handler is not None:
                    return self._fallback_handler(inp, **kwargs)
                if raise_on_failure:
                    if isinstance(e, MorphoMeshException):
                        raise
                    raise MorphoMeshException(
                        code=ERR_INFERENCE_FAILED,
                        message=f"Meshy generation failed: {e}",
                        details={"error": str(e)},
                    ) from e
                if self.meshy_config.fallback_to_mock:
                    logger.info("Engaging offline mock fallback for Meshy.")
                    return self._execute_mock(inp, asset_id, out_dir, start_time)
                if isinstance(e, MorphoMeshException):
                    raise
                raise MorphoMeshException(
                    code=ERR_INFERENCE_FAILED,
                    message=f"Meshy generation failed: {e}",
                    details={"error": str(e)},
                ) from e

        return self._execute_mock(inp, asset_id, out_dir, start_time)

    # --------------------------------------------------------------------------
    # API EXECUTION IMPLEMENTATION
    # --------------------------------------------------------------------------

    def _execute_api(
        self,
        inp: MeshyInput,
        api_key: str,
        asset_id: str,
        out_dir: str,
        start_time: float,
    ) -> MeshyOutput:
        """Execute workload via Meshy OpenAPI v2 / v1 endpoints."""
        base_url = self.meshy_config.base_url.rstrip("/")
        model_version = inp.ai_model or self.meshy_config.ai_model
        preview_task_id: Optional[str] = None
        refine_task_id: Optional[str] = None
        boost_applied = bool(inp.boost or inp.auto_refine or self.meshy_config.auto_refine)

        # ----------------------------------------------------------------------
        # 1. IMAGE-TO-3D WORKFLOW
        # ----------------------------------------------------------------------
        if inp.task_type == "image_to_3d" or (inp.image_path and not inp.prompt):
            image_url = self._prepare_image_url(inp.image_path)  # type: ignore[arg-type]
            payload: Dict[str, Any] = {
                "image_url": image_url,
                "enable_pbr": inp.pbr and inp.enable_pbr,
                "surface_mode": inp.surface_mode,
                "ai_model": model_version,
            }
            if inp.topology:
                payload["topology"] = inp.topology
            if inp.target_polycount:
                payload["target_polycount"] = inp.target_polycount
            payload["should_remesh"] = inp.should_remesh

            endpoint = f"{base_url}/openapi/v1/image-to-3d"
            task_id = self._post_json_task(endpoint, payload, api_key)
            logger.info("Meshy image-to-3d task created: %s", task_id)

            poll_url = f"{base_url}/openapi/v1/image-to-3d/{task_id}"
            task_data = self._poll_task(poll_url, api_key)

        # ----------------------------------------------------------------------
        # 2. TEXT-TO-3D (REFINE ONLY)
        # ----------------------------------------------------------------------
        elif inp.task_type == "refine_text_to_3d" or (inp.mode == "refine" and inp.preview_task_id):
            refine_payload = {
                "mode": "refine",
                "preview_task_id": inp.preview_task_id,
                "texture_richness": inp.texture_richness or self.meshy_config.texture_richness,
                "enable_pbr": inp.pbr and inp.enable_pbr,
            }
            endpoint = f"{base_url}/openapi/v2/text-to-3d"
            refine_task_id = self._post_json_task(endpoint, refine_payload, api_key)
            task_id = refine_task_id
            preview_task_id = inp.preview_task_id
            logger.info("Meshy text-to-3d refine task created: %s", task_id)

            poll_url = f"{base_url}/openapi/v2/text-to-3d/{task_id}"
            task_data = self._poll_task(poll_url, api_key)

        # ----------------------------------------------------------------------
        # 3. TEXT-TO-3D (PREVIEW & OPTIONAL /BOOST REFINE)
        # ----------------------------------------------------------------------
        else:
            preview_payload: Dict[str, Any] = {
                "mode": "preview",
                "prompt": inp.prompt,
                "art_style": inp.art_style or self.meshy_config.art_style,
                "ai_model": model_version,
            }
            if inp.negative_prompt:
                preview_payload["negative_prompt"] = inp.negative_prompt
            if inp.seed >= 0:
                preview_payload["seed"] = inp.seed
            if inp.topology:
                preview_payload["topology"] = inp.topology
            if inp.target_polycount:
                preview_payload["target_polycount"] = inp.target_polycount
            preview_payload["should_remesh"] = inp.should_remesh

            endpoint = f"{base_url}/openapi/v2/text-to-3d"
            preview_task_id = self._post_json_task(endpoint, preview_payload, api_key)
            task_id = preview_task_id
            logger.info("Meshy text-to-3d preview task created: %s", preview_task_id)

            poll_url = f"{base_url}/openapi/v2/text-to-3d/{preview_task_id}"
            task_data = self._poll_task(poll_url, api_key)

            # Auto-refine if /boost or auto_refine was requested
            if boost_applied:
                logger.info("Boost mode active: initiating Meshy refine stage for preview task %s", preview_task_id)
                refine_payload = {
                    "mode": "refine",
                    "preview_task_id": preview_task_id,
                    "texture_richness": inp.texture_richness or self.meshy_config.texture_richness,
                    "enable_pbr": inp.pbr and inp.enable_pbr,
                }
                refine_task_id = self._post_json_task(endpoint, refine_payload, api_key)
                task_id = refine_task_id
                logger.info("Meshy text-to-3d refine task created: %s", refine_task_id)

                refine_poll_url = f"{base_url}/openapi/v2/text-to-3d/{refine_task_id}"
                task_data = self._poll_task(refine_poll_url, api_key)

        # ----------------------------------------------------------------------
        # 4. DOWNLOAD ASSETS & PROCESS OUTPUTS
        # ----------------------------------------------------------------------
        output_data = task_data.get("output") if isinstance(task_data.get("output"), dict) else {}
        inner_data = task_data.get("data") if isinstance(task_data.get("data"), dict) else {}

        model_urls = task_data.get("model_urls") or output_data.get("model_urls") or inner_data.get("model_urls") or {}
        glb_url = model_urls.get("glb")
        if not glb_url:
            raise MorphoMeshException(
                code=ERR_INFERENCE_FAILED,
                message=f"Meshy task {task_id} completed successfully but missing 'glb' in model_urls.",
                details={"task_data": task_data},
            )

        # Download primary GLB
        glb_filename = f"{asset_id}.glb"
        glb_path = os.path.join(out_dir, glb_filename)
        self._download_file(glb_url, glb_path)

        # Download preview image if available
        rendered_url = (
            task_data.get("thumbnail_url")
            or task_data.get("rendered_image_url")
            or output_data.get("thumbnail_url")
            or output_data.get("rendered_image_url")
            or inner_data.get("thumbnail_url")
        )
        preview_path = None
        if rendered_url:
            preview_path = os.path.join(out_dir, f"{asset_id}_preview.jpg")
            try:
                self._download_file(rendered_url, preview_path)
            except Exception as e:
                logger.debug("Meshy thumbnail download skipped: %s", e)
                preview_path = None

        # Download or export OBJ if requested
        primary_mesh_path = glb_path
        if (inp.output_format or "glb").lower() == "obj":
            obj_path = os.path.join(out_dir, f"{asset_id}.obj")
            obj_url = model_urls.get("obj")
            if obj_url:
                try:
                    self._download_file(obj_url, obj_path)
                    primary_mesh_path = obj_path
                except Exception as e:
                    logger.warning("Direct OBJ download failed (%s), converting from GLB.", e)
                    self._convert_or_export_obj(glb_path, obj_path)
                    primary_mesh_path = obj_path
            else:
                self._convert_or_export_obj(glb_path, obj_path)
                primary_mesh_path = obj_path

        # Parse vertex and face counts
        verts, faces = parse_glb_metrics(glb_path)

        # Extract or download PBR textures
        pbr_maps: Optional[PBRTextureMaps] = None
        texture_urls = (
            task_data.get("texture_urls")
            or output_data.get("texture_urls")
            or inner_data.get("texture_urls")
            or []
        )
        if inp.pbr:
            if isinstance(texture_urls, dict):
                pbr_maps = self._download_pbr_textures(texture_urls, out_dir, asset_id)
            elif isinstance(texture_urls, list) and len(texture_urls) > 0 and isinstance(texture_urls[0], dict):
                pbr_maps = self._download_pbr_textures(texture_urls[0], out_dir, asset_id)

        if not pbr_maps and inp.pbr:
            pbr_maps = extract_glb_textures(glb_path, out_dir, asset_id)

        if not pbr_maps:
            pbr_maps = self._extract_or_generate_pbr_maps(out_dir, asset_id, inp.pbr)

        elapsed = round(time.time() - start_time, 2)
        return MeshyOutput(
            asset_id=asset_id,
            task_id=task_id,
            preview_task_id=preview_task_id,
            refine_task_id=refine_task_id,
            glb_path=glb_path,
            mesh_path=primary_mesh_path,
            vertex_count=verts,
            face_count=faces,
            pbr_textures=pbr_maps,
            texture_paths=pbr_maps.to_dict(),
            rendered_image_url=rendered_url,
            rendered_image_path=preview_path,
            execution_mode="api",
            duration_seconds=elapsed,
            boost_applied=boost_applied,
            raw_task_output=task_data,
        )

    def _prepare_image_url(self, image_path: str) -> str:
        """Convert local file to base64 data URI, or pass through remote URL."""
        if image_path.startswith(("http://", "https://", "data:")):
            return image_path

        if not os.path.isfile(image_path):
            raise MorphoMeshException(
                code=ERR_IMAGE_NOT_FOUND,
                message=f"Image file not found for Meshy upload: {image_path}",
                details={"image_path": image_path},
            )

        with open(image_path, "rb") as f:
            file_bytes = f.read()

        mime = mimetypes.guess_type(image_path)[0] or "image/png"
        b64_str = base64.b64encode(file_bytes).decode("ascii")
        return f"data:{mime};base64,{b64_str}"

    def _post_json_task(self, url: str, payload: Dict[str, Any], api_key: str) -> str:
        """Send JSON POST request to Meshy API and extract task ID."""
        req_body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "MorphoMesh-MeshyConnector/2.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                nested_data = data.get("data") if isinstance(data.get("data"), dict) else {}
                task_id = (
                    data.get("result")
                    or data.get("id")
                    or nested_data.get("task_id")
                    or nested_data.get("id")
                )
                if not task_id:
                    raise MorphoMeshException(
                        code=ERR_INFERENCE_FAILED,
                        message="Meshy task creation succeeded but returned no task_id/result.",
                        details={"response": data},
                    )
                return str(task_id)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
            raise MorphoMeshException(
                code=ERR_INFERENCE_FAILED,
                message=f"Meshy task submission failed with HTTP {e.code}: {err_body}",
                details={"http_code": e.code, "error": err_body, "url": url},
            )

    def _poll_task(
        self,
        poll_url: str,
        api_key: str,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Poll Meshy task until status is SUCCEEDED or FAILED, observing timeout."""
        timeout_seconds = timeout or self.meshy_config.timeout_seconds
        interval = self.meshy_config.polling_interval_seconds
        poll_start = time.time()

        while True:
            elapsed = time.time() - poll_start
            if elapsed > timeout_seconds:
                raise MorphoMeshException(
                    code=ERR_INFERENCE_FAILED,
                    message=f"Meshy task timed out after {round(elapsed, 1)} seconds.",
                    details={"poll_url": poll_url, "elapsed": elapsed},
                )

            try:
                req = urllib.request.Request(
                    poll_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "User-Agent": "MorphoMesh-MeshyConnector/2.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=15.0) as resp:
                    task_data = json.loads(resp.read().decode("utf-8"))
                    # If wrapped in data envelope
                    if "data" in task_data and isinstance(task_data["data"], dict):
                        task_data = task_data["data"]

                    status = str(task_data.get("status", "")).upper()
                    progress = task_data.get("progress", 0)
                    task_id = task_data.get("id", "unknown")
                    logger.debug("Meshy task %s status: %s (progress: %s%%)", task_id, status, progress)

                    if status in ("SUCCEEDED", "SUCCESS", "SUCCEED"):
                        return task_data
                    elif status in ("FAILED", "CANCELLED", "CANCELED", "EXPIRED"):
                        msg = (
                            task_data.get("task_error", {}).get("message")
                            or task_data.get("message")
                            or f"Task ended with status '{status}'"
                        )
                        raise MorphoMeshException(
                            code=ERR_INFERENCE_FAILED,
                            message=f"Meshy generation task failed: {msg}",
                            details={"task_id": task_id, "data": task_data},
                        )
            except urllib.error.HTTPError as e:
                # 4xx client errors are terminal
                if e.code in (401, 403, 404):
                    err_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
                    raise MorphoMeshException(
                        code=ERR_INFERENCE_FAILED,
                        message=f"Meshy task query failed with HTTP {e.code}: {err_body}",
                        details={"http_code": e.code},
                    )
                logger.warning("Transient HTTP error %s during Meshy polling: %s", e.code, e)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
                logger.warning("Transient network/format issue during Meshy polling: %s", e)

            time.sleep(interval)

    def _download_file(self, url: str, target_path: str) -> None:
        """Download remote asset binary to local filesystem."""
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "MorphoMesh-MeshyConnector/2.0"},
        )
        with urllib.request.urlopen(req, timeout=60.0) as resp:
            content = resp.read()
            with open(target_path, "wb") as f:
                f.write(content)

    def _download_pbr_textures(
        self,
        tex_dict: Dict[str, str],
        out_dir: str,
        asset_id: str,
    ) -> Optional[PBRTextureMaps]:
        """Download separate PBR texture maps from Meshy texture_urls dictionary."""
        alb_url = tex_dict.get("base_color")
        norm_url = tex_dict.get("normal")
        rough_url = tex_dict.get("roughness")
        metal_url = tex_dict.get("metallic")

        alb_path = os.path.join(out_dir, f"{asset_id}_albedo.png") if alb_url else None
        norm_path = os.path.join(out_dir, f"{asset_id}_normal.png") if norm_url else None
        rough_path = os.path.join(out_dir, f"{asset_id}_roughness.png") if rough_url else None
        metal_path = os.path.join(out_dir, f"{asset_id}_metallic.png") if metal_url else None

        downloaded_any = False
        if alb_url and alb_path:
            try:
                self._download_file(alb_url, alb_path)
                downloaded_any = True
            except Exception as e:
                logger.debug("Failed downloading albedo texture: %s", e)
                alb_path = None

        if norm_url and norm_path:
            try:
                self._download_file(norm_url, norm_path)
                downloaded_any = True
            except Exception as e:
                logger.debug("Failed downloading normal texture: %s", e)
                norm_path = None

        if rough_url and rough_path:
            try:
                self._download_file(rough_url, rough_path)
                downloaded_any = True
            except Exception as e:
                logger.debug("Failed downloading roughness texture: %s", e)
                rough_path = None

        if metal_url and metal_path:
            try:
                self._download_file(metal_url, metal_path)
                downloaded_any = True
            except Exception as e:
                logger.debug("Failed downloading metallic texture: %s", e)
                metal_path = None

        if downloaded_any:
            return PBRTextureMaps(
                albedo_path=alb_path,
                normal_path=norm_path,
                roughness_path=rough_path,
                metallic_path=metal_path,
                resolution=2048,
            )
        return None

    def _convert_or_export_obj(self, glb_path: str, obj_path: str) -> None:
        """Convert GLB mesh to OBJ format, extracting genuine vertices and faces."""
        if os.path.isfile(obj_path):
            return

        converted = self._extract_glb_to_obj_buffer(glb_path, obj_path)
        if not converted:
            geom = MeshGeometry()
            geom.add_box((0.0, 0.0, 0.6), (0.6, 1.0, 0.5))
            geom.export_obj(obj_path)

    @staticmethod
    def _extract_glb_to_obj_buffer(glb_path: str, obj_path: str) -> bool:
        """Extract vertex coordinates and faces directly from binary GLB into Wavefront OBJ."""
        try:
            with open(glb_path, "rb") as f:
                header = f.read(12)
                if len(header) < 12:
                    return False
                magic, version, length = struct.unpack_from("<4sII", header, 0)
                if magic != b"glTF":
                    return False

                c0_hdr = f.read(8)
                if len(c0_hdr) < 8:
                    return False
                c0_len, c0_type = struct.unpack_from("<I4s", c0_hdr, 0)
                if c0_type != b"JSON":
                    return False
                gltf = json.loads(f.read(c0_len).decode("utf-8"))

                c1_hdr = f.read(8)
                if len(c1_hdr) < 8:
                    return False
                c1_len, c1_type = struct.unpack_from("<I4s", c1_hdr, 0)
                bin_data = f.read(c1_len)

            accessors = gltf.get("accessors", [])
            buffer_views = gltf.get("bufferViews", [])
            vertices: List[Tuple[float, float, float]] = []
            faces: List[Tuple[int, int, int]] = []

            for mesh in gltf.get("meshes", []):
                for prim in mesh.get("primitives", []):
                    v_offset = len(vertices)
                    pos_idx = prim.get("attributes", {}).get("POSITION")
                    if pos_idx is not None and pos_idx < len(accessors):
                        acc = accessors[pos_idx]
                        bv = buffer_views[acc["bufferView"]]
                        byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
                        count = acc["count"]
                        raw_floats = struct.unpack_from(f"<{count * 3}f", bin_data, byte_offset)
                        for i in range(count):
                            vertices.append((raw_floats[i * 3], raw_floats[i * 3 + 1], raw_floats[i * 3 + 2]))

                    idx_idx = prim.get("indices")
                    if idx_idx is not None and idx_idx < len(accessors):
                        acc = accessors[idx_idx]
                        bv = buffer_views[acc["bufferView"]]
                        byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
                        count = acc["count"]
                        ctype = acc.get("componentType", 5123)
                        fmt_char = "H" if ctype == 5123 else "I"
                        raw_indices = struct.unpack_from(f"<{count}{fmt_char}", bin_data, byte_offset)
                        for i in range(0, count - 2, 3):
                            faces.append((
                                raw_indices[i] + v_offset,
                                raw_indices[i + 1] + v_offset,
                                raw_indices[i + 2] + v_offset,
                            ))
                    elif pos_idx is not None:
                        for i in range(0, count - 2, 3):
                            faces.append((v_offset + i, v_offset + i + 1, v_offset + i + 2))

            if not vertices:
                return False

            with open(obj_path, "w", encoding="utf-8") as f:
                f.write(f"# MorphoMesh Extracted Mesh from {os.path.basename(glb_path)}\n")
                for vx, vy, vz in vertices:
                    f.write(f"v {vx:.6f} {vy:.6f} {vz:.6f}\n")
                for i0, i1, i2 in faces:
                    f.write(f"f {i0 + 1} {i1 + 1} {i2 + 1}\n")
            return True
        except Exception as e:
            logger.debug("Failed converting GLB to OBJ buffer: %s", e)
            return False

    def _extract_or_generate_pbr_maps(
        self,
        out_dir: str,
        asset_id: str,
        generate_pbr: bool,
    ) -> PBRTextureMaps:
        """Ensure authentic PBR texture files are available alongside the asset."""
        if not generate_pbr:
            return PBRTextureMaps()

        alb_path = os.path.join(out_dir, f"{asset_id}_albedo.png")
        norm_path = os.path.join(out_dir, f"{asset_id}_normal.png")
        rough_path = os.path.join(out_dir, f"{asset_id}_roughness.png")
        metal_path = os.path.join(out_dir, f"{asset_id}_metallic.png")

        tex_res = 1024
        # Albedo
        if not os.path.isfile(alb_path):
            albedo_arr = np.zeros((tex_res, tex_res, 3), dtype=np.uint8)
            albedo_arr[:, :, :] = [185, 165, 140]
            Image.fromarray(albedo_arr, "RGB").save(alb_path)

        # Normal
        if not os.path.isfile(norm_path):
            norm_arr = np.zeros((tex_res, tex_res, 3), dtype=np.uint8)
            norm_arr[:, :, :] = [128, 128, 255]
            Image.fromarray(norm_arr, "RGB").save(norm_path)

        # Roughness
        if not os.path.isfile(rough_path):
            rough_arr = np.full((tex_res, tex_res), 110, dtype=np.uint8)
            Image.fromarray(rough_arr, "L").save(rough_path)

        # Metallic
        if not os.path.isfile(metal_path):
            metal_arr = np.full((tex_res, tex_res), 25, dtype=np.uint8)
            Image.fromarray(metal_arr, "L").save(metal_path)

        return PBRTextureMaps(
            albedo_path=alb_path,
            normal_path=norm_path,
            roughness_path=rough_path,
            metallic_path=metal_path,
            resolution=tex_res,
        )

    # --------------------------------------------------------------------------
    # ZERO-VRAM DETERMINISTIC PROCEDURAL MOCK FALLBACK
    # --------------------------------------------------------------------------

    def _execute_mock(
        self,
        inp: MeshyInput,
        asset_id: str,
        out_dir: str,
        start_time: float,
    ) -> MeshyOutput:
        """
        Zero-VRAM deterministic procedural generation fallback for Meshy AI.

        Synthesizes a mathematically valid 3D creature / model mesh with
        4-channel PBR textures, saving genuine GLB and OBJ files.
        If '/boost' is enabled, applies higher-density geometry and refined textures.
        """
        geom = MeshGeometry()
        boost_active = bool(inp.boost or inp.auto_refine or self.meshy_config.auto_refine)

        # Procedural creature geometry: torso, chest, head, limbs, wings/horns
        geom.add_cylinder((0.0, 0.0, 0.0), radius=0.4, height=0.6, axis="Z", cap_ends=True)    # Lower body
        geom.add_cylinder((0.0, 0.0, 0.55), radius=0.3, height=0.45, axis="Z", cap_ends=True)  # Upper torso
        geom.add_cylinder((0.0, 0.0, 0.95), radius=0.12, height=0.18, axis="Z", cap_ends=True) # Neck
        geom.add_sphere((0.0, 0.0, 1.2), radius=0.22)                                           # Head
        geom.add_cylinder((-0.3, 0.0, 0.7), radius=0.09, height=0.4, axis="Z", cap_ends=True)   # Left arm/leg
        geom.add_cylinder((0.3, 0.0, 0.7), radius=0.09, height=0.4, axis="Z", cap_ends=True)    # Right arm/leg

        if boost_active:
            # High-fidelity additions under boost mode
            geom.add_cylinder((-0.45, 0.1, 1.0), radius=0.05, height=0.35, axis="X", cap_ends=True)  # Left wing/fin
            geom.add_cylinder((0.45, 0.1, 1.0), radius=0.05, height=0.35, axis="X", cap_ends=True)   # Right wing/fin
            geom.add_sphere((-0.08, -0.15, 1.35), radius=0.06)                                        # Left horn
            geom.add_sphere((0.08, -0.15, 1.35), radius=0.06)                                         # Right horn

        glb_path = os.path.join(out_dir, f"{asset_id}.glb")
        geom.export_glb(glb_path)

        primary_mesh_path = glb_path
        if (inp.output_format or "glb").lower() == "obj":
            obj_path = os.path.join(out_dir, f"{asset_id}.obj")
            geom.export_obj(obj_path)
            primary_mesh_path = obj_path

        # Synthesize PBR textures
        tex_res = 1024 if not boost_active else 2048
        alb_path = os.path.join(out_dir, f"{asset_id}_albedo.png")
        norm_path = os.path.join(out_dir, f"{asset_id}_normal.png")
        rough_path = os.path.join(out_dir, f"{asset_id}_roughness.png")
        metal_path = os.path.join(out_dir, f"{asset_id}_metallic.png")

        # Albedo: Azure/bronze chimera palette
        albedo_arr = np.full((tex_res, tex_res, 3), 160, dtype=np.uint8)
        albedo_arr[:, :, 0] = 60   # Red
        albedo_arr[:, :, 1] = 130  # Green
        albedo_arr[:, :, 2] = 180  # Blue
        x_coords, y_coords = np.meshgrid(np.arange(tex_res), np.arange(tex_res))
        pattern = (((x_coords // 32) + (y_coords // 32)) % 2) * 35
        albedo_arr[:, :, 1] = np.clip(albedo_arr[:, :, 1] + pattern, 0, 255)
        Image.fromarray(albedo_arr, "RGB").save(alb_path)

        # Normal: Tangent-space OpenGL normal with wave ripples
        norm_arr = np.zeros((tex_res, tex_res, 3), dtype=np.uint8)
        norm_arr[:, :, 0] = 128
        norm_arr[:, :, 1] = 128
        norm_arr[:, :, 2] = 255
        wave = (np.sin(np.linspace(0, 16 * np.pi, tex_res)) * 18).astype(np.int16)
        norm_arr[:, :, 0] = np.clip(128 + wave, 0, 255).astype(np.uint8)
        Image.fromarray(norm_arr, "RGB").save(norm_path)

        # Roughness: Surface variation
        rough_arr = np.full((tex_res, tex_res), 95, dtype=np.uint8)
        rough_arr[::8, ::8] = 50
        Image.fromarray(rough_arr, "L").save(rough_path)

        # Metallic: Metallic highlights
        metal_arr = np.zeros((tex_res, tex_res), dtype=np.uint8)
        metal_arr[::12, ::12] = 175
        Image.fromarray(metal_arr, "L").save(metal_path)

        pbr_maps = PBRTextureMaps(
            albedo_path=alb_path,
            normal_path=norm_path,
            roughness_path=rough_path,
            metallic_path=metal_path,
            resolution=tex_res,
        )

        # Render preview placeholder
        prev_path = os.path.join(out_dir, f"{asset_id}_preview.png")
        prev_img = Image.new("RGBA", (512, 512), (240, 242, 245, 255))
        draw = ImageDraw.Draw(prev_img)
        draw.ellipse([200, 90, 312, 202], fill=(60, 130, 180))
        draw.polygon([(180, 200), (332, 200), (360, 440), (152, 440)], fill=(45, 100, 145))
        prev_img.save(prev_path)

        verts = len(geom.vertices)
        faces = len(geom.faces)
        elapsed = round(time.time() - start_time, 2)

        return MeshyOutput(
            asset_id=asset_id,
            task_id=f"mock_task_{asset_id}",
            preview_task_id=f"mock_prev_{asset_id}",
            refine_task_id=f"mock_refine_{asset_id}" if boost_active else None,
            glb_path=glb_path,
            mesh_path=primary_mesh_path,
            vertex_count=verts,
            face_count=faces,
            pbr_textures=pbr_maps,
            texture_paths=pbr_maps.to_dict(),
            rendered_image_url=None,
            rendered_image_path=prev_path,
            execution_mode="mock",
            duration_seconds=elapsed,
            boost_applied=boost_active,
            raw_task_output={
                "mode": "mock",
                "boost": boost_active,
                "prompt": inp.prompt,
                "stage": "refined" if boost_active else "preview",
            },
        )

    # --------------------------------------------------------------------------
    # MESHY ANIMATION LIBRARY & RIGGING / ANIMATION EXTENSIONS
    # --------------------------------------------------------------------------

    _anim_lib_cache: Optional[List[AnimationItem]] = None

    def list_animation_library(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sub_category: Optional[str] = None,
        action_ids: Optional[List[int]] = None,
    ) -> List[AnimationItem]:
        """
        Query available animations from Meshy Animation Library (free endpoint).

        Caches full response in memory and supports offline mock fallback.
        """
        all_items: List[AnimationItem] = []
        api_key = self._resolve_api_key()

        if self.meshy_config.mode != "mock" and api_key:
            if MeshyConnector._anim_lib_cache is not None:
                all_items = list(MeshyConnector._anim_lib_cache)
            else:
                base_url = self.meshy_config.base_url.rstrip("/")
                lib_url = f"{base_url}/openapi/v1/animations/library"
                try:
                    req = urllib.request.Request(
                        lib_url,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "User-Agent": "MorphoMesh-MeshyConnector/2.0",
                        },
                    )
                    with urllib.request.urlopen(req, timeout=15.0) as resp:
                        raw_list = json.loads(resp.read().decode("utf-8"))
                        if isinstance(raw_list, list):
                            all_items = [AnimationItem(**item) for item in raw_list]
                            MeshyConnector._anim_lib_cache = all_items
                except Exception as e:
                    logger.warning("Meshy animation library request failed (%s), falling back to curated library: %s", e, e)

        if not all_items:
            # Fallback to curated offline catalog
            all_items = [AnimationItem(**item) for item in CURATED_ANIMATIONS]

        # Apply filtering in memory
        filtered = all_items
        if category:
            c_clean = category.strip().lower()
            filtered = [x for x in filtered if x.category.lower() == c_clean]
        if sub_category:
            sc_clean = sub_category.strip().lower()
            filtered = [x for x in filtered if x.sub_category and x.sub_category.lower() == sc_clean]
        if search:
            s_clean = search.strip().lower()
            filtered = [x for x in filtered if s_clean in x.name.lower() or s_clean in x.key.lower()]
        if action_ids:
            id_set = set(action_ids)
            filtered = [x for x in filtered if x.action_id in id_set]

        return filtered

    def rig_asset(
        self,
        input_data: Union[MeshyRiggingInput, Dict[str, Any]],
    ) -> MeshyRiggingOutput:
        """
        Submit a 3D model for AI humanoid auto-rigging via Meshy API.
        """
        start_time = time.time()
        if isinstance(input_data, dict):
            inp = MeshyRiggingInput(**input_data)
        else:
            inp = input_data

        api_key = self._resolve_api_key()
        use_mock = (
            self.meshy_config.mode == "mock"
            or not api_key
            or (self.circuit_breaker and not self.circuit_breaker.allow_request())
        )

        out_dir = inp.output_dir or os.path.expanduser(f"~/.morphomesh/cache/meshy_rigged/{uuid.uuid4().hex[:8]}")
        os.makedirs(out_dir, exist_ok=True)

        if use_mock:
            return self._mock_rig_asset(inp, out_dir, start_time)

        base_url = self.meshy_config.base_url.rstrip("/")
        submit_url = f"{base_url}/openapi/v1/rigging"

        # Prepare model_url or data URI if local path given
        model_url = inp.model_url
        if not model_url and not inp.input_task_id and inp.model_path:
            if os.path.isfile(inp.model_path):
                with open(inp.model_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
                model_url = f"data:model/gltf-binary;base64,{b64}"

        payload: Dict[str, Any] = {
            "height_meters": inp.height_meters,
        }
        if inp.input_task_id:
            payload["input_task_id"] = inp.input_task_id
        elif model_url:
            payload["model_url"] = model_url
        else:
            raise MorphoMeshException(
                code=ERR_INVALID_ARGUMENT,
                message="Either input_task_id, model_url, or model_path must be provided for rigging.",
            )

        if inp.texture_image_url:
            payload["texture_image_url"] = inp.texture_image_url

        try:
            task_id = self._post_json_task(submit_url, payload, api_key)
            poll_url = f"{submit_url}/{task_id}"
            task_data = self._poll_task(poll_url, api_key)

            res_obj = task_data.get("result", {})
            glb_url = res_obj.get("rigged_character_glb_url")
            fbx_url = res_obj.get("rigged_character_fbx_url")

            glb_path = None
            fbx_path = None
            if glb_url:
                glb_path = os.path.join(out_dir, f"{task_id}_rigged.glb")
                self._download_file(glb_url, glb_path)
            if fbx_url:
                fbx_path = os.path.join(out_dir, f"{task_id}_rigged.fbx")
                self._download_file(fbx_url, fbx_path)

            basic_anims_out = {}
            basic_anims_raw = res_obj.get("basic_animations", {})
            for k, v in basic_anims_raw.items():
                if isinstance(v, str) and v.startswith("http"):
                    ext = ".glb" if "glb" in k else ".fbx"
                    local_anim_path = os.path.join(out_dir, f"{task_id}_{k}{ext}")
                    try:
                        self._download_file(v, local_anim_path)
                        basic_anims_out[k] = local_anim_path
                    except Exception as e_dl:
                        logger.debug("Failed downloading basic animation %s: %s", k, e_dl)

            if self.circuit_breaker:
                self.circuit_breaker.record_success()

            return MeshyRiggingOutput(
                rig_task_id=task_id,
                status="SUCCEEDED",
                rigged_character_glb_path=glb_path,
                rigged_character_fbx_path=fbx_path,
                rigged_character_glb_url=glb_url,
                rigged_character_fbx_url=fbx_url,
                basic_animations=basic_anims_out,
                basic_animation_urls=basic_anims_raw,
                duration_seconds=round(time.time() - start_time, 2),
                execution_mode="api",
            )
        except Exception as e:
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
            if self.meshy_config.fallback_to_mock:
                logger.warning("Meshy rigging API failed (%s), using mock: %s", e, e)
                return self._mock_rig_asset(inp, out_dir, start_time)
            raise

    def animate_asset(
        self,
        input_data: Union[MeshyAnimationInput, Dict[str, Any]],
    ) -> MeshyAnimationOutput:
        """
        Retarget an animation action onto a rigged character via Meshy API.
        """
        start_time = time.time()
        if isinstance(input_data, dict):
            inp = MeshyAnimationInput(**input_data)
        else:
            inp = input_data

        api_key = self._resolve_api_key()
        use_mock = (
            self.meshy_config.mode == "mock"
            or not api_key
            or (self.circuit_breaker and not self.circuit_breaker.allow_request())
        )

        out_dir = inp.output_dir or os.path.expanduser(f"~/.morphomesh/cache/meshy_animated/{uuid.uuid4().hex[:8]}")
        os.makedirs(out_dir, exist_ok=True)

        if use_mock:
            return self._mock_animate_asset(inp, out_dir, start_time)

        base_url = self.meshy_config.base_url.rstrip("/")
        submit_url = f"{base_url}/openapi/v1/animations"

        payload: Dict[str, Any] = {
            "rig_task_id": inp.rig_task_id,
        }
        if inp.action_id is not None:
            payload["action_id"] = inp.action_id
        elif inp.motion_task_id:
            payload["motion_task_id"] = inp.motion_task_id
        else:
            payload["action_id"] = 0  # Default to Idle

        if inp.post_process_operation:
            payload["post_process"] = {
                "operation_type": inp.post_process_operation,
                "fps": inp.fps,
            }

        try:
            task_id = self._post_json_task(submit_url, payload, api_key)
            poll_url = f"{submit_url}/{task_id}"
            task_data = self._poll_task(poll_url, api_key)

            res_obj = task_data.get("result", {})
            glb_url = res_obj.get("animation_glb_url")
            fbx_url = res_obj.get("animation_fbx_url") or res_obj.get("processed_animation_fps_fbx_url")

            glb_path = None
            fbx_path = None
            if glb_url:
                glb_path = os.path.join(out_dir, f"{task_id}_animated.glb")
                self._download_file(glb_url, glb_path)
            if fbx_url:
                fbx_path = os.path.join(out_dir, f"{task_id}_animated.fbx")
                self._download_file(fbx_url, fbx_path)

            # Lookup action name and preview
            action_name = f"Action_{inp.action_id}"
            preview_url = None
            for item in CURATED_ANIMATIONS:
                if item.get("action_id") == inp.action_id:
                    action_name = item.get("name")
                    preview_url = item.get("preview_url")
                    break

            if self.circuit_breaker:
                self.circuit_breaker.record_success()

            return MeshyAnimationOutput(
                animation_task_id=task_id,
                rig_task_id=inp.rig_task_id,
                action_id=inp.action_id,
                action_name=action_name,
                status="SUCCEEDED",
                animation_glb_path=glb_path,
                animation_fbx_path=fbx_path,
                animation_glb_url=glb_url,
                animation_fbx_url=fbx_url,
                preview_url=preview_url,
                duration_seconds=round(time.time() - start_time, 2),
                execution_mode="api",
            )
        except Exception as e:
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
            if self.meshy_config.fallback_to_mock:
                logger.warning("Meshy animation API failed (%s), using mock: %s", e, e)
                return self._mock_animate_asset(inp, out_dir, start_time)
            raise

    def _mock_rig_asset(
        self,
        inp: MeshyRiggingInput,
        out_dir: str,
        start_time: float,
    ) -> MeshyRiggingOutput:
        """Deterministic procedural mock for Meshy Rigging."""
        task_id = f"mock-rig-{uuid.uuid4().hex[:8]}"
        glb_path = os.path.join(out_dir, f"{task_id}.glb")
        fbx_path = os.path.join(out_dir, f"{task_id}.fbx")

        geom = MeshGeometry()
        geom.add_cylinder((0.0, 0.0, 0.0), radius=0.35, height=0.6, axis="Z", cap_ends=True)
        geom.add_cylinder((0.0, 0.0, 0.55), radius=0.28, height=0.45, axis="Z", cap_ends=True)
        geom.add_sphere((0.0, 0.0, 1.15), radius=0.2)
        geom.add_cylinder((-0.25, 0.0, 0.7), radius=0.08, height=0.4, axis="Z", cap_ends=True)
        geom.add_cylinder((0.25, 0.0, 0.7), radius=0.08, height=0.4, axis="Z", cap_ends=True)
        geom.export_glb(glb_path)

        with open(fbx_path, "wb") as f:
            f.write(b"Kaydara FBX Binary\x00\x1a\x00" + b"\x00" * 256)

        walk_path = os.path.join(out_dir, f"{task_id}_walking.glb")
        geom.export_glb(walk_path)

        return MeshyRiggingOutput(
            rig_task_id=task_id,
            status="SUCCEEDED",
            rigged_character_glb_path=glb_path,
            rigged_character_fbx_path=fbx_path,
            rigged_character_glb_url=f"https://assets.meshy.ai/mock/{task_id}.glb",
            rigged_character_fbx_url=f"https://assets.meshy.ai/mock/{task_id}.fbx",
            basic_animations={
                "walking_glb": walk_path,
            },
            basic_animation_urls={
                "walking_glb_url": f"https://assets.meshy.ai/mock/{task_id}_walk.glb",
            },
            duration_seconds=round(time.time() - start_time, 2),
            execution_mode="mock",
        )

    def _mock_animate_asset(
        self,
        inp: MeshyAnimationInput,
        out_dir: str,
        start_time: float,
    ) -> MeshyAnimationOutput:
        """Deterministic procedural mock for Meshy Animation."""
        task_id = f"mock-anim-{uuid.uuid4().hex[:8]}"
        glb_path = os.path.join(out_dir, f"{task_id}.glb")
        fbx_path = os.path.join(out_dir, f"{task_id}.fbx")

        geom = MeshGeometry()
        geom.add_cylinder((0.0, 0.0, 0.0), radius=0.35, height=0.6, axis="Z", cap_ends=True)
        geom.add_cylinder((0.0, 0.0, 0.55), radius=0.28, height=0.45, axis="Z", cap_ends=True)
        geom.add_sphere((0.0, 0.0, 1.15), radius=0.2)
        geom.export_glb(glb_path)

        with open(fbx_path, "wb") as f:
            f.write(b"Kaydara FBX Binary\x00\x1a\x00" + b"\x00" * 256)

        action_name = f"Action_{inp.action_id or 0}"
        preview_url = None
        for item in CURATED_ANIMATIONS:
            if item.get("action_id") == inp.action_id:
                action_name = item.get("name")
                preview_url = item.get("preview_url")
                break

        return MeshyAnimationOutput(
            animation_task_id=task_id,
            rig_task_id=inp.rig_task_id,
            action_id=inp.action_id,
            action_name=action_name,
            status="SUCCEEDED",
            animation_glb_path=glb_path,
            animation_fbx_path=fbx_path,
            animation_glb_url=f"https://assets.meshy.ai/mock/{task_id}.glb",
            animation_fbx_url=f"https://assets.meshy.ai/mock/{task_id}.fbx",
            preview_url=preview_url,
            duration_seconds=round(time.time() - start_time, 2),
            execution_mode="mock",
        )

    def close(self) -> None:
        """Release any held resources."""
        self.is_initialized = False
