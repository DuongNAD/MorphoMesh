# Analysis & Modularization Blueprint: Models Subsystem (`src/morphomesh/models/`)

**Author:** Explorer M1-1  
**Target Milestone:** Milestone 1 (Models Subsystem Architecture & Decomposition Plan)  
**Target Package:** `src/morphomesh/models/`  
**Facade File:** `src/morphomesh/models.py`  
**Date:** 2026-09-09  

---

## 1. Executive Architectural Summary

The monolithic source file `src/morphomesh/models.py` (63.8 KB, 1,233 lines) currently houses all Pydantic v2 schemas, enumerations, error constants, and domain validation logic for the entire MorphoMesh ecosystem. This includes seven distinct functional domains:
1. Universal error codes matrix and authoritative exceptions.
2. Global pipeline enumerations (creatures, viewpoints, topology, rigging, rendering).
3. Core spatial and scene primitives (`BoundingBox`, `SceneObjectInfo`, `BoundingBox3D`).
4. Creature pipeline request/response schemas (FastMCP Tools 1–7).
5. Industrial Digital Human pipeline request/response schemas (FastMCP Tools 8–12).
6. Multi-angle inspector camera and viewport grab schemas (Milestone 2).
7. Closed-loop visual quality critique and defect diagnostic schemas (Milestone 3).
8. Animation preset query and asset retargeting schemas.

### Decomposition Mandate
In accordance with **MM-R1-MODULAR-001** and **PROJECT.md**, `models.py` must be decomposed into a modular package `src/morphomesh/models/` comprising 8 cohesive submodules plus `__init__.py`, accompanied by a backward-compatibility facade at `src/morphomesh/models.py`.

### Architectural Invariance Guarantees
- **100% Symbol Preservation:** All 62 classes (17 enums, 1 exception, 44 Pydantic models), 32 error constants, 5 output aliases, 1 preset alias, and 1 viewpoint lookup set are preserved with exact signatures and field types.
- **Zero Circular Dependencies:** The dependency graph across all submodules forms a strict Directed Acyclic Graph (DAG) with maximum topological depth 3.
- **Dual-Import Parity:** Callers importing via `from morphomesh.models import X` or `from morphomesh.models.enums import X` or legacy `from models import X` resolve seamlessly without regression.

---

## 2. Exhaustive Symbol Inventory & Taxonomy

### 2.1 Complete Error Constants Matrix (32 Constants)

Defined at lines 21–52 in `src/morphomesh/models.py`:

| Constant Name | Value | Category | Domain Scope |
|---|---|---|---|
| `ERR_PARSE_ERROR` | `-32700` | Standard JSON-RPC | IPC framing & serialization failure |
| `ERR_INVALID_REQUEST` | `-32600` | Standard JSON-RPC | Malformed payload structure |
| `ERR_METHOD_NOT_FOUND` | `-32601` | Standard JSON-RPC | Unregistered tool or RPC method |
| `ERR_INVALID_ARGUMENT` | `-32602` | Standard JSON-RPC | Parameter constraint or type violation |
| `ERR_IMAGE_NOT_FOUND` | `-32001` | MorphoMesh Pipeline | Missing concept or input image file |
| `ERR_BACKEND_UNAVAILABLE` | `-32002` | Inference Subsystem | AI backend endpoint unreachable |
| `ERR_VRAM_EXHAUSTED` | `-32003` | Hardware Resource | GPU out-of-memory condition |
| `ERR_REMESH_FAILED` | `-32004` | Geometry Subsystem | Quadriflow / InstantMeshes failure |
| `ERR_SKINNING_HEAT_FAILURE` | `-32005` | Rigging Subsystem | Voxel heat diffuse skin binding failure |
| `ERR_SCRIPT_SECURITY_VIOLATION` | `-32006` | Security Subsystem | AST validation check failed on bpy script |
| `ERR_TIMEOUT` | `-32007` | Runtime Execution | Operation exceeded time budget |
| `ERR_BLENDER_UNAVAILABLE` | `-32008` | Bridge Subsystem | Blender socket/headless process down |
| `ERR_NO_CAMERA` | `-32009` | Scene Subsystem | Viewport/render camera missing in scene |
| `ERR_ANATOMY_DETECTION_FAILED` | `-32010` | Anatomy Subsystem | Bony landmarks or joint detection failure |
| `ERR_INPUT_MESH_NOT_FOUND` | `-32011` | File I/O | Input 3D file (.glb/.obj/.fbx) not on disk |
| `ERR_INVALID_POLY_COUNT` | `-32012` | Geometry Subsystem | Target poly budget out of acceptable bounds |
| `ERR_NON_MANIFOLD_MESH` | `-32013` | Geometry Subsystem | Non-manifold edges, self-intersections |
| `ERR_SCENE_NOT_FOUND` | `-32014` | Blender Bridge | Specified scene collection not found |
| `ERR_RENDER_FAILED` | `-32015` | Rendering Subsystem | Cycles / EEVEE render exception |
| `ERR_OUTPUT_WRITE_FAILED` | `-32016` | File I/O | Unable to write output asset to target path |
| `ERR_SCRIPT_SYNTAX_ERROR` | `-32017` | Python Runtime | Syntax error in dispatched bpy script |
| `ERR_SCRIPT_RUNTIME_EXCEPTION` | `-32018` | Python Runtime | Unhandled exception during bpy execution |
| `ERR_INFERENCE_FAILED` | `-32019` | Inference Subsystem | AI generation returned failure status |
| `ERR_DISK_WRITE_FAILED` | `-32020` | File I/O | Disk full or filesystem permission denied |
| `ERR_SCRIPT_EXECUTION_TIMEOUT` | `-32007` | Runtime Execution | Alias for timeout during bpy execution |
| `ERR_BLENDER_EXECUTION_FAILED` | `-32021` | Blender Bridge | General failure in Blender worker execution |
| `ERR_HUMAN_GENERATION_FAILED` | `-32030` | Human Pipeline | MakeHuman mold loader/morphology failure |
| `ERR_HUMAN_RIGGING_FAILED` | `-32031` | Human Rigging | 163 DEF Rigify metarig generation failure |
| `ERR_HUMAN_MATERIALS_FAILED` | `-32032` | Human Materials | SSS or eye shader tree generation failure |
| `ERR_HUMAN_GROOMING_FAILED` | `-32033` | Human Grooming | Hair curves / Geometry Nodes failure |
| `ERR_HUMAN_WARDROBE_FAILED` | `-32034` | Wardrobe Subsystem | Garment drape or props assembly failure |
| `ERR_INVALID_LANDMARK` | `-32035` | Anatomy Subsystem | Missing critical anatomical reference point |

---

### 2.2 Complete Enumerations Matrix (17 Enums + 1 Alias + 1 Lookup Set)

| Enum Name | Line | Base Class | Members Count | Explicit Members | Custom Methods / Normalizers |
|---|---|---|---|---|---|
| `CreatureType` | 74–86 | `(str, Enum)` | 12 | `QUADRUPED`, `BIPED`, `WINGED`, `AQUATIC`, `SERPENTINE`, `HYBRID`, `CUSTOM`, `WINGED_QUADRUPED`, `BIRD`, `SPIDER_ARTHROPOD`, `FISH_AQUATIC`, `CUSTOM_AUTO` | Standard string enum |
| `ViewMode` | 89–97 | `(str, Enum)` | 8 | `FRONT`, `SIDE`, `THREE_QUARTER`, `TOP`, `TURNAROUND_SHEET`, `ORTHOGRAPHIC_FRONT_SIDE`, `TURNTABLE_4VIEWS`, `ACTIVE_CAMERA` | Standard string enum |
| `Pose` | 100–104 | `(str, Enum)` | 4 | `NEUTRAL_T_POSE`, `NEUTRAL_A_POSE`, `STANDING_NEUTRAL`, `RELAXED` | Standard string enum |
| `Style` | 107–113 | `(str, Enum)` | 6 | `REALISTIC`, `STYLIZED`, `DARK_FANTASY`, `SCI_FI`, `CARTOON`, `SCULPTURE` | Standard string enum |
| `QualityTier` | 116–120 | `(str, Enum)` | 4 | `DRAFT`, `STANDARD`, `PRODUCTION`, `ULTRA` | Standard string enum |
| `TopologyType` | 123–127 | `(str, Enum)` | 4 | `QUAD_DOMINANT`, `PURE_QUAD`, `TRIANGULATED`, `ADAPTIVE` | Standard string enum |
| `RetopoMethod` | 130–135 | `(str, Enum)` | 5 | `QUADRIFLOW`, `DECIMATE`, `VOXEL_REMESH`, `MESHANYTHING_V2`, `MOCK` | Standard string enum |
| `RigType` | 138–142 | `(str, Enum)` | 4 | `BASIC_FK`, `RIGIFY_CREATURE`, `GAME_ENGINE_ROOT`, `DEFORM_ONLY` | Standard string enum |
| `SkinningMethod` | 145–148 | `(str, Enum)` | 3 | `AUTOMATIC_WEIGHTS`, `VOXEL_HEAT_DIFFUSE`, `GEODESIC_VOXEL` | Standard string enum |
| `RenderEngine` | 151–155 | `(str, Enum)` | 4 | `BLENDER_EEVEE`, `BLENDER_EEVEE_NEXT`, `CYCLES`, `BLENDER_WORKBENCH` | Standard string enum |
| `LightingPreset` | 158–163 | `(str, Enum)` | 5 | `STUDIO_THREE_POINT`, `DRAMATIC_RIM`, `NEUTRAL_SOFTBOX`, `OUTDOOR_SUN`, `SCENE_DEFAULT` | Standard string enum |
| `InspectorViewpoint` | 660–676 | `(str, Enum)` | 16 | `FRONT`, `SIDE`, `SIDE_LEFT`, `BACK`, `THREE_QUARTER`, `TOP`, `BOTTOM`, `HEAD`, `CLOSE_UP_HEAD`, `PORTRAIT`, `HANDS`, `CLOSE_UP_HANDS`, `TORSO`, `FEET`, `TURNTABLE`, `TURNTABLE_4VIEWS` | Used in Inspector camera math |
| `AnthropometricPreset` | 679–685 | `(str, Enum)` | 6 | `REALISTIC_HUMAN`, `STYLIZED_HEROINE`, `CHIBI_PETITE`, `REALISTIC_FEMALE`, `HEROIC_MALE`, `CHIBI` | Target proportion models |
| `DiagnosticShadingMode`| 699–704 | `(str, Enum)` | 5 | `SOLID`, `FLAT`, `WIREFRAME`, `MATERIAL`, `RENDERED` | Viewport shading mode |
| `DiagnosticColorType` | 707–712 | `(str, Enum)` | 5 | `RANDOM`, `MATERIAL`, `SINGLE`, `OBJECT`, `TEXTURE` | Viewport color mode |
| `DefectSeverity` | 868–892 | `(str, Enum)` | 4 | `CRITICAL`, `MAJOR`, `MINOR`, `INFO` | `@classmethod _missing_` handles aliases: `HIGH`, `MEDIUM`, `LOW`, `ERROR`, `WARNING`, `NOTICE` |
| `DefectCategory` | 895–927 | `(str, Enum)` | 4 | `PENETRATION`, `PROPORTION`, `SKINNING_PINCH`, `GROOMING_COLLISION` | `@classmethod _missing_` handles 14 legacy aliases (`CLIPPING`, `HAIR_CLIPPING`, etc.) |

**Enum Aliases and Sets:**
- Line 688: `TargetPreset = AnthropometricPreset`
- Line 691–696: `VALID_INSPECTOR_VIEWPOINTS_SET` (contains 16 enum values + 16 legacy string aliases including `"view_front"`, `"marionette"`, `"bodice"`, `"sandals"`).

---

### 2.3 Complete Classes & Exceptions Inventory (45 Classes)

