# Project: MorphoMesh Re-architecture, Modularization, and Documentation Suite

## Architecture
MorphoMesh is an autonomous 3D digital content creation pipeline and Blender MCP server. This re-architecture decomposes 11 monolithic modules (>50KB) into cohesive, single-responsibility sub-packages while strictly preserving 100% backward compatibility for all external callers, test suites, FastMCP tools, and the Blender socket bridge.

### Core Subsystems Layout:
1. **Models Subsystem (`src/morphomesh/models/`)**:
   - Decomposes `models.py` (63.8 KB) into `errors.py`, `enums.py`, `base.py`, `creature.py`, `human.py`, `inspection.py`, `critique.py`, `animation.py`.
   - Preserves `src/morphomesh/models.py` as backward-compatible facade re-exporting all 62 classes, 32 error constants, and enums via `__all__`.
2. **Geometry Subsystem (`src/morphomesh/geometry/`)**:
   - Decouples in-memory `MeshGeometry` (1,108 lines) from `inference_adapter.py`.
   - Houses `mesh.py`, `exporters.py` (glTF 2.0 binary, OBJ), `primitives.py`, `quad_utils.py`.
3. **Inference Subsystem (`src/morphomesh/inference/`)**:
   - Houses `base.py`, `mock_adapter.py`, `replicate_adapter.py`, `huggingface_adapter.py`, `factory.py`.
   - Preserves `src/morphomesh/inference_adapter.py` as backward-compatible facade.
4. **Bridge Subsystem (`src/morphomesh/bridge/`)**:
   - Decomposes `blender_bridge.py` (151.5 KB) into `client.py` (TCP/NDJSON transport), `headless.py` (CLI runner & sentinel extraction), `validator.py` (AST BpyCodeValidator), `constants.py`, and `scripts/` (modular Python script templates).
   - Preserves `src/morphomesh/blender_bridge.py` as backward-compatible facade.
5. **Tools Subsystem (`src/morphomesh/tools/`)**:
   - Decomposes `server.py` (71.9 KB) into `creature.py` (7 tools), `human.py` (7 tools), `inspection.py` (3 tools), `animation.py` (2 tools), and `gating.py` (dual-layer environment gating).
   - Preserves `src/morphomesh/server.py` as backward-compatible facade.
6. **Human Subsystem (`src/morphomesh/human/`)**:
   - Decomposes `human_generator.py` (73.6 KB) into `anatomy.py`, `mold_loader.py`, `morphology.py`, `scripts.py`.
   - Preserves `src/morphomesh/human_generator.py` as facade.
7. **Rigging Subsystem (`src/morphomesh/rigging/`)**:
   - Decomposes `human_rigging.py` (82.5 KB) into `metarig.py` (163 DEF bones), `anti_pinch.py`, `blendshapes.py` (52 ARKit FACS), `scripts.py`.
   - Preserves `src/morphomesh/human_rigging.py` as facade.
8. **Wardrobe Subsystem (`src/morphomesh/wardrobe/`)**:
   - Decomposes `wardrobe.py` (88.0 KB) into `garments.py` (bodice, sash, skirt, sandals), `props.py` (strings, butterflies), `skinning.py`, `scripts.py`.
   - Preserves `src/morphomesh/wardrobe.py` as facade.
9. **Grooming Subsystem (`src/morphomesh/grooming/`)**:
   - Decomposes `human_grooming.py` (50.8 KB) into `hime_cut.py` (spline generation), `ribbons.py`, `curves_pipeline.py` (Geometry Nodes), `scripts.py`.
   - Preserves `src/morphomesh/human_grooming.py` as facade.
10. **Assembler Subsystem (`src/morphomesh/assembler/`)**:
    - Decomposes `character_assembler.py` (105.1 KB) into `character_assembler.py`, `pbr_baker.py` (4K texture generation), `scene_builder.py`, `packager.py`.
    - Preserves `src/morphomesh/character_assembler.py` as facade.
