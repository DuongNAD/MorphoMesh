# Task Assignment: M1 Worker (Implement Botanical Taxonomy & Catalog Specification)
Working Directory: E:\tool\mcp\MorphoMesh\.agents\m1_worker_1
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\ORIGINAL_REQUEST.md
Project Spec: E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_1\PROJECT.md

## 2026-09-10T05:15:41Z
You are Worker 1 for Milestone 1 (M1: Botanical Taxonomy & Catalog Specification).
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\m1_worker_1
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\ORIGINAL_REQUEST.md
Also refer to:
- Project Specification: E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_1\PROJECT.md
- M1 Explorer 1 Report & Prototype: E:\tool\mcp\MorphoMesh\.agents\m1_explorer_1\handoff.md and E:\tool\mcp\MorphoMesh\.agents\m1_explorer_1\proposed_catalog.py
- M1 Explorer 2 Report & Prompt Improvements: E:\tool\mcp\MorphoMesh\.agents\m1_explorer_2\handoff.md
- M1 Explorer 3 Report & Test Suite: E:\tool\mcp\MorphoMesh\.agents\m1_explorer_3\handoff.md, E:\tool\mcp\MorphoMesh\.agents\m1_explorer_3\proposed_test_catalog.py, E:\tool\mcp\MorphoMesh\.agents\m1_explorer_3\proposed_conftest.py
- Source Catalog Data: E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Exclusive Write Ownership Boundaries:
- teamwork_projects/vegetation_library/vegetation_pipeline/__init__.py
- teamwork_projects/vegetation_library/vegetation_pipeline/taxonomy_catalog.json
- teamwork_projects/vegetation_library/vegetation_pipeline/catalog.py
- teamwork_projects/vegetation_library/tests/__init__.py
- teamwork_projects/vegetation_library/tests/conftest.py
- teamwork_projects/vegetation_library/tests/test_catalog.py

Task:
1. Initialize the package structure:
   - Create `teamwork_projects/vegetation_library/vegetation_pipeline/__init__.py` exposing the catalog API.
   - Copy `E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json` into `teamwork_projects/vegetation_library/vegetation_pipeline/taxonomy_catalog.json`.
   - Incorporate the prompt grounding fixes from M1 Explorer 2 (for Willow, Beech, Spruce, Cypress, Moss, Spanish Moss) and the expanded 56-token universal negative prompt blacklist into `taxonomy_catalog.json`.
2. Implement `teamwork_projects/vegetation_library/vegetation_pipeline/catalog.py`:
   - Implement Pydantic v2 schemas: `DimensionsSpec`, `MorphologySpec`, `MeshyPromptSpec`, `VerificationCriteria`, `PlantSpecies`, `BotanicalCategory`, `VegetationLibraryCatalog`.
   - Ensure all property aliases (`id`/`species_id`, `category`/`category_id`, `prompt`/`positive_prompt`, etc.) are implemented so both PROJECT.md contracts and survey formats work seamlessly.
   - Implement functions: `load_catalog()`, `get_catalog()`, `get_species(identifier)`, `get_species_by_category(category)`, `list_categories()`, `list_species_ids()`.
3. Implement `teamwork_projects/vegetation_library/tests/`:
   - Create `teamwork_projects/vegetation_library/tests/__init__.py`.
   - Create `teamwork_projects/vegetation_library/tests/conftest.py` using `E:\tool\mcp\MorphoMesh\.agents\m1_explorer_3\proposed_conftest.py`.
   - Create `teamwork_projects/vegetation_library/tests/test_catalog.py` using `E:\tool\mcp\MorphoMesh\.agents\m1_explorer_3\proposed_test_catalog.py`.
4. Verification & Testing:
   - Run the test suite: `uv run pytest teamwork_projects/vegetation_library/tests/test_catalog.py -v`.
   - Ensure all tests pass 100% with exit code 0.
5. Delivery:
   - Maintain `progress.md` in your working directory `E:\tool\mcp\MorphoMesh\.agents\m1_worker_1\progress.md`.
   - Write a structured handoff report to `E:\tool\mcp\MorphoMesh\.agents\m1_worker_1\handoff.md` with complete test output, verification evidence, and file listings.
   - Send a completion message back to parent.