| # | Class Name | Lines | Category | Base Class | Primary Responsibility |
|---|---|---|---|---|---|
| 1 | `MorphoMeshException` | 55–67 | Exceptions | `Exception` | Authoritative root exception carrying code, message, and details dict |
| 2 | `BoundingBox` | 170–174 | Base Primitives | `BaseModel` | Axis-aligned bounding box (`min_point`, `max_point`, `dimensions`) |
| 3 | `SceneObjectInfo` | 177–190 | Base Primitives | `BaseModel` | Metadata description of Blender scene object (transforms, polycounts, modifiers) |
| 4 | `BoundingBox3D` | 715–721 | Base Primitives | `BaseModel` | World-space Axis-Aligned Bounding Box (used in defect localization) |
| 5 | `GenerateConceptInput` | 197–217 | Creature Pipeline | `BaseModel` | Input parameters for concept image generation (Tool 1) |
| 6 | `GenerateConceptOutput` | 220–232 | Creature Pipeline | `BaseModel` | Generated concept image metadata and multi-view dictionary |
| 7 | `Create3DAssetInput` | 239–265 | Creature Pipeline | `BaseModel` | Single-image / text to 3D asset generation parameters (Tool 2) |
| 8 | `Create3DAssetOutput` | 268–279 | Creature Pipeline | `BaseModel` | Generated 3D mesh metadata, polycounts, texture map paths |
| 9 | `OptimizeTopologyInput` | 286–295 | Creature Pipeline | `BaseModel` | Retopology and quad reduction request parameters (Tool 3) |
| 10 | `OptimizeTopologyOutput` | 298–309 | Creature Pipeline | `BaseModel` | Retopology metrics, quad percentage, vertex/face count diff |
| 11 | `AutoRigInput` | 316–328 | Creature Pipeline | `BaseModel` | Creature skeleton estimation and skinning parameters (Tool 4) |
| 12 | `AutoRigOutput` | 331–346 | Creature Pipeline | `BaseModel` | Generated armature structure, bone count, exported asset path |
| 13 | `BlenderExecuteInput` | 353–360 | Creature Pipeline | `BaseModel` | Safe Python bpy execution request parameters (Tool 5) |
| 14 | `BlenderExecuteOutput` | 363–370 | Creature Pipeline | `BaseModel` | Execution stdout, stderr, serialized returned variables, timing |
| 15 | `SceneStatusInput` | 377–384 | Creature Pipeline | `BaseModel` | Scene hierarchy inspection filter parameters (Tool 6) |
| 16 | `SceneStatusOutput` | 387–398 | Creature Pipeline | `BaseModel` | Scene statistics, active objects, lights, cameras, materials |
| 17 | `RenderPreviewInput` | 405–425 | Creature Pipeline | `BaseModel` | Viewport preview render configuration (Tool 7) |
| 18 | `RenderPreviewOutput` | 428–438 | Creature Pipeline | `BaseModel` | Render output image path, timing, base64 thumbnail |
| 19 | `HumanAnatomyConfig` | 445–459 | Human Pipeline | `BaseModel` | Parametric anthropometry configuration (height, head ratio, girths) |
| 20 | `CreateHumanAssetInput` | 463–493 | Human Pipeline | `BaseModel` | Digital human generation parameters (Tool 8) |
| 21 | `HumanAssetResult` | 496–514 | Human Pipeline | `BaseModel` | Generated human mesh result (vertex groups, landmarks, blendshapes) |
| 22 | `AutoRigHumanInput` | 521–533 | Human Pipeline | `BaseModel` | Human Rigify metarig parameters (Tool 9) |
| 23 | `HumanRigResult` | 536–549 | Human Pipeline | `BaseModel` | Rigging output (163 DEF bones, hierarchy, blend file path) |
| 24 | `SetupHumanMaterialsInput`| 556–568 | Human Pipeline | `BaseModel` | Skin SSS and dual-chamber cornea shader setup (Tool 10) |
| 25 | `HumanMaterialResult` | 571–582 | Human Pipeline | `BaseModel` | Configured PBR material tree details |
| 26 | `GroomHumanInput` | 589–603 | Human Pipeline | `BaseModel` | Hair Curves / Geometry Nodes grooming parameters (Tool 11) |
| 27 | `HumanGroomingResult` | 606–616 | Human Pipeline | `BaseModel` | Hair curves generation result (layers, strand count, objects) |
| 28 | `DressHumanInput` | 623–637 | Human Pipeline | `BaseModel` | Wardrobe dress, sash, and props configuration (Tool 12) |
| 29 | `HumanWardrobeResult` | 640–650 | Human Pipeline | `BaseModel` | Generated garment meshes, marionette strings, butterflies |
| 30 | `SetupInspectorCameraInput`| 724–745 | Inspection | `BaseModel` | Multi-angle inspector camera framing parameters |
| 31 | `SetupInspectorCameraOutput`| 748–761 | Inspection | `BaseModel` | Inspector camera placement, transforms, target bounds |
| 32 | `CaptureViewportInput` | 764–797 | Inspection | `BaseModel` | Fast viewport capture parameters (shading, color type) |
| 33 | `CaptureViewportOutput` | 800–812 | Inspection | `BaseModel` | Captured image path, base64 preview, capture timing |
| 34 | `MultiAngleCaptureFrame` | 815–831 | Inspection | `BaseModel` | Metadata for a single angle frame in batch inspection |
| 35 | `CaptureMultiAngleInspectionInput` | 834–851 | Inspection | `BaseModel` | Multi-view inspection batch run parameters |
| 36 | `CaptureMultiAngleInspectionOutput` | 854–861 | Inspection | `BaseModel` | Collection of captured multi-angle frames |
| 37 | `ActionableRecommendation`| 930–973 | Critique | `BaseModel` | Remediation task prescription with priority and modifier suggestion |
| 38 | `DefectItem` | 976–1071 | Critique | `BaseModel` | Structured diagnostic defect (penetration, proportion, skinning) |
| 39 | `VisualCritiqueInput` | 1074–1130 | Critique | `BaseModel` | Closed-loop visual QA critique parameters |
| 40 | `VisualCritiqueOutput` | 1133–1163 | Critique | `BaseModel` | Comprehensive visual critique report and quality score |
| 41 | `AnimationItem` | 1170–1179 | Animation | `BaseModel` | Preset animation metadata from Meshy Animation Library |
| 42 | `ListAnimationsInput` | 1182–1190 | Animation | `BaseModel` | Search and filter criteria for animation presets |
| 43 | `ListAnimationsOutput` | 1193–1199 | Animation | `BaseModel` | Matched animation presets and category inventory |
| 44 | `AnimateAssetInput` | 1202–1213 | Animation | `BaseModel` | Animation retargeting parameters for rigged character |
| 45 | `AnimateAssetOutput` | 1216–1229 | Animation | `BaseModel` | Retargeted animation output paths and preview URL |

**Output Aliases:**
- Line 517: `CreateHumanAssetOutput = HumanAssetResult`
- Line 552: `AutoRigHumanOutput = HumanRigResult`
- Line 585: `SetupHumanMaterialsOutput = HumanMaterialResult`
- Line 619: `GroomHumanOutput = HumanGroomingResult`
- Line 653: `DressHumanOutput = HumanWardrobeResult`

---

### 2.4 Complete Pydantic Validators Inventory (16 Validator Methods across 8 Classes)

| Class | Method | Decorator | Target Fields | Logic / Normalization |
|---|---|---|---|---|
| `GenerateConceptInput` | `validate_dimension_step` | `@field_validator('width', 'height')` | `width`, `height` | Rounds non-multiple of 64 to closest multiple of 64 |
| `Create3DAssetInput` | `resolve_backend_alias` | `@model_validator(mode='before')` | model | Synchronizes `backend` and `model_backend` aliases |
| `RenderPreviewInput` | `normalize_engine` | `@field_validator('render_engine')` | `render_engine` | Coerces `'BLENDER_EEVEE_NEXT'` to `'BLENDER_EEVEE'` |
| `CreateHumanAssetInput`| `resolve_nested_config` | `@model_validator(mode='before')` | model | Unpacks nested `config: HumanAnatomyConfig` into top-level fields |
| `SetupInspectorCameraInput`| `validate_viewpoint` | `@field_validator('viewpoint')` | `viewpoint` | Validates against `VALID_INSPECTOR_VIEWPOINTS_SET` |
| `CaptureViewportInput` | `validate_shading_mode` | `@field_validator('shading_mode')` | `shading_mode` | Coerces to uppercase and validates against `DiagnosticShadingMode` |
| `CaptureViewportInput` | `validate_color_type` | `@field_validator('color_type')` | `color_type` | Coerces to uppercase and validates against `DiagnosticColorType` |
| `ActionableRecommendation`| `align_description_and_action`| `@model_validator(mode='before')` | model | Ensures `description` and `action` fallback to `guidance` |
| `ActionableRecommendation`| `normalize_category` | `@field_validator('category', mode='before')` | `category` | Delegates to `DefectCategory._missing_` |
| `ActionableRecommendation`| `normalize_priority` | `@field_validator('priority', mode='before')` | `priority` | Delegates to `DefectSeverity._missing_` |
| `DefectItem` | `align_defect_fields` | `@model_validator(mode='before')` | model | Harmonizes `defect_id`/`id`, `category`/`defect_type`, affected objects list, recommendation |
| `DefectItem` | `normalize_category` | `@field_validator('category', mode='before')` | `category` | Delegates to `DefectCategory._missing_` |
| `DefectItem` | `normalize_severity` | `@field_validator('severity', mode='before')` | `severity` | Delegates to `DefectSeverity._missing_` |
| `VisualCritiqueInput` | `validate_target_preset` | `@field_validator('target_preset')` | `target_preset` | Validates lowercase against `AnthropometricPreset` |
| `VisualCritiqueInput` | `resolve_aliases` | `@model_validator(mode='before')` | model | Synchronizes `char_name`, `clearance_threshold`, `camera_angles`/`viewpoints` |
| `VisualCritiqueOutput` | `sync_defect_count` | `@model_validator(mode='before')` | model | Computes `defect_count = len(defects)` and auto-evaluates `passed` |

---

## 3. Modular Sub-Package Architecture & Boundaries

The target directory structure within `src/morphomesh/` is:

```
src/morphomesh/
├── models/
│   ├── __init__.py          # Sub-package aggregator re-exporting all 101 symbols in __all__
│   ├── errors.py            # 32 ERR_* constants and MorphoMeshException
│   ├── enums.py             # 17 Enums, TargetPreset alias, VALID_INSPECTOR_VIEWPOINTS_SET
│   ├── base.py              # BoundingBox, SceneObjectInfo, BoundingBox3D
│   ├── creature.py          # FastMCP Tools 1-7 request/response schemas
│   ├── human.py             # Tools 8-12 schemas, HumanAnatomyConfig, 5 output aliases
│   ├── inspection.py        # Inspector camera, viewport capture, MultiAngleCaptureFrame
│   ├── critique.py          # Visual critique, DefectItem, ActionableRecommendation
│   └── animation.py         # Animation presets, list, retargeting schemas
└── models.py                # Backward-compatibility facade with explicit __all__
```

### Module Responsibilities & Internal Imports