11. **Visual Critic Subsystem (`src/morphomesh/critic/`)**:
    - Decomposes `visual_critic.py` (93.1 KB) into `bvh.py` (`PurePythonBVHTree`), `geometry_math.py`, `penetration.py`, `proportions.py`, `deformation.py`, `reporter.py`.
    - Preserves `src/morphomesh/visual_critic.py` as facade.
12. **Documentation & Specification Subsystem (`docs/`)**:
    - `docs/ARCHITECTURE.md`: Complete architecture with Mermaid diagrams.
    - `docs/MCP_SPECIFICATION.md`: Exhaustive FastMCP spec for all 19 tools.
    - `docs/DEVELOPER_GUIDE.md`: Developer guide with setup, testing, and extension patterns.
    - `README.md`: Modernized documentation hub.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | `models/` Sub-Package Decomposition | Split `models.py` into cohesive domain modules with facade re-export | M1 | Survey E1, E2 |
| 2 | `geometry/` Sub-Package Extraction | Extract `MeshGeometry` and glTF/OBJ export from `inference_adapter.py` | M1 | Survey E1 |
| 3 | `inference/` Sub-Package Modularization | Split adapter backends into modular hierarchy with facade re-export | M1 | Survey E1 |
| 4 | Core Test Failure Remediation | Fix template string bug in `blender_bridge.py:693` (`test_anatomy.py:528`) | M1 | Survey E3 |
| 5 | `bridge/` Sub-Package Modularization | Split `blender_bridge.py` into transport, headless, AST validator, scripts | M2 | Survey E1, E2 |
| 6 | `tools/` Sub-Package Modularization | Split `server.py` into creature, human, inspection, animation, gating | M2 | Survey E1, E2 |
| 7 | FastMCP Tool Compatibility & Gating | Maintain 100% parameter, return schema, and dual-layer gating invariance | M2 | Survey E2 |
| 8 | Blender Socket IPC Protocol Parity | Maintain NDJSON framing, port 9876, 20 RPC commands, timer immortality | M2 | Survey E2 |
| 9 | `human/` Sub-Package Modularization | Split `human_generator.py` into mold loader, morphology, vertex groups | M3 | Survey E1 |
| 10 | `rigging/` Sub-Package Modularization | Split `human_rigging.py` into 163 DEF metarig, anti-pinch, 52 blendshapes | M3 | Survey E1 |
| 11 | `wardrobe/` Sub-Package Modularization | Split `wardrobe.py` into garments (dress/sandals), props (strings/butterflies) | M3 | Survey E1 |
| 12 | `grooming/` Sub-Package Modularization | Split `human_grooming.py` into splines, ribbons, Geometry Nodes tree | M3 | Survey E1 |
| 13 | `assembler/` Sub-Package Modularization | Split `character_assembler.py` into master assembler, 4K PBR baker, scene | M4 | Survey E1 |
| 14 | `critic/` Sub-Package Modularization | Split `visual_critic.py` into BVH tree, math utils, 4 defect analyzers | M4 | Survey E1 |
| 15 | System Architecture Document | Produce `docs/ARCHITECTURE.md` with comprehensive Mermaid diagrams | M5 | Survey E3 |
| 16 | FastMCP Specification Document | Produce `docs/MCP_SPECIFICATION.md` detailing all 19 tools and schemas | M5 | Survey E2, E3 |
| 17 | Developer Guide Document | Author `docs/DEVELOPER_GUIDE.md` covering setup, testing, extension patterns | M5 | Survey E3 |
| 18 | Modernized README.md | Update `README.md` with complete directory tree, tool table, CLI examples | M5 | Survey E3 |
| 19 | Public API Docstrings & PEP 484 Types | Ensure 100% public functions/classes have Google docstrings and types | M5 | Requirements |
| 20 | Packaging & Build Verification | Verify `python -m build` and `pip install -e .` without warnings | M5 | Requirements |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Foundation: Models, Geometry & Inference Subsystems | Modularize `models.py` into `models/`, extract `geometry/` and `inference/` from `inference_adapter.py`, fix `blender_bridge.py:693` bug, verify facade imports | None | DONE |
| M2 | Blender Socket Bridge & FastMCP Tools Subsystems | Modularize `blender_bridge.py` into `bridge/`, modularize `server.py` into `tools/`, verify 19 tools, gating matrix, and socket parity | M1 | DONE |
| M3 | Digital Human, Rigging, Wardrobe & Grooming Subsystems | Modularize `human_generator.py` into `human/`, `human_rigging.py` into `rigging/`, `wardrobe.py` into `wardrobe/`, `human_grooming.py` into `grooming/`, preserve facades | M1 | DONE |
| M4 | Character Assembler & Visual Quality Critic Subsystems | Modularize `character_assembler.py` into `assembler/`, `visual_critic.py` into `critic/`, preserve facades | M1, M2, M3 | DONE |
| M5 | Documentation Suite, Docstrings & Final Verification | Complete `docs/ARCHITECTURE.md`, `docs/MCP_SPECIFICATION.md`, `docs/DEVELOPER_GUIDE.md`, `README.md`, full docstrings, 100% test pass, build verification | M4 | DONE |

