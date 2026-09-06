# Project: Armored War Bear & MorphoMesh Engine Upgrade

## Architecture
MorphoMesh is an automated pipeline and MCP Server connecting AI generation with Blender. This project upgrades the core MorphoMesh engine (`src/morphomesh/`) to generate high-fidelity, photorealistic biological creatures with anatomically authentic geometry, volumetric fur grooming, and PBR shading, using the Armored War Bear as the canonical benchmark demonstration.

### Component Boundaries
1. **Procedural Geometry Engine (`src/morphomesh/inference_adapter.py`, `src/morphomesh/connectors/`)**:
   - Upgraded `MeshGeometry` with biological modeling primitives: `add_curved_claw()`, `add_plantigrade_paw()`, `add_articulated_head()`, `add_anatomical_torso()`.
   - Mathematical forward-and-downward claw curvature guarantee: $\vec{d}_{\text{claw}} \cdot \vec{u}_{\text{fwd}} > 0.60$ and $d_z < 0$.
   - Universal animal archetype generator supporting Ursine, Canine, Feline, and Biped forms with 18 standardized vertex groups.
2. **Volumetric Fur & Grooming Pipeline (`src/morphomesh/grooming.py`, `src/morphomesh/blender_bridge.py`)**:
   - Multi-layer hair grooming system: dense undercoat (8,000 strands, length 0.04m, clump 0.3) and coarse guard hairs (4,000 strands, length 0.09m, clump 0.5) with interpolated children yielding > 100,000 render strands.
   - Biological growth flow radiating from dorsal spine downwards across torso, shoulders, and limbs.
   - Dual representation: Native Blender `Curves` / particle grooming in `.blend` + curve-to-mesh ribbon generator for standard glTF 2.0 `.glb` export.
3. **PBR Material & Armor Fitting Engine (`src/morphomesh/materials.py`, `src/morphomesh/armor.py`)**:
   - 5 distinct 4-channel PBR material slots compliant with Blender 5.2.1 Principled BSDF v2: Fur (melanin/sheen), Wet Skin/Nose (coat moisture 0.85, roughness 0.15), Claws (keratin, roughness 0.38), Weathered Steel Armor (metallic 1.0, roughness 0.42), Brass Trim (metallic 1.0, roughness 0.32).
   - Procedural armor fitting generator maintaining non-intersecting radial clearance $\Delta r \in [0.02, 0.04]\text{m}$ over dorsal shoulders and wrists.
4. **Blender Bridge & IPC Bridge (`src/morphomesh/blender_bridge.py`)**:
   - Bug fix at line 472 (`"success": True` vs `status == "success"`) restoring live socket execution to active Blender sessions on port 9876.
5. **Canonical Benchmark & Verification Suite (`examples/`, `tests/verify_bear_anatomy.py`)**:
   - Canonical assets: `examples/Armored_War_Bear_HD.glb` and `examples/Armored_War_Bear_HD.blend`.
   - Automated inspection script `verify_bear_anatomy.py` running in headless Blender 5.2.1 LTS.
   - 4 high-resolution beauty renders saved to disk via Cycles: Front 3/4 perspective, Head close-up, Paw/claw close-up, Full body.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Socket Bridge Dispatch Fix | Fix status check in `blender_bridge.py` line 472 for active Blender session execution | M1 | Survey (Explorer 1) |
| 2 | Procedural Curved Claw Generator | Lofted parabolic arc claw generator ensuring $\vec{d} \cdot \vec{u}_{\text{fwd}} > 0.6$ and $d_z < 0$ | M1 | Survey (Explorer 2) |
| 3 | Plantigrade Paw & Pad System | Anatomical calcaneus heel, plantar/palmar pads, and 5 digital pads per paw | M1 | Survey (Explorer 2) |
| 4 | Articulated Facial Geometry | Cranium, snout, distinct nares/nostrils, mouth cavity, lower jaw, teeth, eyelids, cupped ears | M1 | Survey (Explorer 2) |
| 5 | Anatomical Ursine Torso & Limbs | Muscular quadruped torso, dorsal spine, short tail, 18 standardized vertex groups | M1 | Survey (Explorer 2) |
| 6 | Volumetric Fur Grooming Module | Multi-layer undercoat + guard hairs (>=10,000 parent strands) in `grooming.py` | M2 | Survey (Explorer 3) |
| 7 | Biological Fur Flow & Clumping | Vector field along dorsal spine, gravity deflection, clump factor 0.3-0.5, taper -0.7 | M2 | Survey (Explorer 3) |
| 8 | Curve-to-Mesh glTF Ribbon Evaluator | Converts fur curves to polygon ribbons for glTF 2.0 export compatibility | M2 | Survey (Explorer 1/3) |
| 9 | 5-Slot PBR Shader Engine | Dedicated Principled BSDF v2 shaders for Fur, Skin/Nose, Keratin Claws, Steel, Brass in `materials.py` | M3 | Survey (Explorer 3) |
| 10 | Procedural Non-Intersecting Armor | Shoulders & wrists war armor fitting with radial offset $\Delta r \in [0.02, 0.04]\text{m}$ in `armor.py` | M3 | Survey (Explorer 3) |
| 11 | Master Scene Assembly & .blend Export | Full assembly in active Blender session and saved as `examples/Armored_War_Bear_HD.blend` | M4 | Survey (Explorer 1/3) |
| 12 | Production Asset Export (.glb) | Clean glTF 2.0 export `examples/Armored_War_Bear_HD.glb` with PBR materials and fur ribbons | M4 | Survey (Explorer 1/3) |
| 13 | Automated Inspection Script | Programmatic verification script `verify_bear_anatomy.py` with vector math and topology assertions | M4 | Survey (Explorer 2/3) |
| 14 | Multi-Angle Beauty Rendering Rig | Headless Cycles camera setups for Front 3/4, Head close-up, Paw close-up, Full body | M4 | Survey (Explorer 3) |
| 15 | Pytest Suite Integration | Automated pytest harness executing `tests/test_bear_anatomy.py` asserting 100% pass | M4 | Survey (Explorer 1) |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Reusable Anatomy Generator & Claw Fix | Features 1, 2, 3, 4, 5 in `src/morphomesh/` (`inference_adapter.py`, `blender_bridge.py`) + base bear geometry | none | DONE |
| M2 | Volumetric Fur & Grooming Engine | Features 6, 7, 8 in `src/morphomesh/grooming.py` + hair curves on bear mesh | M1 | DONE |
| M3 | PBR Shader Engine & War Armor Fitting | Features 9, 10 in `src/morphomesh/materials.py`, `armor.py` + shader assignment and fitted armor plates | M1, M2 | DONE |
| M4 | Scene Assembly, Export, Verification & Renders | Features 11, 12, 13, 14, 15: `Armored_War_Bear_HD.blend/.glb`, `verify_bear_anatomy.py`, 4 renders, pytest pass | M1, M2, M3 | IN_PROGRESS |