```
   ┌─────────────────────────────────────────────────────────────┐
   │                          errors.py                          │ (Level 0)
   │  - 32 ERR_* error constants                                 │
   │  - MorphoMeshException                                      │
   └─────────────────────────────────────────────────────────────┘

   ┌─────────────────────────┐         ┌─────────────────────────┐
   │        enums.py         │         │         base.py         │ (Level 0)
   │  - 17 Enums             │         │  - BoundingBox          │
   │  - TargetPreset alias   │         │  - SceneObjectInfo      │
   │  - Viewpoints set       │         │  - BoundingBox3D        │
   └────────────┬────────────┘         └────────────┬────────────┘
                │                                   │
      ┌─────────┴───────────────┐         ┌─────────┴────────────┐
      ▼                         ▼         ▼                      ▼
┌──────────────┐         ┌──────────────┐                  ┌─────────────┐
│inspection.py │         │ creature.py  │                  │  human.py   │ (Level 1)
│- Cam Setup   │         │- Tools 1..7  │                  │- Tools 8..12│
│- Viewport    │         │  Inputs &    │                  │  AnatomyCfg │
│- MultiAngle  │         │  Outputs     │                  │  5 Aliases  │
└──────┬───────┘         └──────────────┘                  └─────────────┘
       │                                                          ▲
       │                 ┌────────────────────────────────────────┘
       ▼                 ▼
┌───────────────────────────────┐                          ┌─────────────┐
│          critique.py          │ (Level 2)                │animation.py │ (Level 0)
│  - DefectItem                 │                          │- List Anim  │
│  - ActionableRecommendation   │                          │- Retarget   │
│  - VisualCritiqueInput/Output │                          └─────────────┘
└──────────────┬────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   models/__init__.py & models.py                       │ (Level 3)
│   Unified re-exports of all 101 domain symbols with explicit __all__   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Submodule Specification & Complete Code Sketches

### 4.1 `src/morphomesh/models/errors.py`
**Dependencies:** stdlib only (`typing`).  
**Symbols (33):** 32 `ERR_*` constants + `MorphoMeshException`.

```python
"""
MorphoMesh: Authoritative Error Constants & Exception Taxonomy.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Union

# Global Error Codes Matrix
ERR_PARSE_ERROR = -32700
ERR_INVALID_REQUEST = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_INVALID_ARGUMENT = -32602
ERR_IMAGE_NOT_FOUND = -32001
ERR_BACKEND_UNAVAILABLE = -32002
ERR_VRAM_EXHAUSTED = -32003
ERR_REMESH_FAILED = -32004
ERR_SKINNING_HEAT_FAILURE = -32005
ERR_SCRIPT_SECURITY_VIOLATION = -32006
ERR_TIMEOUT = -32007
ERR_BLENDER_UNAVAILABLE = -32008
ERR_NO_CAMERA = -32009
ERR_ANATOMY_DETECTION_FAILED = -32010
ERR_INPUT_MESH_NOT_FOUND = -32011
ERR_INVALID_POLY_COUNT = -32012
ERR_NON_MANIFOLD_MESH = -32013
ERR_SCENE_NOT_FOUND = -32014
ERR_RENDER_FAILED = -32015
ERR_OUTPUT_WRITE_FAILED = -32016
ERR_SCRIPT_SYNTAX_ERROR = -32017
ERR_SCRIPT_RUNTIME_EXCEPTION = -32018
ERR_INFERENCE_FAILED = -32019
ERR_DISK_WRITE_FAILED = -32020
ERR_SCRIPT_EXECUTION_TIMEOUT = -32007
ERR_BLENDER_EXECUTION_FAILED = -32021
ERR_HUMAN_GENERATION_FAILED = -32030
ERR_HUMAN_RIGGING_FAILED = -32031
ERR_HUMAN_MATERIALS_FAILED = -32032
ERR_HUMAN_GROOMING_FAILED = -32033
ERR_HUMAN_WARDROBE_FAILED = -32034
ERR_INVALID_LANDMARK = -32035


class MorphoMeshException(Exception):
    """Authoritative base exception for all domain-specific MorphoMesh errors."""

    def __init__(
        self,
        code: Union[int, str],
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


__all__ = [
    "ERR_ANATOMY_DETECTION_FAILED",
    "ERR_BACKEND_UNAVAILABLE",
    "ERR_BLENDER_EXECUTION_FAILED",
    "ERR_BLENDER_UNAVAILABLE",
    "ERR_DISK_WRITE_FAILED",
    "ERR_HUMAN_GENERATION_FAILED",
    "ERR_HUMAN_GROOMING_FAILED",
    "ERR_HUMAN_MATERIALS_FAILED",
    "ERR_HUMAN_RIGGING_FAILED",
    "ERR_HUMAN_WARDROBE_FAILED",
    "ERR_IMAGE_NOT_FOUND",
    "ERR_INFERENCE_FAILED",
    "ERR_INPUT_MESH_NOT_FOUND",
    "ERR_INVALID_ARGUMENT",
    "ERR_INVALID_LANDMARK",
    "ERR_INVALID_POLY_COUNT",
    "ERR_INVALID_REQUEST",
    "ERR_METHOD_NOT_FOUND",
    "ERR_NON_MANIFOLD_MESH",
    "ERR_NO_CAMERA",
    "ERR_OUTPUT_WRITE_FAILED",
    "ERR_PARSE_ERROR",
    "ERR_REMESH_FAILED",
    "ERR_RENDER_FAILED",
    "ERR_SCENE_NOT_FOUND",
    "ERR_SCRIPT_EXECUTION_TIMEOUT",
    "ERR_SCRIPT_RUNTIME_EXCEPTION",
    "ERR_SCRIPT_SECURITY_VIOLATION",
    "ERR_SCRIPT_SYNTAX_ERROR",
    "ERR_SKINNING_HEAT_FAILURE",
    "ERR_TIMEOUT",
    "ERR_VRAM_EXHAUSTED",
    "MorphoMeshException",
]
```

---

### 4.2 `src/morphomesh/models/enums.py`
**Dependencies:** stdlib only (`enum`, `typing`).  
**Symbols (19):** 17 Enums + `TargetPreset` + `VALID_INSPECTOR_VIEWPOINTS_SET`.

```python
"""
MorphoMesh: Pipeline Enumerations & Presets Taxonomy.
"""
from __future__ import annotations

from enum import Enum
from typing import Any


class CreatureType(str, Enum):
    QUADRUPED = "quadruped"
    BIPED = "biped"
    WINGED = "winged"
    AQUATIC = "aquatic"
    SERPENTINE = "serpentine"
    HYBRID = "hybrid"
    CUSTOM = "custom"
    WINGED_QUADRUPED = "winged_quadruped"
    BIRD = "bird"
    SPIDER_ARTHROPOD = "spider_arthropod"
    FISH_AQUATIC = "fish_aquatic"
    CUSTOM_AUTO = "custom_auto"


class ViewMode(str, Enum):
    FRONT = "front"
    SIDE = "side"
    THREE_QUARTER = "three_quarter"
    TOP = "top"
    TURNAROUND_SHEET = "turnaround_sheet"
    ORTHOGRAPHIC_FRONT_SIDE = "orthographic_front_side"
    TURNTABLE_4VIEWS = "turntable_4views"
    ACTIVE_CAMERA = "active_camera"


class Pose(str, Enum):
    NEUTRAL_T_POSE = "neutral_t_pose"
    NEUTRAL_A_POSE = "neutral_a_pose"
    STANDING_NEUTRAL = "standing_neutral"
    RELAXED = "relaxed"


class Style(str, Enum):
    REALISTIC = "realistic"
    STYLIZED = "stylized"
    DARK_FANTASY = "dark_fantasy"
    SCI_FI = "sci_fi"
    CARTOON = "cartoon"
    SCULPTURE = "sculpture"


class QualityTier(str, Enum):
    DRAFT = "draft"
    STANDARD = "standard"
    PRODUCTION = "production"
    ULTRA = "ultra"


class TopologyType(str, Enum):
    QUAD_DOMINANT = "quad_dominant"
    PURE_QUAD = "pure_quad"
    TRIANGULATED = "triangulated"
    ADAPTIVE = "adaptive"


class RetopoMethod(str, Enum):
    QUADRIFLOW = "quadriflow"
    DECIMATE = "decimate"
    VOXEL_REMESH = "voxel_remesh"
    MESHANYTHING_V2 = "meshanything_v2"
    MOCK = "mock"


class RigType(str, Enum):
    BASIC_FK = "basic_fk"
    RIGIFY_CREATURE = "rigify_creature"
    GAME_ENGINE_ROOT = "game_engine_root"
    DEFORM_ONLY = "deform_only"


class SkinningMethod(str, Enum):
    AUTOMATIC_WEIGHTS = "automatic_weights"
    VOXEL_HEAT_DIFFUSE = "voxel_heat_diffuse"
    GEODESIC_VOXEL = "geodesic_voxel"


class RenderEngine(str, Enum):
    BLENDER_EEVEE = "BLENDER_EEVEE"
    BLENDER_EEVEE_NEXT = "BLENDER_EEVEE_NEXT"
    CYCLES = "CYCLES"
    BLENDER_WORKBENCH = "BLENDER_WORKBENCH"


class LightingPreset(str, Enum):
    STUDIO_THREE_POINT = "studio_three_point"
    DRAMATIC_RIM = "dramatic_rim"
    NEUTRAL_SOFTBOX = "neutral_softbox"
    OUTDOOR_SUN = "outdoor_sun"
    SCENE_DEFAULT = "scene_default"


class InspectorViewpoint(str, Enum):
    FRONT = "front"
    SIDE = "side"
    SIDE_LEFT = "side_left"
    BACK = "back"
    THREE_QUARTER = "three_quarter"
    TOP = "top"
    BOTTOM = "bottom"
    HEAD = "head"
    CLOSE_UP_HEAD = "close_up_head"
    PORTRAIT = "portrait"
    HANDS = "hands"
    CLOSE_UP_HANDS = "close_up_hands"
    TORSO = "torso"
    FEET = "feet"
    TURNTABLE = "turntable"
    TURNTABLE_4VIEWS = "turntable_4views"


class AnthropometricPreset(str, Enum):
    REALISTIC_HUMAN = "realistic_human"
    STYLIZED_HEROINE = "stylized_heroine"
    CHIBI_PETITE = "chibi_petite"
    REALISTIC_FEMALE = "realistic_female"
    HEROIC_MALE = "heroic_male"
    CHIBI = "chibi"


TargetPreset = AnthropometricPreset


VALID_INSPECTOR_VIEWPOINTS_SET = {e.value for e in InspectorViewpoint} | {
    "view_front", "front_view", "side_right", "view_side", "view_side_left",
    "view_back", "back_view", "front_three_quarter", "three_quarter_left",
    "back_three_quarter", "head_close_up", "hands_close_up", "marionette",
    "bodice", "sandals", "shoes",
}


class DiagnosticShadingMode(str, Enum):
    SOLID = "SOLID"
    FLAT = "FLAT"
    WIREFRAME = "WIREFRAME"
    MATERIAL = "MATERIAL"
    RENDERED = "RENDERED"


class DiagnosticColorType(str, Enum):
    RANDOM = "RANDOM"
    MATERIAL = "MATERIAL"
    SINGLE = "SINGLE"
    OBJECT = "OBJECT"
    TEXTURE = "TEXTURE"


class DefectSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if isinstance(value, str):
            val_upper = value.strip().upper()
            mapping = {
                "HIGH": cls.CRITICAL,
                "MEDIUM": cls.MAJOR,
                "LOW": cls.MINOR,
                "ERROR": cls.CRITICAL,
                "WARNING": cls.MAJOR,
                "NOTICE": cls.INFO,
            }
            if val_upper in mapping:
                return mapping[val_upper]
            for member in cls:
                if member.value.upper() == val_upper or member.name.upper() == val_upper:
                    return member
        return None


class DefectCategory(str, Enum):
    PENETRATION = "PENETRATION"
    PROPORTION = "PROPORTION"
    SKINNING_PINCH = "SKINNING_PINCH"
    GROOMING_COLLISION = "GROOMING_COLLISION"

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if isinstance(value, str):
            val_upper = value.strip().upper()
            mapping = {
                "CLIPPING": cls.PENETRATION,
                "MESH_PENETRATION": cls.PENETRATION,
                "FACE_OVERLAP": cls.PENETRATION,
                "SKIN_BURST": cls.PENETRATION,
                "PROPORTION_DEVIATION": cls.PROPORTION,
                "BODY_PROPORTION": cls.PROPORTION,
                "SKINNING_ARTIFACT": cls.SKINNING_PINCH,
                "RIG_PINCH": cls.SKINNING_PINCH,
                "PINCHING": cls.SKINNING_PINCH,
                "GROOMING_INTERSECTION": cls.GROOMING_COLLISION,
                "HAIR_CLIPPING": cls.GROOMING_COLLISION,
                "GROOMING_ROOT_SUBMERGED": cls.GROOMING_COLLISION,
                "GROOMING_BODY_COLLISION": cls.GROOMING_COLLISION,
                "GROOMING_GARMENT_COLLISION": cls.GROOMING_COLLISION,
            }
            if val_upper in mapping:
                return mapping[val_upper]
            for member in cls:
                if member.value.upper() == val_upper or member.name.upper() == val_upper:
                    return member
        return None


__all__ = [
    "AnthropometricPreset",
    "CreatureType",
    "DefectCategory",
    "DefectSeverity",
    "DiagnosticColorType",
    "DiagnosticShadingMode",
    "InspectorViewpoint",
    "LightingPreset",
    "Pose",
    "QualityTier",
    "RenderEngine",
    "RetopoMethod",
    "RigType",
    "SkinningMethod",
    "Style",
    "TargetPreset",
    "TopologyType",
    "VALID_INSPECTOR_VIEWPOINTS_SET",
    "ViewMode",
]
```

---

### 4.3 `src/morphomesh/models/base.py`
**Dependencies:** `pydantic`, `typing`.  
**Symbols (3):** `BoundingBox`, `SceneObjectInfo`, `BoundingBox3D`.

```python
"""
MorphoMesh: Geometric and Scene Primitive Schemas.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_point: List[float] = Field(..., description="[min_x, min_y, min_z]")
    max_point: List[float] = Field(..., description="[max_x, max_y, max_z]")
    dimensions: List[float] = Field(..., description="[width, depth, height]")


class SceneObjectInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    type: str
    location: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_euler: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = Field(default_factory=lambda: [1.0, 1.0, 1.0])
    parent: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    vertex_count: int = 0
    face_count: int = 0
    triangle_count: int = 0
    materials: List[str] = Field(default_factory=list)
    modifiers: List[str] = Field(default_factory=list)


class BoundingBox3D(BaseModel):
    """World-space Axis-Aligned Bounding Box."""
    model_config = ConfigDict(extra="ignore")

    min_point: List[float] = Field(..., description="[min_x, min_y, min_z]")
    max_point: List[float] = Field(..., description="[max_x, max_y, max_z]")
    dimensions: List[float] = Field(..., description="[width, depth, height]")


