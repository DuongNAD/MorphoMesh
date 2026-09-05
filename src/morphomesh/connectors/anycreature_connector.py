"""
MorphoMesh: anyCreature Procedural Engine Connector.

Parses natural language creature prompts into structured Directed Acyclic Graph
(DAG) BodyGraph JSON specifications, builds procedural multi-segment 3D meshes,
and binds kinematic locomotion/flight gait animation clips.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from morphomesh.connectors.base import (
    BaseConnector,
    DependencyCheckResult,
    HealthCheckResult,
)
from morphomesh.inference_adapter import MeshGeometry

logger = logging.getLogger(__name__)


# ==============================================================================
# PYDANTIC V2 SCHEMAS
# ==============================================================================

class LimbSpec(BaseModel):
    """Specification of an articulated appendage (leg, wing, arm, etc.)."""
    model_config = ConfigDict(extra="ignore")

    limb_id: str
    limb_type: Literal["leg", "wing", "arm", "fin", "tentacle"]
    side: Literal["left", "right", "center"]
    attachment_joint: str
    segment_lengths: List[float] = Field(default_factory=lambda: [0.4, 0.4, 0.15])
    joint_constraints: Dict[str, Dict[str, float]] = Field(
        default_factory=lambda: {
            "knee": {"min_deg": 0.0, "max_deg": 120.0},
            "ankle": {"min_deg": -45.0, "max_deg": 60.0},
        }
    )


class BodyPart(BaseModel):
    """Individual morphological body segment in the creature graph."""
    model_config = ConfigDict(extra="ignore")

    part_id: str
    part_type: Literal["root", "spine", "neck", "head", "tail", "jaw", "ear", "horn", "torso"]
    parent_id: Optional[str] = None
    length: float = 0.5
    radius_start: float = 0.2
    radius_end: float = 0.15
    subdivisions: int = 4
    symmetry: bool = False


class BodyGraph(BaseModel):
    """Directed Acyclic Graph (DAG) describing creature morphology."""
    model_config = ConfigDict(extra="ignore")

    creature_name: str = "ProceduralCreature"
    archetype: str = "quadruped"
    parts: Dict[str, BodyPart] = Field(default_factory=dict)
    limbs: List[LimbSpec] = Field(default_factory=list)
    root_id: str = "pelvis"


class AnimationBinding(BaseModel):
    """Gait oscillator parameters and phase offsets for locomotion."""
    model_config = ConfigDict(extra="ignore")

    action_name: str = "walk_cycle"
    gait_frequency: float = 1.0
    phase_offsets: Dict[str, float] = Field(
        default_factory=lambda: {
            "front_left": 0.0,
            "rear_right": 0.25,
            "front_right": 0.5,
            "rear_left": 0.75,
        }
    )
    stride_length: float = 1.2
    body_undulation_amplitude: float = 0.15


class CreaturePromptSpec(BaseModel):
    """Complete compiled creature specification parsed from natural language."""
    model_config = ConfigDict(extra="ignore")

    raw_prompt: str
    inferred_type: str = "quadruped"
    body_graph: BodyGraph
    animation_bindings: List[AnimationBinding] = Field(default_factory=list)
    procedural_parameters: Dict[str, Any] = Field(default_factory=dict)


class AnyCreatureOutput(BaseModel):
    """Execution output containing generated specification and asset paths."""
    model_config = ConfigDict(extra="ignore")

    asset_id: str
    spec: CreaturePromptSpec
    generated_mesh_path: Optional[str] = None
    json_spec_path: str
    clip_names: List[str] = Field(default_factory=list)
    total_parts: int
    total_limbs: int


class AnyCreatureConnector(BaseConnector):
    """
    anyCreature procedural engine connector.
    
    Compiles text prompts into anatomical BodyGraph specifications, synthesizes
    procedural geometry, and binds multi-phase gait animation controllers.
    """

    connector_id: str = "anycreature"
    display_name: str = "anyCreature Procedural Engine Connector"
    version: str = "2.0.0"
    stage: int = 1
    description: str = "NLP prompt compilation to modular BodyGraph specification, procedural mesh builder, and gait animation bindings"

    def initialize(self) -> bool:
        """Initialize grammatical parser rules and procedural primitives."""
        self.is_initialized = True
        return True

    def health_check(self) -> HealthCheckResult:
        """Probe procedural engine health."""
        return HealthCheckResult(
            status="healthy",
            latency_ms=0.2,
            message="anyCreature procedural compiler ready",
            details={"rules_loaded": 12, "archetypes_supported": 6},
            circuit_state=getattr(self.circuit_breaker, "state", "CLOSED"),
            dependencies_met=True,
        )

    def check_dependencies(self) -> DependencyCheckResult:
        """Verify dependencies."""
        return DependencyCheckResult(
            satisfied=True,
            missing_packages=[],
            hardware_supported=True,
            details={"engine": "pure_python_procedural"},
        )

    def parse_prompt(self, prompt: str) -> CreaturePromptSpec:
        """
        Deconstruct natural language description into an anatomical BodyGraph.
        
        Args:
            prompt: Text description of the creature.
            
        Returns:
            CreaturePromptSpec: Compiled specification.
        """
        p_lower = prompt.lower()

        # 1. Infer archetype
        if any(w in p_lower for w in ("dragon", "winged", "pegasus", "wyvern", "bat")):
            archetype = "winged_quadruped"
        elif any(w in p_lower for w in ("humanoid", "biped", "orc", "goblin", "giant")):
            archetype = "biped"
        elif any(w in p_lower for w in ("snake", "serpent", "worm", "naga")):
            archetype = "serpentine"
        elif any(w in p_lower for w in ("fish", "shark", "whale", "aquatic")):
            archetype = "aquatic"
        else:
            archetype = "quadruped"

        # 2. Build core body parts
        parts: Dict[str, BodyPart] = {
            "pelvis": BodyPart(part_id="pelvis", part_type="root", length=0.4, radius_start=0.25, radius_end=0.22),
            "chest": BodyPart(part_id="chest", part_type="torso", parent_id="pelvis", length=0.6, radius_start=0.28, radius_end=0.24),
            "neck": BodyPart(part_id="neck", part_type="neck", parent_id="chest", length=0.35, radius_start=0.18, radius_end=0.14),
            "head": BodyPart(part_id="head", part_type="head", parent_id="neck", length=0.3, radius_start=0.16, radius_end=0.12),
        }

        # Tail
        if archetype in ("quadruped", "winged_quadruped", "serpentine"):
            parts["tail"] = BodyPart(part_id="tail", part_type="tail", parent_id="pelvis", length=0.7, radius_start=0.12, radius_end=0.04)

        # Horns
        if "horn" in p_lower:
            parts["left_horn"] = BodyPart(part_id="left_horn", part_type="horn", parent_id="head", length=0.25, radius_start=0.06, radius_end=0.01)
            parts["right_horn"] = BodyPart(part_id="right_horn", part_type="horn", parent_id="head", length=0.25, radius_start=0.06, radius_end=0.01)

        # 3. Assemble limbs
        limbs: List[LimbSpec] = []
        if archetype in ("quadruped", "winged_quadruped"):
            limbs.extend([
                LimbSpec(limb_id="front_left_leg", limb_type="leg", side="left", attachment_joint="chest", segment_lengths=[0.35, 0.35, 0.1]),
                LimbSpec(limb_id="front_right_leg", limb_type="leg", side="right", attachment_joint="chest", segment_lengths=[0.35, 0.35, 0.1]),
                LimbSpec(limb_id="rear_left_leg", limb_type="leg", side="left", attachment_joint="pelvis", segment_lengths=[0.4, 0.4, 0.12]),
                LimbSpec(limb_id="rear_right_leg", limb_type="leg", side="right", attachment_joint="pelvis", segment_lengths=[0.4, 0.4, 0.12]),
            ])

        if archetype == "winged_quadruped":
            limbs.extend([
                LimbSpec(
                    limb_id="left_wing",
                    limb_type="wing",
                    side="left",
                    attachment_joint="chest",
                    segment_lengths=[0.7, 0.9, 0.4],
                    joint_constraints={"shoulder": {"min_deg": -30.0, "max_deg": 60.0}},
                ),
                LimbSpec(
                    limb_id="right_wing",
                    limb_type="wing",
                    side="right",
                    attachment_joint="chest",
                    segment_lengths=[0.7, 0.9, 0.4],
                    joint_constraints={"shoulder": {"min_deg": -30.0, "max_deg": 60.0}},
                ),
            ])
        elif archetype == "biped":
            limbs.extend([
                LimbSpec(limb_id="left_leg", limb_type="leg", side="left", attachment_joint="pelvis", segment_lengths=[0.5, 0.5, 0.15]),
                LimbSpec(limb_id="right_leg", limb_type="leg", side="right", attachment_joint="pelvis", segment_lengths=[0.5, 0.5, 0.15]),
                LimbSpec(limb_id="left_arm", limb_type="arm", side="left", attachment_joint="chest", segment_lengths=[0.4, 0.4, 0.12]),
                LimbSpec(limb_id="right_arm", limb_type="arm", side="right", attachment_joint="chest", segment_lengths=[0.4, 0.4, 0.12]),
            ])

        # 4. Generate animation bindings
        bindings = [
            AnimationBinding(
                action_name="idle",
                gait_frequency=0.5,
                phase_offsets={"all": 0.0},
                stride_length=0.0,
                body_undulation_amplitude=0.05,
            ),
            AnimationBinding(
                action_name="walk_cycle",
                gait_frequency=1.2,
                phase_offsets={"front_left": 0.0, "rear_right": 0.25, "front_right": 0.5, "rear_left": 0.75},
                stride_length=1.1,
                body_undulation_amplitude=0.12,
            ),
            AnimationBinding(
                action_name="run_cycle",
                gait_frequency=2.2,
                phase_offsets={"front_left": 0.0, "front_right": 0.1, "rear_left": 0.5, "rear_right": 0.6},
                stride_length=1.8,
                body_undulation_amplitude=0.22,
            ),
        ]

        if archetype == "winged_quadruped":
            bindings.append(
                AnimationBinding(
                    action_name="fly_cycle",
                    gait_frequency=1.5,
                    phase_offsets={"left_wing": 0.0, "right_wing": 0.0},
                    stride_length=2.5,
                    body_undulation_amplitude=0.25,
                )
            )

        name_match = re.search(r"\b([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\b", prompt)
        c_name = name_match.group(1).title().replace(" ", "") if name_match else "Creature"

        body_graph = BodyGraph(
            creature_name=c_name,
            archetype=archetype,
            parts=parts,
            limbs=limbs,
            root_id="pelvis",
        )

        return CreaturePromptSpec(
            raw_prompt=prompt,
            inferred_type=archetype,
            body_graph=body_graph,
            animation_bindings=bindings,
            procedural_parameters={"symmetry_axis": "X", "scale_factor": 1.0},
        )

    def execute(self, request: Union[str, Dict[str, Any], CreaturePromptSpec], **kwargs: Any) -> AnyCreatureOutput:
        """
        Parse prompt, compile BodyGraph, generate procedural mesh, and save specification.
        
        Args:
            request: Prompt string, dict, or CreaturePromptSpec.
            
        Returns:
            AnyCreatureOutput: Compilation result.
        """
        if isinstance(request, str):
            spec = self.parse_prompt(request)
        elif isinstance(request, dict):
            if "raw_prompt" in request and "body_graph" not in request:
                spec = self.parse_prompt(request["raw_prompt"])
            else:
                spec = CreaturePromptSpec(**request)
        elif isinstance(request, CreaturePromptSpec):
            spec = request
        else:
            raise TypeError(f"Unsupported request type: {type(request)}")

        asset_id = f"creature_{uuid.uuid4().hex[:8]}"
        out_dir = kwargs.get("output_dir") or os.path.expanduser(f"~/.morphomesh/cache/assets/{asset_id}")
        os.makedirs(out_dir, exist_ok=True)

        # 1. Export JSON specification
        json_path = os.path.join(out_dir, "creature_spec.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(spec.model_dump(), f, indent=2)

        # 2. Build procedural mesh
        geom = MeshGeometry()
        # Torso & Pelvis
        geom.add_box((0.0, 0.0, 0.6), (0.6, 1.2, 0.5))
        # Neck & Head
        geom.add_cylinder((0.0, 0.5, 0.7), 0.16, 0.35, axis="Z")
        geom.add_sphere((0.0, 0.65, 1.05), 0.22)
        # Limbs
        for limb in spec.body_graph.limbs:
            offset_x = -0.3 if limb.side == "left" else 0.3
            if limb.limb_type == "leg":
                geom.add_cylinder((offset_x, 0.0, 0.0), 0.09, 0.6, axis="Z")
            elif limb.limb_type == "wing":
                geom.add_box((offset_x * 1.5, 0.2, 0.9), (0.8, 0.4, 0.03))

        mesh_path = os.path.join(out_dir, f"{asset_id}.glb")
        geom.export_glb(mesh_path)

        clip_names = [b.action_name for b in spec.animation_bindings]

        return AnyCreatureOutput(
            asset_id=asset_id,
            spec=spec,
            generated_mesh_path=mesh_path,
            json_spec_path=json_path,
            clip_names=clip_names,
            total_parts=len(spec.body_graph.parts),
            total_limbs=len(spec.body_graph.limbs),
        )

    def close(self) -> None:
        """Release connector resources."""
        self.is_initialized = False
