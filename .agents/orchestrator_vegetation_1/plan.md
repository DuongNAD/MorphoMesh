# Execution Plan — Vegetation Library Project

## Objective
Build an automated generation pipeline and high-fidelity 3D botanical asset library using Meshy AI Text-to-3D, producing 30+ diverse, unrigged plant species across >= 6 major categories with complete PBR materials, clean quad/triangle topology, correct pivot, and 100% automated verification.

## Step-by-Step Milestones

### Phase 0: Survey & Scope Mapping
- Dispatch 3 Explorers:
  1. Explorer 1: Inspect MorphoMesh repository, Meshy API clients, Blender bridge, and environment setup.
  2. Explorer 2: Survey botanical taxonomy requirements, biome categories, prompt engineering, and catalog structure for 30+ species.
  3. Explorer 3: Survey 3D processing pipelines (mesh cleanup, unrigged guarantee, pivot normalization, PBR texture packing, GLB/OBJ export, and headless preview rendering).
- Synthesize survey findings into `PROJECT.md`.

### Phase 1: M1 - Botanical Taxonomy & Catalog Specification
- Define 30+ distinct species across 7 biomes/categories.
- Complete JSON/Python taxonomy specification with morphological traits, real-world metric dimensions, and tuned Meshy prompts.

### Phase 2: M2 - Meshy AI Generation Engine & Deterministic Fallback Harness
- Implement robust Meshy Text-to-3D generator with retry, polling, rate limiting, and PBR extraction.
- Implement high-fidelity offline deterministic botanical mesh generator fallback ensuring complete independence from transient API failures or rate limits.

### Phase 3: M3 - Post-Processing, Normalization & Multi-Format Export
- Implement pivot ground snapping (Z_min = 0).
- Scale normalization to metric units.
- Clean topology verification (3,000 - 45,000 vertices).
- Dual export to production GLB and OBJ/MTL.

### Phase 4: M4 - Automated Inspection Suite & Preview Visuals
- Geometry integrity validator (no NaNs/Infs, valid normals, manifold).
- Strict zero-armature / zero-bone / zero-skinning validator.
- PBR texture validator (valid dimensions, non-empty, non-black).
- Multi-angle turntable / thumbnail render generator.

### Phase 5: M5 - Full Asset Generation & End-to-End Verification
- Run full batch generation across all 30+ species.
- Execute automated inspection suite with 100% pass rate.
- Generate contact sheets, catalog documentation, and visual showcase.
- Forensic integrity audit and victory claim.