__all__ = [
    "BoundingBox",
    "BoundingBox3D",
    "SceneObjectInfo",
]
```

---

### 4.4 `src/morphomesh/models/creature.py`
**Dependencies:** `models.enums`, `models.base`, `pydantic`, `typing`.  
**Symbols (14):** Request/Response schemas for FastMCP Tools 1–7.

```python
"""
MorphoMesh: Creature Generation Pipeline Schemas (FastMCP Tools 1-7).
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .base import BoundingBox, SceneObjectInfo
from .enums import (
    CreatureType,
    LightingPreset,
    Pose,
    QualityTier,
    RenderEngine,
    RetopoMethod,
    RigType,
    SkinningMethod,
    Style,
    TopologyType,
    ViewMode,
)


class GenerateConceptInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    prompt: str = Field(..., min_length=3, max_length=2000, description="Natural language description of creature anatomy, species, features.")
    negative_prompt: str = Field(default="", max_length=1000, description="Negative constraints to avoid artifacts, cropping, or occlusions.")
    creature_type: Union[CreatureType, str] = Field(default=CreatureType.CUSTOM, description="Morphological archetype guiding prompt augmentation.")
    view_mode: Union[ViewMode, str] = Field(default=ViewMode.FRONT, description="Camera perspective tailored for 3D reconstruction.")
    pose: Union[Pose, str] = Field(default=Pose.STANDING_NEUTRAL, description="Rest pose preventing limb self-occlusion.")
    style: Union[Style, str] = Field(default=Style.REALISTIC, description="Visual rendering aesthetic.")
    background: str = Field(default="white_neutral", description="Neutral backdrop ensuring clean segmentation.")
    width: int = Field(default=1024, ge=512, le=2048, description="Image width in pixels (multiple of 64).")
    height: int = Field(default=1024, ge=512, le=2048, description="Image height in pixels (multiple of 64).")
    seed: int = Field(default=-1, ge=-1, le=2147483647, description="RNG seed (-1 for random).")
    output_format: str = Field(default="png", description="File format on disk.")
    backend: str = Field(default="default", description="Generator backend engine ('default', 'mock', 'gemini').")

    @field_validator("width", "height")
    @classmethod
    def validate_dimension_step(cls, v: int) -> int:
        if v % 64 != 0:
            return round(v / 64) * 64
        return v


class GenerateConceptOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    concept_id: str = Field(..., description="Unique concept UUID")
    image_path: str = Field(..., description="Absolute path to cached image")
    rgba_image_path: Optional[str] = Field(default=None, description="Path to alpha-isolated image")
    prompt_enhanced: str = Field(..., description="Augmented prompt with anatomical modifiers")
    creature_type: str
    view_mode: str
    dimensions: List[int]
    seed_used: int
    status: Literal["success", "mock_success"]
    views: Dict[str, str] = Field(default_factory=dict, description="Segmented views for turnaround sheets")
    backend_used: Optional[str] = Field(default=None, description="Backend generator used")


class Create3DAssetInput(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    image_path: Optional[str] = Field(default=None, description="Path to local concept image on disk.")
    concept_id: Optional[str] = Field(default=None, description="UUID of concept generated in Stage 1.")
    model_backend: str = Field(default="mock", description="3D AI generator engine backend (mock, meshy, trellis, hunyuan3d_2, tripo, triposr, step1x_3d).")
    backend: Optional[str] = Field(default=None, description="Alias for model_backend allowing backend='meshy' selection.")
    export_format: str = Field(default="glb", description="Target 3D file format (glb, obj, fbx, ply).")
    generate_pbr: bool = Field(default=True, description="Bake PBR textures (albedo, roughness, metallic, normal).")
    texture_resolution: int = Field(default=2048, description="Texture atlas resolution in pixels.")
    remove_background: bool = Field(default=True, description="Perform foreground isolation before 3D reconstruction.")
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0, description="Classifier-free guidance strength.")
    seed: int = Field(default=-1, ge=-1, description="RNG seed (-1 for random).")
    prompt: Optional[str] = Field(default=None, description="Direct text prompt for text-to-3D foundation models (e.g. Meshy, Tripo).")
    quality_tier: Optional[str] = Field(default="standard", description="Quality preset tier.")

    @model_validator(mode="before")
    @classmethod
    def resolve_backend_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            backend = data.get("backend")
            model_backend = data.get("model_backend")
            if backend and (not model_backend or model_backend == "mock"):
                data["model_backend"] = backend
                data["backend"] = backend
            elif model_backend:
                data["backend"] = model_backend
        return data


class Create3DAssetOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    asset_id: str = Field(..., description="Unique 3D asset UUID")
    mesh_path: str = Field(..., description="Path to generated .glb/.obj file")
    format: str
    vertex_count: int
    face_count: int
    has_pbr_materials: bool
    texture_paths: Dict[str, str] = Field(default_factory=dict)
    bounding_box: BoundingBox
    generation_time_seconds: float
    backend_used: str


class OptimizeTopologyInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    asset_id: Optional[str] = Field(default=None, description="Asset UUID from Stage 2.")
    input_mesh_path: Optional[str] = Field(default=None, description="Direct file path to 3D mesh.")
    target_poly_count: int = Field(default=10000, ge=500, le=500000, description="Desired polygon (face) count.")
    topology_type: Union[TopologyType, str] = Field(default=TopologyType.QUAD_DOMINANT, description="Preferred polygon topology.")
    preserve_uvs: bool = Field(default=True, description="Preserve UV coordinates.")
    preserve_sharp_edges: bool = Field(default=True, description="Preserve creased feature edges.")
    method: Union[RetopoMethod, str] = Field(default=RetopoMethod.QUADRIFLOW, description="Retopology solver algorithm.")
    output_format: str = Field(default="glb", description="Target file format.")


class OptimizeTopologyOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    optimized_asset_id: str
    output_mesh_path: str
    original_vertex_count: int
    original_face_count: int
    optimized_vertex_count: int
    optimized_face_count: int
    quad_percentage: float = Field(..., ge=0.0, le=100.0)
    reduction_ratio: float
    uv_preserved: bool
    processing_time_seconds: float


class AutoRigInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    asset_id: Optional[str] = Field(default=None, description="Asset UUID to rig.")
    input_mesh_path: Optional[str] = Field(default=None, description="Direct path to mesh file.")
    creature_type: Union[CreatureType, str] = Field(default=CreatureType.QUADRUPED, description="Morphological archetype guiding metarig selection.")
    rig_type: Union[RigType, str] = Field(default=RigType.RIGIFY_CREATURE, description="Armature control hierarchy.")
    skinning_method: Union[SkinningMethod, str] = Field(default=SkinningMethod.AUTOMATIC_WEIGHTS, description="Vertex skin weighting algorithm.")
    symmetry: bool = Field(default=True, description="Enforce X bilateral symmetry.")
    generate_test_animation: bool = Field(default=True, description="Attach test animation action.")
    load_into_scene: bool = Field(default=True, description="Import into active Blender scene.")
    backend: Optional[str] = Field(default="blender", description="Rigging execution backend: 'blender' or 'meshy'.")
    model_task_id: Optional[str] = Field(default=None, description="Meshy generation task ID to rig via Meshy API.")
    height_meters: Optional[float] = Field(default=1.7, description="Approximate model height in meters for AI rigging.")


class AutoRigOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rigged_asset_id: str
    blend_file_path: Optional[str] = None
    exported_mesh_path: str
    armature_name: str
    bone_count: int
    bone_hierarchy: List[str] = Field(default_factory=list)
    creature_type: str
    has_skin_weights: bool
    test_action_name: Optional[str] = None
    status: Literal["success", "mock_success"]
    rig_task_id: Optional[str] = Field(default=None, description="Meshy cloud rigging task ID if applicable.")
    downloaded_glb_path: Optional[str] = Field(default=None, description="Path to downloaded rigged GLB.")
    downloaded_fbx_path: Optional[str] = Field(default=None, description="Path to downloaded rigged FBX.")
    basic_animations: Dict[str, str] = Field(default_factory=dict, description="Paths or URLs to basic animations (e.g. walking, running).")


class BlenderExecuteInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    script: str = Field(..., min_length=1, max_length=10000, description="Python script with bpy commands to execute in Blender.")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Execution timeout limit in seconds.")
    target_scene: Optional[str] = Field(default=None, description="Target Blender scene name.")
    save_after: bool = Field(default=False, description="Save scene after execution.")
    save_path: Optional[str] = Field(default=None, description="Destination path for saved .blend file.")
    return_variables: List[str] = Field(default_factory=list, description="Variable names in script scope to serialize into response.")


class BlenderExecuteOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    success: bool
    stdout: str = ""
    stderr: str = ""
    returned_data: Dict[str, Any] = Field(default_factory=dict)
    execution_time_seconds: float = 0.0
    blend_file_path: Optional[str] = None


class SceneStatusInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    scene_name: Optional[str] = Field(default=None, description="Specific scene name to inspect.")
    include_mesh_stats: bool = Field(default=True, description="Include vertex/face counts.")
    include_hierarchy: bool = Field(default=True, description="Include object parent-child relationships.")
    include_materials: bool = Field(default=True, description="Include Principled BSDF shader materials.")
    include_armatures: bool = Field(default=True, description="Include armature bone structures.")
    include_cameras_lights: bool = Field(default=True, description="Include cameras and lights.")


class SceneStatusOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    scene_name: str
    blender_version: str
    active_object: Optional[str] = None
    object_count: int
    total_vertices: int
    total_faces: int
    objects: List[SceneObjectInfo] = Field(default_factory=list)
    armatures: List[Dict[str, Any]] = Field(default_factory=list)
    cameras: List[Dict[str, Any]] = Field(default_factory=list)
    lights: List[Dict[str, Any]] = Field(default_factory=list)


class RenderPreviewInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    camera_name: Optional[str] = Field(default=None, description="Camera object name.")
    resolution_width: int = Field(default=1024, ge=256, le=4096, description="Render width in pixels.")
    resolution_height: int = Field(default=1024, ge=256, le=4096, description="Render height in pixels.")
    render_engine: Union[RenderEngine, str] = Field(default=RenderEngine.BLENDER_EEVEE, description="Blender render engine.")
    samples: int = Field(default=64, ge=1, le=1024, description="Render samples.")
    view_angle: Union[ViewMode, str] = Field(default=ViewMode.THREE_QUARTER, description="Camera perspective viewpoint.")
    transparent_background: bool = Field(default=True, description="Transparent alpha background.")
    lighting_preset: Union[LightingPreset, str] = Field(default=LightingPreset.STUDIO_THREE_POINT, description="Studio lighting configuration.")
    save_to_disk: bool = Field(default=True, description="Save rendered image to disk cache.")
    output_dir: Optional[str] = Field(default=None, description="Destination directory for rendered PNG.")

    @field_validator("render_engine")
    @classmethod
    def normalize_engine(cls, v: Union[RenderEngine, str]) -> str:
        val = v.value if isinstance(v, RenderEngine) else str(v)
        if val == "BLENDER_EEVEE_NEXT":
            return "BLENDER_EEVEE"
        return val


class RenderPreviewOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    image_path: str
    image_format: str = "png"
    resolution: List[int]
    render_engine: str
    samples: int
    render_time_seconds: float
    view_angle: str
    lighting_preset: str
    base64_image: Optional[str] = None


__all__ = [
    "AutoRigInput",
    "AutoRigOutput",
    "BlenderExecuteInput",
    "BlenderExecuteOutput",
    "Create3DAssetInput",
    "Create3DAssetOutput",
    "GenerateConceptInput",
    "GenerateConceptOutput",
    "OptimizeTopologyInput",
    "OptimizeTopologyOutput",
    "RenderPreviewInput",
    "RenderPreviewOutput",
    "SceneStatusInput",
    "SceneStatusOutput",
]
```

---

### 4.5 `src/morphomesh/models/human.py`
**Dependencies:** `models.base`, `pydantic`, `typing`.  
**Symbols (16):** 11 classes + 5 output aliases.

```python
"""
MorphoMesh: Digital Human Pipeline Schemas (FastMCP Tools 8-12).
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .base import BoundingBox


class HumanAnatomyConfig(BaseModel):
    """Anthropometric parametric specification for digital human geometry synthesis."""
    model_config = ConfigDict(extra="ignore")

    height: float = Field(default=1.65, ge=1.0, le=2.5, description="Total standing height in meters (canonical: 1.65m).")
    head_ratio: float = Field(default=7.41, ge=5.0, le=10.0, description="Height-to-head ratio (Yu Nian An: 7.41 heads).")
    chest_girth: float = Field(default=0.82, ge=0.5, le=1.5, description="Chest / bust circumference in meters.")
    waist_girth: float = Field(default=0.58, ge=0.4, le=1.2, description="Waist circumference in meters (cinched waist).")
    hip_girth: float = Field(default=0.86, ge=0.5, le=1.5, description="Hip circumference in meters (0.70 waist-to-hip ratio).")
    shoulder_width: float = Field(default=0.36, ge=0.2, le=0.8, description="Biacromial shoulder diameter in meters.")
    arm_span: float = Field(default=1.62, ge=1.0, le=2.5, description="Fingertip-to-fingertip arm span in meters.")
    leg_length: float = Field(default=0.88, ge=0.5, le=1.5, description="Inseam / leg length in meters.")
    gender: str = Field(default="female", description="Biological gender template ('female' or 'male').")
    style: str = Field(default="stylized_photorealism", description="Visual aesthetic style ('stylized_photorealism', 'realistic').")
    poly_budget: int = Field(default=25000, ge=1000, le=200000, description="Target polygon face budget for body mesh.")