---

## Code Layout
- `src/morphomesh/models/` (New sub-package): Domain-partitioned Pydantic schemas, errors, enums.
- `src/morphomesh/models.py` (Facade): Re-exports all symbols from `morphomesh.models`.
- `src/morphomesh/geometry/` (New sub-package): `MeshGeometry`, glTF 2.0 binary & OBJ exporters, quad math.
- `src/morphomesh/inference/` (New sub-package): Mock, Replicate, HuggingFace adapters, factory.
- `src/morphomesh/inference_adapter.py` (Facade): Re-exports all symbols from `morphomesh.inference` and `geometry`.
- `src/morphomesh/bridge/` (New sub-package): Client transport, NDJSON streaming, AST validator, headless runner, domain scripts.
- `src/morphomesh/blender_bridge.py` (Facade): Re-exports all symbols from `morphomesh.bridge`.
- `src/morphomesh/tools/` (New sub-package): Creature, Human, Inspection, Animation tools, gating logic.
- `src/morphomesh/server.py` (Facade): FastMCP server instance, tool registrations, gating wrappers, re-exports.
- `src/morphomesh/human/` (New sub-package): MakeHuman base mold loader, morphology, vertex groups, scripts.
- `src/morphomesh/human_generator.py` (Facade): Re-exports all symbols from `morphomesh.human`.
- `src/morphomesh/rigging/` (New sub-package): 163 DEF metarig, anti-pinch weights, 52 ARKit blendshapes.
- `src/morphomesh/human_rigging.py` (Facade): Re-exports all symbols from `morphomesh.rigging`.
- `src/morphomesh/wardrobe/` (New sub-package): Sundress, bodice, sash, sandals, props, skinning.
- `src/morphomesh/wardrobe.py` (Facade): Re-exports all symbols from `morphomesh.wardrobe`.
- `src/morphomesh/grooming/` (New sub-package): Hime cut splines, ribbons, Geometry Nodes hair tree.
- `src/morphomesh/human_grooming.py` (Facade): Re-exports all symbols from `morphomesh.grooming`.
- `src/morphomesh/assembler/` (New sub-package): YuNianAn master assembler, 4K PBR texture baker, packaging.
- `src/morphomesh/character_assembler.py` (Facade): Re-exports all symbols from `morphomesh.assembler`.
- `src/morphomesh/critic/` (New sub-package): PurePythonBVHTree, vector algebra, 4 defect evaluators.
- `src/morphomesh/visual_critic.py` (Facade): Re-exports all symbols from `morphomesh.critic`.
- `docs/ARCHITECTURE.md`: Architecture diagrams and pipeline flow.
- `docs/MCP_SPECIFICATION.md`: FastMCP tool documentation.
- `docs/DEVELOPER_GUIDE.md`: Developer guide.
- `README.md`: Master project documentation.