---

## Interface Contracts

### `MeshGeometry` ↔ `InferenceAdapter`
```python
def add_curved_claw(
    self,
    base_pos: Tuple[float, float, float],
    forward_dir: Tuple[float, float, float] = (0.0, -1.0, 0.0),
    downward_dir: Tuple[float, float, float] = (0.0, 0.0, -1.0),
    length: float = 0.12,
    base_radius: float = 0.025,
    curve_factor: float = 0.45,
    segments: int = 6,
    radial_segments: int = 8,
) -> None:
    """Adds a curved claw guarantee: dot(claw_tip - claw_base, forward_dir) > 0.60 and dz < 0."""

def add_plantigrade_paw(
    self,
    heel_pos: Tuple[float, float, float],
    forward_dir: Tuple[float, float, float] = (0.0, -1.0, 0.0),
    is_front: bool = False,
    scale: float = 1.0,
) -> None:
    """Adds plantigrade foot/paw with calcaneus heel, plantar/palmar pad, and 5 digital pads."""

def add_articulated_head(
    self,
    head_center: Tuple[float, float, float],
    forward_dir: Tuple[float, float, float] = (0.0, -1.0, 0.0),
    scale: float = 1.0,
) -> None:
    """Adds head with cranium, rostrum, indented nares, mouth cavity, jaw, teeth, eyelids, cupped ears."""
```

### `GroomingEngine` ↔ `BlenderBridge` (`src/morphomesh/grooming.py`)
```python
def setup_volumetric_fur(
    mesh_object_name: str,
    undercoat_strands: int = 8000,
    guard_hair_strands: int = 4000,
    flow_vertex_group: str = "dorsal_spine",
    clump_factor: float = 0.4,
    taper_shape: float = -0.7,
) -> Dict[str, Any]:
    """Sets up multi-layer volumetric fur with biological growth flow on target mesh."""

def evaluate_fur_ribbons_for_gltf(
    mesh_object_name: str,
    fur_system_names: List[str],
    max_export_strands: int = 5000,
) -> str:
    """Generates polygonal ribbon mesh for standard glTF export."""
```

### `PbrMaterialEngine` ↔ `BlenderBridge` (`src/morphomesh/materials.py`)
```python
def create_pbr_creature_materials() -> Dict[str, str]:
    """Creates 5 distinct Principled BSDF v2 materials: Fur, Wet_Skin, Claws, Steel_Armor, Brass_Trim."""
```

### `ArmorFittingEngine` ↔ `BlenderBridge` (`src/morphomesh/armor.py`)
```python
def fit_war_armor(
    base_mesh_name: str,
    shoulder_group: str = "armor_mounts_shoulder",
    wrist_group: str = "armor_mounts_wrist",
    clearance_offset: float = 0.025,
) -> List[str]:
    """Generates non-intersecting pauldron, gorget, backplate, and bracer armor meshes."""
```

---

## Code Layout
- `src/morphomesh/inference_adapter.py`: Upgraded `MeshGeometry` & procedural creature synthesis.
- `src/morphomesh/blender_bridge.py`: Socket dispatch fix and bridge execution wrappers.
- `src/morphomesh/grooming.py`: Volumetric fur and hair curve pipeline.
- `src/morphomesh/materials.py`: 4-channel PBR material creation suite.
- `src/morphomesh/armor.py`: Procedural battle-hardened war armor fitting.
- `verify_bear_anatomy.py` (project root): Standalone automated inspection script.
- `tests/test_bear_anatomy.py`: Pytest integration test for claw math, facial landmarks, and fur count.
- `examples/Armored_War_Bear_HD.blend`: Complete master Blender scene.
- `examples/Armored_War_Bear_HD.glb`: Production glTF 2.0 export.
- `docs/renders/`: High-resolution beauty renders.