class CreateHumanAssetInput(BaseModel):
    """Input parameters for morphomesh_create_human_asset."""
    model_config = ConfigDict(extra="ignore")

    character_name: str = Field(default="Yu_Nian_An", description="Character identifier name.")
    prompt: str = Field(default="Yu Nian An female semi-realistic character", description="Prompt description.")
    gender: str = Field(default="female", description="Character gender.")
    height: float = Field(default=1.65, ge=1.0, le=2.5, description="Height in meters.")
    head_ratio: float = Field(default=7.41, ge=5.0, le=10.0, description="Head-to-body proportion ratio.")
    style: str = Field(default="stylized_photorealism", description="Visual aesthetic style.")
    chest_girth: float = Field(default=0.82, ge=0.5, le=1.5, description="Chest girth in meters.")
    waist_girth: float = Field(default=0.58, ge=0.4, le=1.2, description="Waist girth in meters.")
    hip_girth: float = Field(default=0.86, ge=0.5, le=1.5, description="Hip girth in meters.")
    poly_budget: int = Field(default=25000, ge=1000, le=200000, description="Target face count.")
    include_blendshapes: bool = Field(default=True, description="Generate 52 Apple ARKit FACS blendshapes.")
    export_format: str = Field(default="glb", description="Export format (glb, obj, fbx).")
    load_into_scene: bool = Field(default=True, description="Load created mesh into active Blender scene.")
    config: Optional[HumanAnatomyConfig] = Field(default=None, description="Optional nested anatomy configuration.")

    @model_validator(mode="before")
    @classmethod
    def resolve_nested_config(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("config") is not None:
            cfg = data["config"]
            cfg_dict = cfg.model_dump() if hasattr(cfg, "model_dump") else (cfg if isinstance(cfg, dict) else {})
            for key in ["height", "head_ratio", "gender", "style", "chest_girth", "waist_girth", "hip_girth", "poly_budget"]:
                if key in cfg_dict:
                    default_val = cls.model_fields[key].default
                    if key not in data or data[key] == default_val:
                        data[key] = cfg_dict[key]
        return data


class HumanAssetResult(BaseModel):
    """Authoritative result of digital human mesh generation."""
    model_config = ConfigDict(extra="ignore")

    asset_id: str = Field(..., description="Unique human asset UUID.")
    mesh_path: str = Field(..., description="Path to generated 3D mesh file on disk.")
    character_name: str = Field(default="Yu_Nian_An", description="Character identifier name.")
    gender: str = Field(default="female", description="Character gender.")
    height: float = Field(default=1.65, description="Total standing height in meters.")
    head_ratio: float = Field(default=7.41, description="Height-to-head ratio.")
    vertex_count: int = Field(..., description="Total vertex count.")
    face_count: int = Field(..., description="Total polygon face count.")
    quad_ratio: float = Field(default=0.95, ge=0.0, le=1.0, description="Fraction of quads in mesh (>=0.95 in deforming areas).")
    vertex_groups: List[str] = Field(default_factory=list, description="Populated standardized vertex groups.")
    landmarks: Dict[str, List[float]] = Field(default_factory=dict, description="Anatomical 3D landmark coordinates for Rigify snapping.")
    shape_keys: List[str] = Field(default_factory=list, description="52 ARKit FACS shape key names.")
    bounding_box: BoundingBox = Field(..., description="Calculated 3D bounding box.")
    has_pbr_materials: bool = Field(default=False, description="Whether PBR materials are bound.")
    status: Literal["success", "mock_success"] = Field(default="success", description="Execution status.")


CreateHumanAssetOutput = HumanAssetResult


class AutoRigHumanInput(BaseModel):
    """Input parameters for morphomesh_auto_rig_human."""
    model_config = ConfigDict(extra="ignore")

    human_asset_id: Optional[str] = Field(default=None, description="Human asset UUID to rig.")
    mesh_object_name: str = Field(default="Human_Base_Mesh", description="Target mesh object name in Blender scene.")
    target_object: Optional[str] = Field(default=None, description="Alias for mesh_object_name.")
    rig_type: str = Field(default="rigify_human", description="Rig type (rigify_human, basic_biped).")
    skinning_method: str = Field(default="automatic_weights", description="Skin binding algorithm.")
    include_face_rig: bool = Field(default=True, description="Include 28 facial deformer bones.")
    include_finger_rig: bool = True
    pose: str = Field(default="puppeteer_pose", description="Initial rest or test pose (puppeteer_pose, a_pose, t_pose).")
    export_format: str = Field(default="fbx", description="Target rigged export format.")


class HumanRigResult(BaseModel):
    """Authoritative result of digital human rigging."""
    model_config = ConfigDict(extra="ignore")

    rigged_asset_id: str = Field(..., description="Unique rigged asset UUID.")
    armature_name: str = Field(..., description="Name of the generated armature in Blender.")
    bone_count: int = Field(..., description="Total bone count in armature.")
    def_bone_count: int = Field(default=163, description="Exact count of DEF deforming bones (163 DEF bones).")
    bone_hierarchy: List[str] = Field(default_factory=list, description="List of primary deform bone names.")
    blend_file_path: Optional[str] = Field(default=None, description="Path to saved .blend file if requested.")
    exported_mesh_path: Optional[str] = Field(default=None, description="Path to exported rigged asset on disk.")
    has_skin_weights: bool = Field(default=True, description="Whether anti-pinch skin weights are bound.")
    pose: str = Field(default="puppeteer_pose", description="Active pose applied to the rig.")
    status: Literal["success", "mock_success"] = Field(default="success", description="Execution status.")


AutoRigHumanOutput = HumanRigResult


class SetupHumanMaterialsInput(BaseModel):
    """Input parameters for morphomesh_setup_human_materials."""
    model_config = ConfigDict(extra="ignore")

    mesh_object_name: str = Field(default="Human_Base_Mesh", description="Target character body mesh object name.")
    target_object: Optional[str] = Field(default=None, description="Alias for mesh_object_name.")
    material_preset: str = Field(default="yu_nian_an", description="PBR shader preset ('yu_nian_an', 'standard_human').")
    skin_tone: str = Field(default="porcelain_fair", description="Skin tone base color preset.")
    subsurface_scattering: bool = Field(default=True, description="Enable Random Walk SSS on skin shader.")
    refractive_eyes: bool = Field(default=True, description="Configure 2-chamber refractive cornea and concave iris dish.")
    render_engine: str = Field(default="CYCLES", description="Target render engine ('CYCLES', 'BLENDER_EEVEE').")
    save_after: bool = Field(default=False, description="Save .blend file after material assignment.")
    save_path: Optional[str] = Field(default=None, description="Destination path for saved .blend file.")


class HumanMaterialResult(BaseModel):
    """Authoritative result of human PBR material setup."""
    model_config = ConfigDict(extra="ignore")

    material_preset: str = Field(default="yu_nian_an", description="PBR material preset configured.")
    materials_created: List[str] = Field(default_factory=list, description="Names of created materials.")
    assigned_objects: List[str] = Field(default_factory=list, description="Objects receiving material assignments.")
    subsurface_scattering: bool = Field(default=True, description="Subsurface scattering status.")
    refractive_eyes: bool = Field(default=True, description="Dual-chamber eye optics status.")
    socket_version: str = Field(default="Principled BSDF v2", description="Shader socket architecture version.")
    blend_file_path: Optional[str] = Field(default=None, description="Path to saved .blend file if saved.")
    status: Literal["success", "mock_success"] = Field(default="success", description="Execution status.")


SetupHumanMaterialsOutput = HumanMaterialResult


class GroomHumanInput(BaseModel):
    """Input parameters for morphomesh_groom_human."""
    model_config = ConfigDict(extra="ignore")

    mesh_object_name: str = Field(default="Human_Base_Mesh", description="Target mesh object name in scene.")
    target_object: Optional[str] = Field(default=None, description="Alias for mesh_object_name.")
    hair_style: str = Field(default="hime_cut_long", description="Hairstyle preset ('hime_cut_long', 'straight_bangs').")
    hairstyle: Optional[str] = Field(default=None, description="Alias for hair_style.")
    hair_color: str = Field(default="silky_black", description="Hair melanin and color preset.")
    strand_count: int = Field(default=15000, ge=1000, le=200000, description="Parent/guide hair curves count.")
    include_eyebrows: bool = Field(default=True, description="Include procedural eyebrow groom curves.")
    include_eyelashes: bool = Field(default=True, description="Include procedural eyelash groom curves.")
    generate_ribbons: bool = Field(default=False, description="Generate polygonal quad ribbon mesh for real-time export.")
    save_after: bool = Field(default=False, description="Save .blend file after grooming.")
    save_path: Optional[str] = Field(default=None, description="Destination path for saved .blend file.")


class HumanGroomingResult(BaseModel):
    """Authoritative result of human hair grooming setup."""
    model_config = ConfigDict(extra="ignore")

    hair_style: str = Field(default="hime_cut_long", description="Configured hairstyle preset.")
    hair_color: str = Field(default="silky_black", description="Hair tint and melanin configuration.")
    layers: List[str] = Field(default_factory=list, description="Hair strata layers (bangs, sidelocks, back cascade, etc.).")
    strand_count: int = Field(default=15000, description="Total guide/parent curve strands created.")
    hair_objects: List[str] = Field(default_factory=list, description="Names of created Hair Curves objects in Blender.")
    blend_file_path: Optional[str] = Field(default=None, description="Path to saved .blend file if saved.")
    status: Literal["success", "mock_success"] = Field(default="success", description="Execution status.")


GroomHumanOutput = HumanGroomingResult


class DressHumanInput(BaseModel):
    """Input parameters for morphomesh_dress_human."""
    model_config = ConfigDict(extra="ignore")

    human_object_name: str = Field(default="Human_Base_Mesh", description="Target character body mesh object name.")
    target_object: Optional[str] = Field(default=None, description="Alias for human_object_name.")
    outfit: str = Field(default="yu_nian_an_dress", description="Costume preset ('yu_nian_an_dress').")
    outfit_preset: Optional[str] = Field(default=None, description="Alias for outfit.")
    include_sandals: bool = Field(default=True, description="Include flat slip-on sandals.")
    include_red_threads: bool = Field(default=True, description="Include 10 taut glowing crimson marionette strings.")
    include_glowing_butterflies: bool = Field(default=True, description="Include instanced luminous white butterflies.")
    butterfly_count: int = Field(default=10, ge=1, le=50, description="Count of luminous white butterflies to stage.")
    clearance_offset: float = Field(default=0.015, ge=0.005, le=0.05, description="Garment body radial clearance offset in meters.")
    save_after: bool = Field(default=False, description="Save .blend file after wardrobe generation.")
    save_path: Optional[str] = Field(default=None, description="Destination path for saved .blend file.")


class HumanWardrobeResult(BaseModel):
    """Authoritative result of human wardrobe and props generation."""
    model_config = ConfigDict(extra="ignore")

    outfit_preset: str = Field(default="yu_nian_an_dress", description="Costume preset configured.")
    garments: List[str] = Field(default_factory=list, description="Names of generated garment meshes (bodice, sash, pleated skirt).")
    accessories: List[str] = Field(default_factory=list, description="Names of generated accessories (sandals, red strings).")
    prop_count: int = Field(default=20, description="Total count of active props (10 strings + 10 butterflies).")
    clearance_offset: float = Field(default=0.015, description="Radial body clearance maintained to eliminate clipping.")
    blend_file_path: Optional[str] = Field(default=None, description="Path to saved .blend file if saved.")
    status: Literal["success", "mock_success"] = Field(default="success", description="Execution status.")


DressHumanOutput = HumanWardrobeResult


__all__ = [
    "AutoRigHumanInput",
    "AutoRigHumanOutput",
    "CreateHumanAssetInput",
    "CreateHumanAssetOutput",
    "DressHumanInput",
    "DressHumanOutput",
    "GroomHumanInput",
    "GroomHumanOutput",
    "HumanAnatomyConfig",
    "HumanAssetResult",
    "HumanGroomingResult",
    "HumanMaterialResult",
    "HumanRigResult",
    "HumanWardrobeResult",
    "SetupHumanMaterialsInput",
    "SetupHumanMaterialsOutput",
]
```

---

### 4.6 `src/morphomesh/models/inspection.py`
**Dependencies:** `models.enums`, `pydantic`, `typing`.  
**Symbols (7):** Inspector camera, viewport grab, and multi-angle inspection frames.

```python
"""
MorphoMesh: Inspector Camera & Viewport Capture Schemas (Milestone 2).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import (
    DiagnosticColorType,
    DiagnosticShadingMode,
    InspectorViewpoint,
    VALID_INSPECTOR_VIEWPOINTS_SET,
)


class SetupInspectorCameraInput(BaseModel):
    """Input parameters for morphomesh.setup_inspector_camera."""
    model_config = ConfigDict(extra="ignore")

    viewpoint: str = Field(default="three_quarter", description="Viewing angle preset ('front', 'side', 'three_quarter', etc.).")
    target_object: Optional[str] = Field(default=None, description="Optional target character mesh object name.")
    target_center: Optional[List[float]] = Field(default=None, description="Explicit [x, y, z] target center.")
    framing_radius: Optional[float] = Field(default=None, description="Explicit framing bounding sphere radius.")
    focal_length: float = Field(default=50.0, ge=10.0, le=300.0, description="Camera lens focal length in mm.")
    camera_name: str = Field(default="MorphoMesh_Inspector_Camera", description="Name of inspector camera in Blender.")
    margin: float = Field(default=0.15, ge=0.0, le=1.0, description="Safety framing margin factor.")
    resolution: List[int] = Field(default_factory=lambda: [1024, 1024], description="Target image resolution [width, height].")

    @field_validator("viewpoint")
    @classmethod
    def validate_viewpoint(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("viewpoint cannot be empty")
        v_clean = v.lower().strip()
        if v_clean not in VALID_INSPECTOR_VIEWPOINTS_SET:
            raise ValueError(f"Invalid viewpoint '{v}'. Allowed: {sorted(list(VALID_INSPECTOR_VIEWPOINTS_SET))}")
        return v_clean


class SetupInspectorCameraOutput(BaseModel):
    """Result of morphomesh.setup_inspector_camera."""
    model_config = ConfigDict(extra="ignore")

    status: str = "success"
    camera_name: str
    viewpoint: str
    focal_length: float
    camera_location: List[float]
    camera_rotation: List[float]
    target_center: List[float]
    framing_distance: float
    bounding_radius: float
    bounding_box: Optional[Dict[str, Any]] = None


class CaptureViewportInput(BaseModel):
    """Input parameters for morphomesh.capture_viewport."""
    model_config = ConfigDict(extra="ignore")

    output_path: Optional[str] = Field(default=None, description="Destination path for captured PNG.")
    camera_name: str = Field(default="MorphoMesh_Inspector_Camera", description="Camera object to capture through.")
    resolution: List[int] = Field(default_factory=lambda: [1024, 1024], description="[width, height] resolution.")
    resolution_width: Optional[int] = Field(default=None, description="Alternative width parameter.")
    resolution_height: Optional[int] = Field(default=None, description="Alternative height parameter.")
    shading_mode: str = Field(default="SOLID", description="Viewport shading ('SOLID', 'FLAT', 'WIREFRAME', 'MATERIAL').")
    color_type: str = Field(default="RANDOM", description="Solid color mode ('RANDOM', 'MATERIAL', 'SINGLE', 'OBJECT').")
    output_dir: Optional[str] = Field(default=None, description="Optional directory to store output if output_path is None.")

    @field_validator("shading_mode")
    @classmethod
    def validate_shading_mode(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("shading_mode cannot be empty")
        v_upper = v.upper().strip()
        valid_shading = {e.value for e in DiagnosticShadingMode}
        if v_upper not in valid_shading:
            raise ValueError(f"Invalid shading_mode '{v}'. Allowed: {sorted(list(valid_shading))}")
        return v_upper

    @field_validator("color_type")
    @classmethod
    def validate_color_type(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("color_type cannot be empty")
        v_upper = v.upper().strip()
        valid_colors = {e.value for e in DiagnosticColorType}
        if v_upper not in valid_colors:
            raise ValueError(f"Invalid color_type '{v}'. Allowed: {sorted(list(valid_colors))}")
        return v_upper


class CaptureViewportOutput(BaseModel):
    """Result of morphomesh.capture_viewport."""
    model_config = ConfigDict(extra="ignore")

    status: str = "success"
    image_path: str
    image_format: str = "png"
    resolution: List[int]
    shading_mode: str
    color_type: str
    camera_name: str
    base64_preview: Optional[str] = None
    capture_time_seconds: float = 0.0


class MultiAngleCaptureFrame(BaseModel):
    """Metadata for a single captured angle within batch inspection."""
    model_config = ConfigDict(extra="ignore")

    viewpoint: str
    image_path: str
    image_format: str = "png"
    resolution: List[int]
    shading_mode: str
    color_type: str
    camera_location: Optional[List[float]] = None
    camera_rotation: Optional[List[float]] = None
    target_center: Optional[List[float]] = None
    framing_distance: Optional[float] = None
    bounding_radius: Optional[float] = None
    capture_time_seconds: float = 0.0
    base64_image: Optional[str] = None


class CaptureMultiAngleInspectionInput(BaseModel):
    """Input parameters for morphomesh.capture_multi_angle_inspection."""
    model_config = ConfigDict(extra="ignore")

    viewpoints: Optional[List[str]] = Field(
        default=None,
        description="List of viewpoints (defaults to ['front', 'three_quarter', 'side', 'back', 'close_up_head']).",
    )
    target_object: Optional[str] = Field(default=None, description="Name of character mesh to frame.")
    output_dir: Optional[str] = Field(default=None, description="Directory to save rendered frames.")
    resolution: List[int] = Field(default_factory=lambda: [1024, 1024], description="[width, height] resolution.")
    resolution_width: Optional[int] = Field(default=None, description="Alternative width parameter.")
    resolution_height: Optional[int] = Field(default=None, description="Alternative height parameter.")
    shading_mode: str = Field(default="SOLID", description="Viewport shading mode ('SOLID', 'FLAT', 'WIREFRAME').")
    color_type: str = Field(default="RANDOM", description="Color mode ('RANDOM', 'MATERIAL', 'OBJECT').")
    focal_length: float = Field(default=50.0, ge=10.0, le=300.0, description="Camera focal length in mm.")
    camera_name: str = Field(default="MorphoMesh_Inspector_Camera", description="Inspector camera name.")
    include_base64: bool = Field(default=True, description="Whether to embed base64 image strings.")


class CaptureMultiAngleInspectionOutput(BaseModel):
    """Result of morphomesh.capture_multi_angle_inspection."""
    model_config = ConfigDict(extra="ignore")

    status: str = "success"
    capture_count: int
    viewpoints: List[str] = Field(default_factory=list)
    captures: List[MultiAngleCaptureFrame] = Field(default_factory=list)


__all__ = [
    "CaptureMultiAngleInspectionInput",
    "CaptureMultiAngleInspectionOutput",
    "CaptureViewportInput",
    "CaptureViewportOutput",
    "MultiAngleCaptureFrame",
    "SetupInspectorCameraInput",
    "SetupInspectorCameraOutput",
]
```

---

### 4.7 `src/morphomesh/models/critique.py`
**Dependencies:** `models.enums`, `models.base`, `models.inspection`, `pydantic`, `uuid`, `typing`.  
**Symbols (4):** `ActionableRecommendation`, `DefectItem`, `VisualCritiqueInput`, `VisualCritiqueOutput`.

```python
"""
MorphoMesh: Closed-Loop Visual Quality Critique Schemas (Milestone 3).
"""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .base import BoundingBox3D
from .enums import AnthropometricPreset, DefectCategory, DefectSeverity, TargetPreset
from .inspection import MultiAngleCaptureFrame


class ActionableRecommendation(BaseModel):
    """Structured actionable prescription for automated or manual remediation."""
    model_config = ConfigDict(extra="ignore")

    action_id: str = Field(default_factory=lambda: f"REC-{uuid.uuid4().hex[:6]}", description="Unique recommendation ID.")
    action: Optional[str] = Field(default=None, description="Action name/verb (e.g. RESCALE_HEAD, SMOOTH_WEIGHTS).")
    category: Optional[Union[DefectCategory, str]] = Field(default=None, description="Target defect category.")
    target_objects: List[str] = Field(default_factory=list, description="Mesh/curve objects requiring remediation.")
    description: Optional[str] = Field(default=None, description="Human and agent-readable instructions.")
    guidance: Optional[str] = Field(default=None, description="Detailed guidance instructions.")
    suggested_modifier: Optional[str] = Field(default=None, description="Recommended Blender modifier (Shrinkwrap, Smooth, Displace).")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Concrete parameters for automated remediation.")
    priority: Union[DefectSeverity, str] = Field(default=DefectSeverity.MAJOR, description="Remediation priority.")

    @model_validator(mode="before")
    @classmethod
    def align_description_and_action(cls, data: Any) -> Any:
        if isinstance(data, dict):
            desc = data.get("description")
            act = data.get("action")
            guide = data.get("guidance")
            if not desc:
                data["description"] = guide or act or "Remediation recommended."
            if not act:
                data["action"] = desc or "REMEDIATE"
        return data

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> Any:
        if isinstance(v, str):
            res = DefectCategory._missing_(v)
            if res:
                return res
        return v

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v: Any) -> Any:
        if isinstance(v, str):
            res = DefectSeverity._missing_(v)
            if res:
                return res
        return v


class DefectItem(BaseModel):
    """Individual structural defect diagnosed by visual critic."""
    model_config = ConfigDict(extra="ignore")

    defect_id: str = Field(default_factory=lambda: f"DEF-{uuid.uuid4().hex[:6]}", description="Unique defect ID.")
    id: Optional[str] = Field(default=None, description="Alias for defect_id.")
    category: Union[DefectCategory, str] = Field(..., description="Defect classification category.")
    defect_type: Optional[str] = Field(default=None, description="Legacy/convenience defect string type.")
    severity: Union[DefectSeverity, str] = Field(default=DefectSeverity.MAJOR, description="Defect severity.")
    affected_objects: List[str] = Field(default_factory=list, description="Object names involved in defect.")
    object_name: Optional[str] = Field(default=None, description="Primary affected object name.")
    source_object: Optional[str] = Field(default=None, description="Source object involved in collision.")
    target_object: Optional[str] = Field(default=None, description="Target object involved in collision.")
    description: str = Field(..., description="Diagnostic textual description.")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="Confidence score of detection (0.0 to 1.0).")
    location: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0], description="Primary 3D world coordinate [x, y, z] of defect centroid.")
    sample_locations: List[List[float]] = Field(default_factory=list, description="Additional sample 3D points where defect occurs.")
    bounding_box: Optional[BoundingBox3D] = Field(default=None, description="Local 3D bounding box enclosing defect.")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Quantitative diagnostic metrics.")
    penetration_depth_mm: Optional[float] = Field(default=None, description="Max penetration depth in mm if category is PENETRATION.")
    penetration_count: int = Field(default=0, description="Number of penetrating vertices or samples.")
    penetrated_triangles: List[int] = Field(default_factory=list, description="Indices of penetrating triangles.")
    affected_vertices: List[int] = Field(default_factory=list, description="Indices of affected vertices.")
    affected_faces: List[int] = Field(default_factory=list, description="Indices of affected faces.")
    recommendation: Optional[Union[ActionableRecommendation, str]] = Field(default=None, description="Remediation recommendation.")
    actionable_recommendation: Optional[str] = Field(default=None, description="Textual summary recommendation.")

    @model_validator(mode="before")
    @classmethod
    def align_defect_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # ID sync
            d_id = data.get("defect_id")
            s_id = data.get("id")
            if not d_id and s_id:
                data["defect_id"] = s_id
                data["id"] = s_id
            elif d_id and not s_id:
                data["id"] = d_id
            elif not d_id and not s_id:
                new_id = f"DEF-{uuid.uuid4().hex[:6]}"
                data["defect_id"] = new_id
                data["id"] = new_id

            # Category sync
            cat = data.get("category")
            dtype = data.get("defect_type")
            if not cat and dtype:
                data["category"] = dtype
            elif cat and not dtype:
                data["defect_type"] = cat.value if isinstance(cat, Enum) else str(cat)

            # Object name & affected_objects sync
            aff = data.get("affected_objects") or []
            obj_name = data.get("object_name")
            src_obj = data.get("source_object")
            tgt_obj = data.get("target_object")
            combined_objs = list(aff)
            if obj_name and obj_name not in combined_objs:
                combined_objs.append(obj_name)
            if src_obj and src_obj not in combined_objs:
                combined_objs.append(src_obj)
            if tgt_obj and tgt_obj not in combined_objs:
                combined_objs.append(tgt_obj)
            data["affected_objects"] = combined_objs
            if not obj_name and combined_objs:
                data["object_name"] = combined_objs[0]

            # Recommendation sync
            rec = data.get("recommendation")
            act_rec = data.get("actionable_recommendation")
            if not rec and act_rec:
                data["recommendation"] = act_rec
            elif not act_rec and isinstance(rec, str):
                data["actionable_recommendation"] = rec
            elif not act_rec and hasattr(rec, "description"):
                data["actionable_recommendation"] = getattr(rec, "description", str(rec))
        return data

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> Any:
        if isinstance(v, str):
            res = DefectCategory._missing_(v)
            if res:
                return res
        return v

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, v: Any) -> Any:
        if isinstance(v, str):
            res = DefectSeverity._missing_(v)
            if res:
                return res
        return v


class VisualCritiqueInput(BaseModel):
    """Input parameters for morphomesh.critique_visual_quality."""
    model_config = ConfigDict(extra="ignore")

    target_object: Optional[str] = Field(default="Human_Base_Mesh", description="Target character body mesh name.")
    character_name: Optional[str] = Field(default=None, description="Character root or identifier name.")
    body_obj_name: Optional[str] = Field(default=None, description="Explicit body mesh name.")
    garment_obj_names: Optional[List[str]] = Field(default=None, description="List of garment mesh names.")
    hair_obj_names: Optional[List[str]] = Field(default=None, description="List of hair curve/mesh names.")
    armature_obj_name: Optional[str] = Field(default=None, description="Armature object name.")
    camera_angles: Optional[List[str]] = Field(
        default_factory=lambda: ["front", "side", "three_quarter", "back"],
        description="Camera viewing angles for visual inspection.",
    )
    viewpoints: Optional[List[str]] = Field(default=None, description="Alias for camera_angles.")
    target_preset: str = Field(default="stylized_heroine", description="Anthropometric target preset.")
    clearance_tolerance: float = Field(default=0.0005, ge=0.0, description="Penetration clearance threshold in meters (0.5mm).")
    clearance_threshold: Optional[float] = Field(default=None, description="Alias for clearance_tolerance.")
    evaluate_penetration: bool = Field(default=True, description="Evaluate garment/armor mesh penetration.")
    evaluate_proportions: bool = Field(default=True, description="Evaluate body proportions against preset.")
    evaluate_skinning: bool = Field(default=True, description="Evaluate rig deformation and pinching.")
    evaluate_grooming: bool = Field(default=True, description="Evaluate hair curve intersections.")
    capture_images: bool = Field(default=False, description="Whether to capture multi-angle viewport PNGs.")
    resolution: List[int] = Field(default_factory=lambda: [1024, 1024], description="Viewport render resolution.")

    @field_validator("target_preset")
    @classmethod
    def validate_target_preset(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("target_preset cannot be empty")
        v_clean = v.lower().strip()
        valid_presets = {e.value for e in AnthropometricPreset}
        if v_clean not in valid_presets:
            raise ValueError(f"Invalid target_preset '{v}'. Allowed: {sorted(list(valid_presets))}")
        return v_clean

    @model_validator(mode="before")
    @classmethod
    def resolve_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "char_name" in data and "character_name" not in data:
                data["character_name"] = data["char_name"]
            if "clearance_threshold" in data and "clearance_tolerance" not in data:
                data["clearance_tolerance"] = data["clearance_threshold"]
            elif "clearance_tolerance" in data and "clearance_threshold" not in data:
                data["clearance_threshold"] = data["clearance_tolerance"]
            if "character_name" in data and ("target_object" not in data or data["target_object"] == "Human_Base_Mesh"):
                data["target_object"] = f"{data['character_name']}_Base_Mesh" if not data.get("target_object") else data["target_object"]
            if "body_obj_name" in data and ("target_object" not in data or data["target_object"] == "Human_Base_Mesh"):
                data["target_object"] = data["body_obj_name"]
            elif "target_object" in data and "body_obj_name" not in data:
                data["body_obj_name"] = data["target_object"]
            if "viewpoints" in data and ("camera_angles" not in data or not data["camera_angles"]):
                data["camera_angles"] = data["viewpoints"]
            elif "camera_angles" in data and "viewpoints" not in data:
                data["viewpoints"] = data["camera_angles"]
        return data


class VisualCritiqueOutput(BaseModel):
    """Diagnostic critique report returned by closed-loop visual QA engine."""
    model_config = ConfigDict(extra="ignore")

    status: str = Field(default="success", description="Critique execution status ('success' or 'error').")
    passed: bool = Field(default=True, description="Overall pass/fail verdict (True if no CRITICAL or excessive MAJOR defects).")
    quality_score: float = Field(default=100.0, ge=0.0, le=100.0, description="Overall quality score (0.0 to 100.0).")
    defect_count: int = Field(default=0, description="Total number of diagnosed defects.")
    defects: List[DefectItem] = Field(default_factory=list, description="List of structured defect items.")
    recommendations: List[str] = Field(default_factory=list, description="Human-readable remediation recommendations.")
    actionable_recommendations: List[ActionableRecommendation] = Field(default_factory=list, description="Structured actionable remediation tasks.")
    inspected_objects: List[str] = Field(default_factory=list, description="List of mesh/curve object names inspected.")
    scene_stats: Dict[str, Any] = Field(default_factory=dict, description="Geometric statistics (vertices, faces, dimensions, ratios).")
    evaluated_angles: List[str] = Field(default_factory=list, description="Camera angles evaluated.")
    capture_previews: List[MultiAngleCaptureFrame] = Field(default_factory=list, description="Viewport preview frames if requested.")
    execution_time_seconds: float = Field(default=0.0, description="Evaluation run duration in seconds.")

    @model_validator(mode="before")
    @classmethod
    def sync_defect_count(cls, data: Any) -> Any:
        if isinstance(data, dict):
            defs = data.get("defects") or []
            if "defect_count" not in data:
                data["defect_count"] = len(defs)
            if "passed" not in data:
                has_critical = any(
                    (d.get("severity") in ("CRITICAL", DefectSeverity.CRITICAL) if isinstance(d, dict) else d.severity == DefectSeverity.CRITICAL)
                    for d in defs
                )
                data["passed"] = not has_critical
        return data


__all__ = [
    "ActionableRecommendation",
    "DefectItem",
    "VisualCritiqueInput",
    "VisualCritiqueOutput",
]
```

---

### 4.8 `src/morphomesh/models/animation.py`
**Dependencies:** `pydantic`, `typing`.  
**Symbols (5):** `AnimationItem`, `ListAnimationsInput`, `ListAnimationsOutput`, `AnimateAssetInput`, `AnimateAssetOutput`.

```python
"""
MorphoMesh: Animation & Meshy Library Models.
"""
from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class AnimationItem(BaseModel):
    """Preset animation metadata from Meshy Animation Library."""
    model_config = ConfigDict(extra="ignore")

    action_id: int = Field(..., description="Unique integer ID for the animation action.")
    name: str = Field(..., description="Human-readable animation name.")
    key: str = Field(..., description="Unique stable slug identifier.")
    category: str = Field(..., description="Top-level category: WalkAndRun, BodyMovements, DailyActions, Fighting, Dancing.")
    sub_category: Optional[str] = Field(default=None, description="Sub-category grouping.")
    preview_url: Optional[str] = Field(default=None, description="Direct URL to animated GIF preview.")


class ListAnimationsInput(BaseModel):
    """Filter parameters for querying available animations."""
    model_config = ConfigDict(extra="ignore")

    category: Optional[str] = Field(default=None, description="Filter by category: WalkAndRun, BodyMovements, DailyActions, Fighting, Dancing.")
    sub_category: Optional[str] = Field(default=None, description="Filter by sub-category.")
    search: Optional[str] = Field(default=None, description="Search term matching name or key.")
    action_ids: Optional[List[int]] = Field(default=None, description="Specific action IDs to fetch.")
    limit: Optional[int] = Field(default=50, ge=1, le=500, description="Max items to return.")


class ListAnimationsOutput(BaseModel):
    """Response containing matched animation presets."""
    model_config = ConfigDict(extra="ignore")

    total_count: int = Field(..., description="Total animations matching the criteria.")
    animations: List[AnimationItem] = Field(default_factory=list, description="List of matched animations.")
    categories: List[str] = Field(default_factory=list, description="Available category names.")


class AnimateAssetInput(BaseModel):
    """Workload request parameters to retarget an animation onto a rigged character."""
    model_config = ConfigDict(extra="ignore")

    asset_id: Optional[str] = Field(default=None, description="Rigged asset ID or mesh ID.")
    rig_task_id: Optional[str] = Field(default=None, description="Meshy cloud rigging task ID.")
    input_mesh_path: Optional[str] = Field(default=None, description="Local path to rigged GLB/FBX.")
    action_id: Optional[int] = Field(default=None, description="Preset animation action ID from library.")
    action_name: Optional[str] = Field(default=None, description="Action name or keyword to search if action_id is not specified.")
    fps: int = Field(default=30, description="Target animation frame rate: 24, 25, 30, 60.")
    output_format: str = Field(default="glb", description="Desired 3D file format: glb or fbx.")
    backend: Literal["meshy", "blender"] = Field(default="meshy", description="Animation engine backend: 'meshy' (cloud retargeting) or 'blender' (local procedural/pose).")


class AnimateAssetOutput(BaseModel):
    """Result of retargeting an animation onto a character."""
    model_config = ConfigDict(extra="ignore")

    animated_asset_id: str = Field(..., description="Unique identifier for the animated asset.")
    animation_task_id: Optional[str] = Field(default=None, description="Meshy animation cloud task ID.")
    rig_task_id: Optional[str] = Field(default=None, description="Source rigging task ID.")
    action_id: Optional[int] = Field(default=None, description="Applied animation action ID.")
    action_name: Optional[str] = Field(default=None, description="Applied animation action name.")
    animated_glb_path: Optional[str] = Field(default=None, description="Local path to animated GLB file.")
    animated_fbx_path: Optional[str] = Field(default=None, description="Local path to animated FBX file.")
    preview_url: Optional[str] = Field(default=None, description="URL of animated GIF preview.")
    status: Literal["success", "mock_success"] = Field(default="success", description="Execution status.")
    duration_seconds: float = Field(default=0.0, description="Execution time in seconds.")


__all__ = [
    "AnimateAssetInput",
    "AnimateAssetOutput",
    "AnimationItem",
    "ListAnimationsInput",
    "ListAnimationsOutput",
]
```

---

### 4.9 `src/morphomesh/models/__init__.py`
**Dependencies:** Re-exports all 8 submodules.  
**Explicit `__all__`:** Exhaustively lists all 101 domain symbols.

```python
"""
MorphoMesh Models Subsystem.

Authoritative Pydantic v2 data models, enums, error constants, and exception hierarchy.
"""
from __future__ import annotations

from .animation import (
    AnimateAssetInput,
    AnimateAssetOutput,
    AnimationItem,
    ListAnimationsInput,
    ListAnimationsOutput,
)
from .base import (
    BoundingBox,
    BoundingBox3D,
    SceneObjectInfo,
)
from .creature import (
    AutoRigInput,
    AutoRigOutput,
    BlenderExecuteInput,
    BlenderExecuteOutput,
    Create3DAssetInput,
    Create3DAssetOutput,
    GenerateConceptInput,
    GenerateConceptOutput,
    OptimizeTopologyInput,
    OptimizeTopologyOutput,
    RenderPreviewInput,
    RenderPreviewOutput,
    SceneStatusInput,
    SceneStatusOutput,
)
from .critique import (
    ActionableRecommendation,
    DefectItem,
    VisualCritiqueInput,
    VisualCritiqueOutput,
)
from .enums import (
    AnthropometricPreset,
    CreatureType,
    DefectCategory,
    DefectSeverity,
    DiagnosticColorType,
    DiagnosticShadingMode,
    InspectorViewpoint,
    LightingPreset,
    Pose,
    QualityTier,
    RenderEngine,
    RetopoMethod,
    RigType,
    SkinningMethod,
    Style,
    TargetPreset,
    TopologyType,
    VALID_INSPECTOR_VIEWPOINTS_SET,
    ViewMode,
)
from .errors import (
    ERR_ANATOMY_DETECTION_FAILED,
    ERR_BACKEND_UNAVAILABLE,
    ERR_BLENDER_EXECUTION_FAILED,
    ERR_BLENDER_UNAVAILABLE,
    ERR_DISK_WRITE_FAILED,
    ERR_HUMAN_GENERATION_FAILED,
    ERR_HUMAN_GROOMING_FAILED,
    ERR_HUMAN_MATERIALS_FAILED,
    ERR_HUMAN_RIGGING_FAILED,
    ERR_HUMAN_WARDROBE_FAILED,
    ERR_IMAGE_NOT_FOUND,
    ERR_INFERENCE_FAILED,
    ERR_INPUT_MESH_NOT_FOUND,
    ERR_INVALID_ARGUMENT,
    ERR_INVALID_LANDMARK,
    ERR_INVALID_POLY_COUNT,
    ERR_INVALID_REQUEST,
    ERR_METHOD_NOT_FOUND,
    ERR_NON_MANIFOLD_MESH,
    ERR_NO_CAMERA,
    ERR_OUTPUT_WRITE_FAILED,
    ERR_PARSE_ERROR,
    ERR_REMESH_FAILED,
    ERR_RENDER_FAILED,
    ERR_SCENE_NOT_FOUND,
    ERR_SCRIPT_EXECUTION_TIMEOUT,
    ERR_SCRIPT_RUNTIME_EXCEPTION,
    ERR_SCRIPT_SECURITY_VIOLATION,
    ERR_SCRIPT_SYNTAX_ERROR,
    ERR_SKINNING_HEAT_FAILURE,
    ERR_TIMEOUT,
    ERR_VRAM_EXHAUSTED,
    MorphoMeshException,
)
from .human import (
    AutoRigHumanInput,
    AutoRigHumanOutput,
    CreateHumanAssetInput,
    CreateHumanAssetOutput,
    DressHumanInput,
    DressHumanOutput,
    GroomHumanInput,
    GroomHumanOutput,
    HumanAnatomyConfig,
    HumanAssetResult,
    HumanGroomingResult,
    HumanMaterialResult,
    HumanRigResult,
    HumanWardrobeResult,
    SetupHumanMaterialsInput,
    SetupHumanMaterialsOutput,
)

__all__ = [
    "ActionableRecommendation",
    "AnimateAssetInput",
    "AnimateAssetOutput",
    "AnimationItem",
    "AnthropometricPreset",
    "AutoRigHumanInput",
    "AutoRigHumanOutput",
    "AutoRigInput",
    "AutoRigOutput",
    "BlenderExecuteInput",
    "BlenderExecuteOutput",
    "BoundingBox",
    "BoundingBox3D",
    "CaptureMultiAngleInspectionInput",
    "CaptureMultiAngleInspectionOutput",
    "CaptureViewportInput",
    "CaptureViewportOutput",
    "Create3DAssetInput",
    "Create3DAssetOutput",
    "CreateHumanAssetInput",
    "CreateHumanAssetOutput",
    "CreatureType",
    "DefectCategory",
    "DefectItem",
    "DefectSeverity",
    "DiagnosticColorType",
    "DiagnosticShadingMode",
    "DressHumanInput",
    "DressHumanOutput",
    "ERR_ANATOMY_DETECTION_FAILED",
    "ERR_BACKEND_UNAVAILABLE",
    "ERR_BLENDER_EXECUTION_FAILED",
    "ERR_BLENDER_UNAVAILABLE",
    "ERR_DISK_WRITE_FAILED",
    "ERR_HUMAN_GENERATION_FAILED",
    "ERR_HUMAN_GROOMING_FAILED",
    "ERR_HUMAN_MATERIALS_FAILED",
    "ERR_HUMAN_RIGGING_FAILED",
    "ERR_HUMAN_WARDROBE_FAILED",
    "ERR_IMAGE_NOT_FOUND",
    "ERR_INFERENCE_FAILED",
    "ERR_INPUT_MESH_NOT_FOUND",
    "ERR_INVALID_ARGUMENT",
    "ERR_INVALID_LANDMARK",
    "ERR_INVALID_POLY_COUNT",
    "ERR_INVALID_REQUEST",
    "ERR_METHOD_NOT_FOUND",
    "ERR_NON_MANIFOLD_MESH",
    "ERR_NO_CAMERA",
    "ERR_OUTPUT_WRITE_FAILED",
    "ERR_PARSE_ERROR",
    "ERR_REMESH_FAILED",
    "ERR_RENDER_FAILED",
    "ERR_SCENE_NOT_FOUND",
    "ERR_SCRIPT_EXECUTION_TIMEOUT",
    "ERR_SCRIPT_RUNTIME_EXCEPTION",
    "ERR_SCRIPT_SECURITY_VIOLATION",
    "ERR_SCRIPT_SYNTAX_ERROR",
    "ERR_SKINNING_HEAT_FAILURE",
    "ERR_TIMEOUT",
    "ERR_VRAM_EXHAUSTED",
    "GenerateConceptInput",
    "GenerateConceptOutput",
    "GroomHumanInput",
    "GroomHumanOutput",
    "HumanAnatomyConfig",
    "HumanAssetResult",
    "HumanGroomingResult",
    "HumanMaterialResult",
    "HumanRigResult",
    "HumanWardrobeResult",
    "InspectorViewpoint",
    "LightingPreset",
    "ListAnimationsInput",
    "ListAnimationsOutput",
    "MorphoMeshException",
    "MultiAngleCaptureFrame",
    "OptimizeTopologyInput",
    "OptimizeTopologyOutput",
    "Pose",
    "QualityTier",
    "RenderEngine",
    "RenderPreviewInput",
    "RenderPreviewOutput",
    "RetopoMethod",
    "RigType",
    "SceneObjectInfo",
    "SceneStatusInput",
    "SceneStatusOutput",
    "SetupHumanMaterialsInput",
    "SetupHumanMaterialsOutput",
    "SetupInspectorCameraInput",
    "SetupInspectorCameraOutput",
    "SkinningMethod",
    "Style",
    "TargetPreset",
    "TopologyType",
    "VALID_INSPECTOR_VIEWPOINTS_SET",
    "ViewMode",
    "VisualCritiqueInput",
    "VisualCritiqueOutput",
]
```

---

## 5. Backward-Compatibility Facade Design (`src/morphomesh/models.py`)

### 5.1 Import Machinery and Coexistence Analysis
In standard Python 3.11+, when a directory `src/morphomesh/models/` contains `__init__.py`, any statement such as `import morphomesh.models` or `from morphomesh.models import X` resolves directly to `src/morphomesh/models/__init__.py`.

However, maintaining `src/morphomesh/models.py` alongside `src/morphomesh/models/` serves two vital purposes:
1. **Direct file-path loaders:** Scripts or AST tools (such as IDE indexers, static analyzers, and explicit module loaders) that inspect `src/morphomesh/models.py` continue to find a valid module definition.
2. **Strict Project Specification Compliance:** Requirement R1 of Milestone 1 explicitly dictates:
   > *"Preserves `src/morphomesh/models.py` as backward-compatible facade re-exporting all 62 classes, 32 error constants, and enums via `__all__`."*

### 5.2 Facade Implementation Pattern
The facade file `src/morphomesh/models.py` re-exports all symbols from the new `morphomesh.models` subpackage with clean, explicit declarations:

```python
"""
MorphoMesh Models Facade (Backward Compatibility).

Re-exports all authoritative schemas, enumerations, error constants, and
validators from the modularized ``morphomesh.models`` package.
"""
from __future__ import annotations

from morphomesh.models import (
    ActionableRecommendation,
    AnimateAssetInput,
    AnimateAssetOutput,
    AnimationItem,
    AnthropometricPreset,
    AutoRigHumanInput,
    AutoRigHumanOutput,
    AutoRigInput,
    AutoRigOutput,
    BlenderExecuteInput,
    BlenderExecuteOutput,
    BoundingBox,
    BoundingBox3D,
    CaptureMultiAngleInspectionInput,
    CaptureMultiAngleInspectionOutput,
    CaptureViewportInput,
    CaptureViewportOutput,
    Create3DAssetInput,
    Create3DAssetOutput,
    CreateHumanAssetInput,
    CreateHumanAssetOutput,
    CreatureType,
    DefectCategory,
    DefectItem,
    DefectSeverity,
    DiagnosticColorType,
    DiagnosticShadingMode,
    DressHumanInput,
    DressHumanOutput,
    ERR_ANATOMY_DETECTION_FAILED,
    ERR_BACKEND_UNAVAILABLE,
    ERR_BLENDER_EXECUTION_FAILED,
    ERR_BLENDER_UNAVAILABLE,
    ERR_DISK_WRITE_FAILED,
    ERR_HUMAN_GENERATION_FAILED,
    ERR_HUMAN_GROOMING_FAILED,
    ERR_HUMAN_MATERIALS_FAILED,
    ERR_HUMAN_RIGGING_FAILED,
    ERR_HUMAN_WARDROBE_FAILED,
    ERR_IMAGE_NOT_FOUND,
    ERR_INFERENCE_FAILED,
    ERR_INPUT_MESH_NOT_FOUND,
    ERR_INVALID_ARGUMENT,
    ERR_INVALID_LANDMARK,
    ERR_INVALID_POLY_COUNT,
    ERR_INVALID_REQUEST,
    ERR_METHOD_NOT_FOUND,
    ERR_NON_MANIFOLD_MESH,
    ERR_NO_CAMERA,
    ERR_OUTPUT_WRITE_FAILED,
    ERR_PARSE_ERROR,
    ERR_REMESH_FAILED,
    ERR_RENDER_FAILED,
    ERR_SCENE_NOT_FOUND,
    ERR_SCRIPT_EXECUTION_TIMEOUT,
    ERR_SCRIPT_RUNTIME_EXCEPTION,
    ERR_SCRIPT_SECURITY_VIOLATION,
    ERR_SCRIPT_SYNTAX_ERROR,
    ERR_SKINNING_HEAT_FAILURE,
    ERR_TIMEOUT,
    ERR_VRAM_EXHAUSTED,
    GenerateConceptInput,
    GenerateConceptOutput,
    GroomHumanInput,
    GroomHumanOutput,
    HumanAnatomyConfig,
    HumanAssetResult,
    HumanGroomingResult,
    HumanMaterialResult,
    HumanRigResult,
    HumanWardrobeResult,
    InspectorViewpoint,
    LightingPreset,
    ListAnimationsInput,
    ListAnimationsOutput,
    MorphoMeshException,
    MultiAngleCaptureFrame,
    OptimizeTopologyInput,
    OptimizeTopologyOutput,
    Pose,
    QualityTier,
    RenderEngine,
    RenderPreviewInput,
    RenderPreviewOutput,
    RetopoMethod,
    RigType,
    SceneObjectInfo,
    SceneStatusInput,
    SceneStatusOutput,
    SetupHumanMaterialsInput,
    SetupHumanMaterialsOutput,
    SetupInspectorCameraInput,
    SetupInspectorCameraOutput,
    SkinningMethod,
    Style,
    TargetPreset,
    TopologyType,
    VALID_INSPECTOR_VIEWPOINTS_SET,
    ViewMode,
    VisualCritiqueInput,
    VisualCritiqueOutput,
)
from morphomesh.models import __all__ as _models_all

__all__ = list(_models_all)
```

---

## 6. Dependency Graph & Circular Import Verification

### 6.1 Inter-Module Dependency Table

| Module | Depends On | Depended Upon By | Cycle Potential |
|---|---|---|---|
| `errors.py` | *(None)* | `__init__.py`, facade | **Zero** (Leaf) |
| `enums.py` | *(None)* | `creature.py`, `inspection.py`, `critique.py`, `__init__.py`, facade | **Zero** (Leaf) |
| `base.py` | *(None)* | `creature.py`, `human.py`, `critique.py`, `__init__.py`, facade | **Zero** (Leaf) |
| `animation.py` | *(None)* | `__init__.py`, facade | **Zero** (Leaf) |
| `human.py` | `base.py` | `__init__.py`, facade | **Zero** (Level 1) |
| `inspection.py`| `enums.py` | `critique.py`, `__init__.py`, facade | **Zero** (Level 1) |
| `creature.py` | `enums.py`, `base.py` | `__init__.py`, facade | **Zero** (Level 1) |
| `critique.py` | `enums.py`, `base.py`, `inspection.py` | `__init__.py`, facade | **Zero** (Level 2) |
| `__init__.py` | All 8 submodules | External callers, facade | **Zero** (Root Aggregator) |

### 6.2 Topological Sort Proof
Define partial order $\prec$ where $A \prec B$ means $B$ imports $A$:
$$\{errors, enums, base, animation\} \prec \{human, inspection, creature\} \prec \{critique\} \prec \{__init__\}$$

Since every edge $(u, v)$ in the dependency graph satisfies $\text{Level}(u) < \text{Level}(v)$, the graph is strictly acyclic. No cycles can exist.

---

## 7. Migration Playbook for Builder Agent

1. **Step 1: Create Directory**
   `mkdir src/morphomesh/models/`
2. **Step 2: Generate Submodules in Topological Order**
   - Create `src/morphomesh/models/errors.py`
   - Create `src/morphomesh/models/enums.py`
   - Create `src/morphomesh/models/base.py`
   - Create `src/morphomesh/models/animation.py`
   - Create `src/morphomesh/models/human.py`
   - Create `src/morphomesh/models/inspection.py`
   - Create `src/morphomesh/models/creature.py`
   - Create `src/morphomesh/models/critique.py`
3. **Step 3: Generate Sub-Package `__init__.py`**
   - Populate `src/morphomesh/models/__init__.py` with all imports and authoritative `__all__`.
4. **Step 4: Update Facade `src/morphomesh/models.py`**
   - Replace monolithic code with clean re-export facade.
5. **Step 5: Run Verification Command Suite**
   - `uv run pytest tests/test_tools_schema.py`
   - `uv run pytest tests/test_visual_critic.py`
   - `uv run pytest tests/test_fastmcp_human_tools.py`
   - `uv run pytest tests/test_fastmcp_inspection_tools.py`
   - `uv run python -c "import morphomesh.models; from morphomesh.models import *; print(len(dir(morphomesh.models)))"`
   - Assert all 101 symbols resolve with 0 import errors and 0 circular dependency warnings.
