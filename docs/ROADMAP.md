# MorphoMesh: Engineering & Research Roadmap

**Document ID**: `MM-R3-ROAD-001`  
**Milestone**: M3 (MCP Server Specification & Architecture Roadmap)  
**Author**: MorphoMesh Core Protocol & Architecture Team  
**Date**: September 2026  
**Status**: Authoritative Strategic Plan / Engineering Roadmap  
**Target Architecture**: Hybrid macOS Apple Silicon Client + Remote Linux GPU Compute + Blender 5.2.1 LTS  
**Repository Path**: `docs/ROADMAP.md`  

---

## Table of Contents

1. [Executive Summary & Strategic Vision](#1-executive-summary--strategic-vision)
   - [1.1 Strategic Mission](#11-strategic-mission)
   - [1.2 Global Phased Timeline & Milestones](#12-global-phased-timeline--milestones)
   - [1.3 Core Engineering Principles](#13-core-engineering-principles)
2. [Phase 1: Runnable PoC & Mock Pipeline Foundation (Current Scope — Month 1)](#2-phase-1-runnable-poc--mock-pipeline-foundation-current-scope--month-1)
   - [2.1 Strategic Objective](#21-strategic-objective)
   - [2.2 Detailed Work Breakdown Structure (WBS)](#22-detailed-work-breakdown-structure-wbs)
   - [2.3 Deliverables & Artifacts](#23-deliverables--artifacts)
   - [2.4 Technical Dependencies & Prerequisites](#24-technical-dependencies--prerequisites)
   - [2.5 Timeline & Sprint Schedule](#25-timeline--sprint-schedule)
   - [2.6 Risk Management & Fallback Strategy](#26-risk-management--fallback-strategy)
   - [2.7 Key Performance Indicators (KPIs)](#27-key-performance-indicators-kpis)
3. [Phase 2: Remote GPU AI Inference & Cloud Adapter Tier (Month 2 — Month 3)](#3-phase-2-remote-gpu-ai-inference--cloud-adapter-tier-month-2--month-3)
   - [3.1 Strategic Objective](#31-strategic-objective)
   - [3.2 Detailed Work Breakdown Structure (WBS)](#32-detailed-work-breakdown-structure-wbs)
   - [3.3 Deliverables & Artifacts](#33-deliverables--artifacts)
   - [3.4 Technical Dependencies & Cloud Infrastructure](#34-technical-dependencies--cloud-infrastructure)
   - [3.5 Timeline & Sprint Schedule](#35-timeline--sprint-schedule)
   - [3.6 Risk Management & Fallback Strategy](#36-risk-management--fallback-strategy)
   - [3.7 Key Performance Indicators (KPIs)](#37-key-performance-indicators-kpis)
4. [Phase 3: Advanced Topology & Biomechanical Rigging Engine (Month 4 — Month 5)](#4-phase-3-advanced-topology--biomechanical-rigging-engine-month-4--month-5)
   - [4.1 Strategic Objective](#41-strategic-objective)
   - [4.2 Detailed Work Breakdown Structure (WBS)](#42-detailed-work-breakdown-structure-wbs)
   - [4.3 Deliverables & Artifacts](#43-deliverables--artifacts)
   - [4.4 Technical Dependencies & Model Weights](#44-technical-dependencies--model-weights)
   - [4.5 Timeline & Sprint Schedule](#45-timeline--sprint-schedule)
   - [4.6 Risk Management & Fallback Strategy](#46-risk-management--fallback-strategy)
   - [4.7 Key Performance Indicators (KPIs)](#47-key-performance-indicators-kpis)
5. [Phase 4: Production Hardening & Interactive Blender Studio Addon (Month 6+)](#5-phase-4-production-hardening--interactive-blender-studio-addon-month-6)
   - [5.1 Strategic Objective](#51-strategic-objective)
   - [5.2 Detailed Work Breakdown Structure (WBS)](#52-detailed-work-breakdown-structure-wbs)
   - [5.3 Deliverables & Artifacts](#53-deliverables--artifacts)
   - [5.4 Technical Dependencies & Integration Boundaries](#54-technical-dependencies--integration-boundaries)
   - [5.5 Timeline & Sprint Schedule](#55-timeline--sprint-schedule)
   - [5.6 Risk Management & Fallback Strategy](#56-risk-management--fallback-strategy)
   - [5.7 Key Performance Indicators (KPIs)](#57-key-performance-indicators-kpis)
6. [Cross-Phase Engineering & Operational Governance](#6-cross-phase-engineering--operational-governance)
   - [6.1 Computing Hardware & VRAM Allocation Matrix](#61-computing-hardware--vram-allocation-matrix)
   - [6.2 Cloud Infrastructure & API Cost Projections](#62-cloud-infrastructure--api-cost-projections)
   - [6.3 Security Auditing & Continuous Penetration Testing](#63-security-auditing--continuous-penetration-testing)
   - [6.4 Semantic Versioning & Release Governance](#64-semantic-versioning--release-governance)

---

## 1. Executive Summary & Strategic Vision

### 1.1 Strategic Mission

**MorphoMesh** bridges **Google Antigravity 2.0** with **Blender 5.2.1 LTS**, delivering an autonomous, end-to-end procedural and generative digital content creation (DCC) studio specialized in 3D creature and animal generation:

$$\text{Natural Language Prompt} \xrightarrow{\text{AI Orchestration}} \text{Production-Ready, Rigged, Textured 3D Creature in Blender}$$

Standard generative 3D models fail on biological organisms because creatures exhibit variable genus ($g \in [0, 12+]$), radical anatomical diversity (digitigrade felines, unguligrade equines, plantigrade primates, multi-segmented chimeras), and complex appendages (wings, horns, tails). MorphoMesh addresses this via an end-to-end orchestrated pipeline structured into a **Hybrid Computing Topology**:
- **Client & Coordination Layer (macOS Apple Silicon)**: Ultra-responsive local Python 3.11+ / FastMCP 1.28.1 server, Pydantic v2 validation, session state management, and two-tier AST security sandbox.
- **Blender Communication Layer (macOS Localhost IPC)**: High-speed dual-mode communication bridge (Localhost TCP socket on port `9876` and Headless CLI runner) driving Blender 5.2.1 LTS with Apple Metal GPU viewport rendering.
- **AI Inference Layer (Hybrid Tiered Engine)**: Pluggable strategy adapters enabling deterministic zero-VRAM offline testing (`MockInferenceAdapter`), local Apple Silicon fallbacks (`rembg` / `BiRefNet` via CoreML), and remote Linux GPU cloud clusters (NVIDIA RTX 4090 / A10G / A100) running heavy 3D diffusion backbones (TRELLIS.2 4B, Hunyuan3D-2.1) and neural retopology (MeshAnything V2).

---

### 1.2 Global Phased Timeline & Milestones

The roadmap spans four sequential phases transitioning from foundational PoC to an enterprise-grade multi-agent studio:

```
2026
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ MONTH 1            │ MONTH 2 - 3         │ MONTH 4 - 5         │ MONTH 6+                       │
├────────────────────┼─────────────────────┼─────────────────────┼────────────────────────────────┤
│ PHASE 1:           │ PHASE 2:            │ PHASE 3:            │ PHASE 4:                       │
│ Runnable PoC &     │ Remote Cloud GPU    │ Advanced Topology   │ Production Hardening &         │
│ Mock Pipeline      │ Inference Tier      │ & Biomechanical Rig │ Interactive Blender Addon      │
├────────────────────┼─────────────────────┼─────────────────────┼────────────────────────────────┤
│ • FastMCP 7 Tools  │ • Replicate/HF APIs │ • MeshAnything V2   │ • Live TCP Addon (Port 9876)   │
│ • Headless Bridge  │ • TRELLIS.2 4B Mesh │ • QuadriFlow Crease │ • Real-Time Metal Viewport     │
│ • Mock Adapter     │ • Hunyuan3D-2.1     │ • Landmark Detector │ • Multi-Agent Orchestration    │
│ • AST Validator    │ • PBR Texture Bake  │ • Rigify Metarigs   │ • Procedural Motion Library    │
│ • 100% Pytest Pass │ • Apple Silicon MPS │ • Auto Heat Weight  │ • Blender Extensions Platform  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Master Phase Overview
| Phase | Focus Area | Primary Deliverables | Target Environment | Exit Gate |
|---|---|---|---|---|
| **Phase 1** (M1) | Foundation & Architecture | FastMCP Server, Headless Bridge, Mock Adapter, AST Guard, Pytest Suite | macOS Apple Silicon (Darwin ARM64) | 100% Passing Tests (`pytest -v tests/`), zero network dependencies. |
| **Phase 2** (M2–M3) | Cloud GPU Inference | Remote GPU Adapters (Replicate/HF), TRELLIS.2 4B, Hunyuan3D-2.1, PBR Atlas Baking | Linux x86_64 / NVIDIA CUDA 12.x + macOS Client | Photorealistic GLB generation < 60s with 4 PBR texture maps. |
| **Phase 3** (M4–M5) | Topology & Rigging | MeshAnything V2 Retopo, QuadriFlow Symmetry, Anatomical Landmark Detection, Rigify Metarigs | Cloud GPU (MeshAnything) + Local Blender 5.2.1 | Clean quad mesh (< 15k faces, > 90% quads) rigged with 100% skinning success. |
| **Phase 4** (M6+) | Production Studio & Addon | Interactive Blender Addon (N-Panel), Localhost Socket (Port 9876), Multi-Agent Coordination | Interactive Blender 5.2.1 GUI (macOS & Linux) | Sub-second viewport feedback, multi-agent director approval loop, extension packaging. |

---

### 1.3 Core Engineering Principles

1. **Zero-VRAM Developer Parity**: Every tool, module, and dataflow must run in 100% offline mock mode on commodity workstations without requiring local CUDA hardware or external cloud API credits.
2. **Strict Protocol Compliance**: All external interfaces adhere strictly to Model Context Protocol (MCP 2024-11-05), JSON-RPC 2.0, and Pydantic v2 schemas.
3. **Defense-in-Depth Security**: Autonomous agent execution inside Blender is constrained by two-tier AST static analysis (`BpyCodeValidator`), timeouts, process isolation, and environment variable scrubbing.
4. **Resilient Failure Recovery**: When cloud endpoints timeout, solvers diverge, or bone heat weights fail, the pipeline automatically recovers via deterministic local fallbacks without aborting the agent workflow.

---

## 2. Phase 1: Runnable PoC & Mock Pipeline Foundation (Current Scope — Month 1)

### 2.1 Strategic Objective
Deliver an end-to-end, runnable Proof-of-Concept (PoC) establishing the complete client, bridge, and mock inference layers. Provide 100% test coverage with automated unit, integration, and security verification on macOS Apple Silicon without external network or GPU dependencies.

---

### 2.2 Detailed Work Breakdown Structure (WBS)

```
PHASE 1 WORK BREAKDOWN STRUCTURE
├── 1.1 FastMCP Server & Protocol Gateway (src/morphomesh/server.py)
│   ├── 1.1.1 FastMCP instance instantiation and lifespan configuration
│   ├── 1.1.2 Registration of all 7 core tools with top-level keyword parameter signatures
│   ├── 1.1.3 Pydantic v2 request model validation and error normalization
│   ├── 1.1.4 FastMCP Context integration for progress streaming and diagnostics
│   └── 1.1.5 Dual transport support (stdio pipe and SSE server)
├── 1.2 Deterministic Mock Inference Engine (src/morphomesh/inference_adapter.py)
│   ├── 1.2.1 BaseInferenceAdapter abstract interface definition
│   ├── 1.2.2 Mock 2D concept generation producing valid PNG buffers with metadata
│   ├── 1.2.3 Procedural 3D mesh generator producing valid binary glTF (.glb) assets
│   ├── 1.2.4 Procedural PBR texture atlas synthesis (Albedo, Normal, Roughness, Metal)
│   ├── 1.2.5 Mock mesh decimation conforming to target polycount budgets
│   └── 1.2.6 Mock skeletal hierarchy synthesizer with vertex weight groups
├── 1.3 Dual-Mode Blender Communication Bridge (src/morphomesh/blender_bridge.py)
│   ├── 1.3.1 Headless CLI runner launching Blender with sentinel serialization tokens
│   ├── 1.3.2 Localhost TCP socket client with auto-reconnection and timeout handlers
│   ├── 1.3.3 Two-tier AST static analysis code validator (BpyCodeValidator)
│   ├── 1.3.4 Automatic engine normalization ('BLENDER_EEVEE_NEXT' -> 'BLENDER_EEVEE')
│   └── 1.3.5 Procedural studio camera auto-spawner and framing solver
├── 1.4 Starter Blender Addon Template (blender_addon/morphomesh/)
│   ├── 1.4.1 Modular package layout (__init__.py, operators, panels, preferences)
│   ├── 1.4.2 Threaded socket listener server on 127.0.0.1:9876 (server_listener.py)
│   ├── 1.4.3 Non-blocking bpy.app.timers queue consumer on Blender main thread
│   └── 1.4.4 Standalone addon packaging script (package_addon.py)
├── 1.5 Automated Verification & Test Suite (tests/)
│   ├── 1.5.1 Conftest fixtures (event loops, mock servers, temporary cache, sample meshes)
│   ├── 1.5.2 Tool schema & registration tests (test_tools_schema.py)
│   ├── 1.5.3 Inference adapter unit tests (test_inference_adapter.py)
│   ├── 1.5.4 Blender bridge & AST security tests (test_blender_bridge.py)
│   └── 1.5.5 End-to-end 5-stage offline pipeline tests (test_e2e_offline.py)
└── 1.6 Documentation & Developer Enablement
    ├── 1.6.1 Master Architectural Standard (docs/ARCHITECTURE.md)
    ├── 1.6.2 State-of-the-Art Research Benchmark (docs/RESEARCH_BENCHMARK.md)
    ├── 1.6.3 Authoritative MCP Specification (docs/MCP_SPECIFICATION.md)
    ├── 1.6.4 Engineering & Research Roadmap (docs/ROADMAP.md)
    └── 1.6.5 Project Overview & Setup Guides (README.md, SETUP_GUIDE.md)
```

---

### 2.3 Deliverables & Artifacts
1. `src/morphomesh/server.py`: Complete FastMCP server exposing 7 tools with Pydantic v2 models.
2. `src/morphomesh/blender_bridge.py`: Headless CLI runner, TCP client, and AST security engine.
3. `src/morphomesh/inference_adapter.py`: Deterministic mock adapter producing valid PNGs, GLBs, and rigs.
4. `blender_addon/morphomesh/`: Starter Blender addon with threaded listener and `bpy.app.timers`.
5. `tests/`: 4 test modules with 100% passing tests under `pytest -v tests/`.
6. Complete publication-grade documentation suite in `docs/`.

---

### 2.4 Technical Dependencies & Prerequisites
- **Host OS**: macOS 14.x+ Sonoma / Darwin ARM64 (Apple Silicon M1/M2/M3/M4).
- **Python**: Python 3.11.8+ (`mcp` 1.28.1, `pydantic` 2.13.4, `pytest` 9.1.1, `pytest-asyncio` 1.4.0).
- **Blender**: Blender 5.2.1 LTS installed at `/Applications/Blender.app/Contents/MacOS/Blender`.

---

### 2.5 Timeline & Sprint Schedule
- **Sprint 1.1 (Days 1–5)**: Architecture research, benchmark analysis, and MCP tool specification.
- **Sprint 1.2 (Days 6–10)**: FastMCP server implementation, Pydantic models, and mock inference engine.
- **Sprint 1.3 (Days 11–15)**: Blender headless bridge, AST security guard, and starter addon.
- **Sprint 1.4 (Days 16–20)**: Comprehensive test suite construction and CI/CD validation.

---

### 2.6 Risk Management & Fallback Strategy
| Risk Event | Likelihood | Impact | Mitigation Strategy | Fallback Protocol |
|---|---|---|---|---|
| Blender not installed on test runner | Medium | High | Decouple test execution via mock bridge mode. | Headless runner detects missing binary and returns structured mock response. |
| FastMCP argument nesting issues | Low | High | Declare tools with unpacked keyword arguments. | Validate generated schema via `test_tools_schema.py`. |
| Script injection via custom `bpy` | High | Critical | Enforce two-tier AST static validation. | Hard block on forbidden modules (`os`, `subprocess`) before transmission. |

---

### 2.7 Key Performance Indicators (KPIs)
- **Test Pass Rate**: 100% of test cases pass with exit code 0 (`pytest -v tests/`).
- **Cold Startup Time**: FastMCP server initial handshake < 350 ms.
- **Mock Generation Latency**: Complete 5-stage offline mock generation < 3.5 seconds.
- **AST Security Rejection Rate**: 100% interception of malicious test payloads (`import os`, `eval()`).

---

## 3. Phase 2: Remote GPU AI Inference & Cloud Adapter Tier (Month 2 — Month 3)

### 3.1 Strategic Objective
Connect production-grade generative 3D neural networks (Microsoft TRELLIS.2 4B, Tencent Hunyuan3D-2.1) and 2D concept models (FLUX.1-schnell / SD-XL) hosted on remote Linux GPU infrastructure (Replicate API, Hugging Face Inference Endpoints, and custom Linux GPU servers), providing photorealistic 3D creature synthesis with full PBR textures.

---

### 3.2 Detailed Work Breakdown Structure (WBS)

```
PHASE 2 WORK BREAKDOWN STRUCTURE
├── 2.1 Cloud API Client Adapters (src/morphomesh/adapters/)
│   ├── 2.1.1 ReplicateInferenceAdapter supporting TRELLIS.2 and FLUX.1 models
│   ├── 2.1.2 HuggingFaceInferenceAdapter connecting to dedicated Inference Endpoints
│   ├── 2.1.3 CustomLinuxServerAdapter utilizing gRPC / HTTP2 for on-premise clusters
│   └── 2.1.4 Exponential backoff retry engine with full jitter and circuit breakers
├── 2.2 Stage 1 Concept Art Generation Engine
│   ├── 2.2.1 Anatomical conditioning prompt expansion for 8 creature archetypes
│   ├── 2.2.2 Negative prompt injection suppressing artifacts, humanoids, and text
│   ├── 2.2.3 Multi-view concept generation (orthographic front, side, and 3/4 profiles)
│   └── 2.2.4 LoRA adapter support for specific creature styles (Dark Fantasy, Stylized)
├── 2.3 Automated Foreground Segmentation Tier
│   ├── 2.3.1 Local ONNX Runtime / CoreML Rembg integration on Apple Silicon
│   ├── 2.3.2 BiRefNet high-resolution alpha matte boundary refinement
│   └── 2.3.3 Edge feathering and despill filters eliminating fringe artifacts
├── 2.4 Stage 2 Single-Image to 3D Generative Backbone
│   ├── 2.4.1 TRELLIS.2 (4B O-Voxel) cloud deployment and tensor streaming
│   ├── 2.4.2 Hunyuan3D-2.1 rectified flow transformer integration
│   ├── 2.4.3 Isosurface extraction via Marching Tetrahedra / FlexiCubes
│   └── 2.4.4 Binary glTF (.glb) asset assembly and packaging
├── 2.5 High-Resolution PBR Material Parameterization
│   ├── 2.5.1 Tangent-space Normal map baking encoding micro-geometric details
│   ├── 2.5.2 Roughness map estimation separating wet vs. dry organic surfaces
│   ├── 2.5.3 Metallic/chitinous mask classification for armored creatures
│   └── 2.5.4 2048x2048 square texture atlas baking and UV pack optimization
├── 2.6 Local Apple Silicon Fallback Engine
│   ├── 2.6.1 TripoSR local inference via PyTorch Metal Performance Shaders (MPS)
│   ├── 2.6.2 Stable Fast 3D CoreML conversion and execution
│   └── 2.6.3 Zero-cost offline fallback when cloud budgets or networks are exhausted
└── 2.7 FastMCP Asynchronous Polling & Progress Streaming
    ├── 2.7.1 Webhook listener receiver for asynchronous cloud completion tokens
    ├── 2.7.2 Real-time progress percentage streaming via FastMCP Context
    └── 2.7.3 Graceful client cancellation propagating SIGINT to cloud jobs
```

---

### 3.3 Deliverables & Artifacts
1. `src/morphomesh/adapters/replicate_adapter.py`: Production Replicate client.
2. `src/morphomesh/adapters/huggingface_adapter.py`: Dedicated HF Inference Endpoint client.
3. `src/morphomesh/adapters/local_mps_adapter.py`: Local TripoSR runner accelerated via Apple Metal.
4. `src/morphomesh/preprocessors/segmentation.py`: CoreML/ONNX background isolation engine.
5. Live configuration schemas supporting remote endpoint credentials and model selection.

---

### 3.4 Technical Dependencies & Cloud Infrastructure
- **Cloud Hardware**: Dedicated NVIDIA A10G (24GB VRAM) or RTX 4090 for TRELLIS / Hunyuan3D.
- **CUDA Runtime**: Linux x86_64, CUDA 12.1+, PyTorch 2.4+, `spconv-cu120`, `nvdiffrast`.
- **API Credentials**: Replicate API Token (`REPLICATE_API_TOKEN`) or Hugging Face Hub Token (`HF_TOKEN`).

---

### 3.5 Timeline & Sprint Schedule
- **Sprint 2.1 (Weeks 5–6)**: Cloud adapter interfaces, authentication, and background removal tier.
- **Sprint 2.2 (Weeks 7–8)**: TRELLIS.2 and Hunyuan3D-2.1 cloud deployment and GLB extraction.
- **Sprint 2.3 (Weeks 9–10)**: PBR texture baking, normal map generation, and Apple Silicon MPS fallback.
- **Sprint 2.4 (Weeks 11–12)**: Asynchronous polling, webhook endpoints, and circuit breaker stress testing.

---

### 3.6 Risk Management & Fallback Strategy
| Risk Event | Likelihood | Impact | Mitigation Strategy | Fallback Protocol |
|---|---|---|---|---|
| Cloud GPU Out-of-Memory (OOM) | Medium | High | Dynamic texture resolution downscaling (2048 to 1024). | Switch to serverless burst instances or local TripoSR MPS. |
| Remote API Rate Limiting / 429 | High | Medium | Implement token bucket rate limiting and exponential backoff. | Fall back to alternative provider (Replicate -> HF -> Mock). |
| Cloud Service Cold Start Latency | High | Low | Provision warm standby instances or display progress bar. | Stream periodic progress heartbeats to agent via FastMCP Context. |

---

### 3.7 Key Performance Indicators (KPIs)
- **3D Reconstruction Latency**: Complete cloud mesh generation < 60 seconds.
- **Geometric Fidelity**: Extracted mesh contains > 150,000 polygons with clean watertight boundaries.
- **Texture Completeness**: 100% of generated assets output all 4 PBR channels (Albedo, Normal, Roughness, Metal).
- **Network Resilience**: Circuit breaker trips correctly after 3 failures; 0 unhandled network exceptions.

---

## 4. Phase 3: Advanced Topology & Biomechanical Rigging Engine (Month 4 — Month 5)

### 4.1 Strategic Objective
Transform raw generative 3D meshes into production animation-ready assets. Implement automated quad-dominant retopology (MeshAnything V2 and Blender QuadriFlow), automatic 3D anatomical landmark detection, adaptive Rigify creature metarigs across 8 archetypes, and biharmonic skin weighting with geodesic distance fallback.

---

### 4.2 Detailed Work Breakdown Structure (WBS)

```
PHASE 3 WORK BREAKDOWN STRUCTURE
├── 3.1 Neural Autoregressive Retopology Engine (MeshAnything V2)
│   ├── 3.1.1 Cloud containerization of MeshAnything V2 with FlashAttention-3
│   ├── 3.1.2 Autoregressive tokenization of high-density creature meshes
│   ├── 3.1.3 Extraction of pure quad topologies conforming to strict edge flow
│   └── 3.1.4 Preservation of organic curvature along spines, limbs, and joints
├── 3.2 Native Blender QuadriFlow Enhancement Engine
│   ├── 3.2.1 Automated pre-cleaning pass dissolving zero-area and non-manifold faces
│   ├── 3.2.2 Bilateral X-axis symmetry constraint enforcement for limbs and horns
│   ├── 3.2.3 Sharp feature edge angle preservation (preserving teeth, claws, scales)
│   └── 3.2.4 Polycount budget adaptive targeting ([5,000, 15,000] face range)
├── 3.3 Conformal UV Unwrapping & Detail Transfer
│   ├── 3.3.1 Angle-Based Flattening (ABF) seam generation along ventral line
│   ├── 3.3.2 Non-overlapping UV island packing with 0.02 margin padding
│   └── 3.3.3 Tangent-space normal map baking from high-poly mesh onto low-poly UVs
├── 3.4 3D Anatomical Landmark Detection Engine
│   ├── 3.4.1 Principal Component Analysis (PCA) longitudinal spinal alignment
│   ├── 3.4.2 Volumetric cross-sectional slicing detecting head, neck, and tail
│   ├── 3.4.3 K-Means spatial clustering identifying 4-limb contact points
│   └── 3.4.4 Specialized landmark locators for avian wings and serpentine segments
├── 3.5 Rigify Modular Creature Metarig Synthesizer
│   ├── 3.5.1 Archetype mapping: Quadruped, Biped, Winged, Serpentine, Avian, Arachnid
│   ├── 3.5.2 Automated joint positioning and bone roll recalculation
│   ├── 3.5.3 Inverse Kinematics (IK) and Forward Kinematics (FK) controller setup
│   └── 3.5.4 SMAL 35-joint bone translation dictionary integration
├── 3.6 Biomechanical Skin Weighting & Deformation Solver
│   ├── 3.6.1 Automated biharmonic heat diffusion weighting execution
│   ├── 3.6.2 Non-manifold geometry trap handling with harmonic distance fallback
│   ├── 3.6.3 Geodesic voxel skinning pass for thin membranes and wing surfaces
│   └── 3.6.4 Vertex weight group smoothing and normalization across bone chains
└── 3.7 Procedural Test Motion & Action Library
    ├── 3.7.1 Quadruped natural walk and trot cycle action synthesis
    ├── 3.7.2 Wing flap and soaring canopy deformation actions
    ├── 3.7.3 Idle tail swish and breathing chest expansion procedural modifiers
    └── 3.7.4 Automated action binding for immediate agent visual verification
```

---

### 4.3 Deliverables & Artifacts
1. `src/morphomesh/topology/meshanything_client.py`: MeshAnything V2 cloud client.
2. `src/morphomesh/topology/quadriflow_optimizer.py`: Enhanced Blender QuadriFlow remesher.
3. `src/morphomesh/rigging/landmark_detector.py`: 3D morphological landmark detection engine.
4. `src/morphomesh/rigging/metarig_builder.py`: Rigify creature metarig synthesizer.
5. `src/morphomesh/rigging/skinning_solver.py`: Biharmonic and geodesic skinning engine.
6. Procedural motion library containing standard test actions (`.blend` format).

---

### 4.4 Technical Dependencies & Model Weights
- **Model Weights**: MeshAnything V2 (approx. 2.2B parameters) deployed on remote CUDA node.
- **Blender Addons**: Blender native `rigify` addon (auto-enabled via script).
- **Libraries**: `scikit-learn` / `scipy` for PCA and spatial clustering in landmark detection.

---

### 4.5 Timeline & Sprint Schedule
- **Sprint 3.1 (Weeks 13–14)**: Native QuadriFlow optimization, symmetry enforcement, and UV baking.
- **Sprint 3.2 (Weeks 15–16)**: MeshAnything V2 cloud retopology integration and evaluation.
- **Sprint 3.3 (Weeks 17–18)**: Morphological landmark detection algorithms for 8 creature archetypes.
- **Sprint 3.4 (Weeks 19–20)**: Rigify metarig synthesis, biharmonic skinning, and test motion actions.

---

### 4.6 Risk Management & Fallback Strategy
| Risk Event | Likelihood | Impact | Mitigation Strategy | Fallback Protocol |
|---|---|---|---|---|
| Bone Heat Weighting Non-Convergence | High | High | Pre-weld non-manifold vertices; clamp proximity thresholds. | Fallback to harmonic distance envelope skinning (`ARMATURE_ENVELOPE`). |
| Landmark Misidentification on Chimeras | Medium | Medium | Multi-hypothesis confidence scoring based on bounding box ratios. | Fallback to generic biped or single articulated spine chain. |
| MeshAnything V2 Server Timeout | Medium | Medium | Enforce strict 90-second solver timeout. | Immediately trigger local Blender QuadriFlow remeshing. |

---

### 4.7 Key Performance Indicators (KPIs)
- **Quad Ratio**: Retopologized meshes achieve $\ge 90\%$ quadrilateral faces.
- **Rigging Success Rate**: 100% of generated creatures receive a functional, parented armature.
- **Skinning Convergence Rate**: Zero unweighted vertices on deformable mesh surfaces.
- **Retopology Latency**: Local QuadriFlow remeshing < 5.0 seconds; Cloud retopology < 90 seconds.

---

## 5. Phase 4: Production Hardening & Interactive Blender Studio Addon (Month 6+)

### 5.1 Strategic Objective
Elevate MorphoMesh into a production digital art studio. Deliver a native Blender 5.2.1 LTS interactive addon with an N-Panel graphical user interface, low-latency bidirectional TCP socket server, real-time EEVEE Next viewport streaming to Google Antigravity 2.0, multi-agent collaborative workflows, and enterprise extension packaging.

---

### 5.2 Detailed Work Breakdown Structure (WBS)

```
PHASE 4 WORK BREAKDOWN STRUCTURE
├── 4.1 Interactive Blender Studio Addon (blender_addon/morphomesh/)
│   ├── 4.1.1 3D Viewport Sidebar N-Panel UI (panels.py) with status dashboard
│   ├── 4.1.2 Operator controls for manual triggering, bridge start/stop, and asset sync
│   ├── 4.1.3 Real-time visual progress indicators for remote inference and remeshing
│   └── 4.1.4 User preferences panel for host, port, API keys, and cache management
├── 4.2 Low-Latency Localhost TCP Bridge (server_listener.py)
│   ├── 4.2.1 Multi-client socket server bound to 127.0.0.1:9876
│   ├── 4.2.2 Non-blocking main-thread synchronization via bpy.app.timers
│   ├── 4.2.3 Sub-millisecond command dispatch latency (< 2 ms roundtrip)
│   └── 4.2.4 Graceful socket shutdown, cleanup, and port collision recovery
├── 4.3 Real-Time Viewport Preview Streaming
│   ├── 4.3.1 Headless and interactive viewport buffer capture via GPU offscreen rendering
│   ├── 4.3.2 Apple Metal-accelerated EEVEE Next turntable video/still compression
│   └── 4.3.3 Multipart ImageContent streaming to Antigravity agents in real time
├── 4.4 Multi-Agent Collaborative Orchestration Protocols
│   ├── 4.4.1 Role division: Art Director, Modeler, Rigger, and Shading agents
│   ├── 4.4.2 Visual feedback loop: Render preview -> Agent visual critique -> Iterative edit
│   └── 4.4.3 Multi-turn editing memory maintaining creature consistency across modifications
├── 4.5 Enterprise Cloud Render Farm Integration
│   ├── 4.5.1 Cycles high-res raytraced turntable batch rendering on remote clusters
│   ├── 4.5.2 Distributed caching of 3D assets, textures, and rigged scene files
│   └── 4.5.3 USD (Universal Scene Description) and Alembic export pipelines
└── 4.6 Packaging, Distribution & Continuous Operations
    ├── 4.6.1 Standalone Python wheel package (pip install morphomesh)
    ├── 4.6.2 Blender Extensions Platform compatible zip package
    └── 4.6.3 Automated GitHub Actions release pipeline with multi-platform verification
```

---

### 5.3 Deliverables & Artifacts
1. Complete `blender_addon/morphomesh/` interactive package ready for Blender 5.2.1 LTS.
2. Built addon distribution archive (`morphomesh_addon.zip`).
3. CLI distribution package (`pyproject.toml` console scripts `morphomesh` and `morphomesh-server`).
4. Multi-agent director-in-the-loop prompt templates and orchestration guidelines.
5. End-to-end tutorial documentation and video walkthrough assets.

---

### 5.4 Technical Dependencies & Integration Boundaries
- **Blender API**: Blender 5.2.1 LTS Python API (`bpy`, `bmesh`, `mathutils`, `gpu`).
- **Network**: Localhost TCP loopback (`127.0.0.1:9876`).
- **Packaging**: Standard Python `setuptools` / `wheel` and Blender Extension Manifest (`blender_manifest.toml`).

---

### 5.5 Timeline & Sprint Schedule
- **Sprint 4.1 (Weeks 21–22)**: Interactive N-Panel GUI development and preference configurations.
- **Sprint 4.2 (Weeks 23–24)**: Viewport GPU buffer capture and sub-second preview streaming.
- **Sprint 4.3 (Weeks 25–26)**: Multi-agent orchestration protocols and feedback iteration loops.
- **Sprint 4.4 (Weeks 27–28)**: Enterprise packaging, cross-platform validation, and release publication.

---

### 5.6 Risk Management & Fallback Strategy
| Risk Event | Likelihood | Impact | Mitigation Strategy | Fallback Protocol |
|---|---|---|---|---|
| Port 9876 Collision | Low | Medium | Configurable port preference with automatic increment scan (`9876 -> 9877`). | Notify user in Blender UI; fall back to available port. |
| Main-Thread UI Freezing in Blender | Medium | High | Keep timer callbacks strictly non-blocking (< 5 ms execution window). | Defer heavy mesh processing to background subprocess worker. |
| Agent Hallucination in Multi-Turn Edits | Medium | Medium | Maintain rigid scene state in `get_scene_status` before each action. | Reset to checkpoint snapshot if agent introduces mesh corruption. |

---

### 5.7 Key Performance Indicators (KPIs)
- **Interactive Command Latency**: IPC roundtrip < 2.0 ms for standard scene mutations.
- **Viewport Render Latency**: 1080p preview render returned to agent in < 1.2 seconds.
- **Agent Self-Correction Rate**: $\ge 85\%$ success in autonomous repair of detected geometric defects.
- **Packaging Integrity**: 1-click installation in Blender with zero external Python path requirements.

---

## 6. Cross-Phase Engineering & Operational Governance

### 6.1 Computing Hardware & VRAM Allocation Matrix

MorphoMesh partitions computational tasks across local and remote hardware to maximize performance while minimizing cost:

| Pipeline Stage | Module / Model | Minimum Hardware | Target Hardware | Execution Location | VRAM Requirement |
|---|---|---|---|---|---|
| **Coordination** | FastMCP Server 1.28.1 | 4-Core CPU, 8GB RAM | Apple M-Series (ARM64) | Local Workstation | 0 MB (Host RAM: 150 MB) |
| **Bridge / Sandbox** | AST Security & IPC | 4-Core CPU, 8GB RAM | Apple M-Series (ARM64) | Local Workstation | 0 MB (Host RAM: 80 MB) |
| **Stage 1 (Concept)** | FLUX.1-schnell / SD-XL | NVIDIA RTX 3090 | NVIDIA A10G / RTX 4090 | Remote Cloud GPU | 16 GB - 24 GB VRAM |
| **Stage 1 (Alpha)** | Rembg / BiRefNet | Apple Silicon M1 (MPS) | Apple M3/M4 Max (Neural Engine)| Local Workstation | 0 MB (Host RAM: 1.2 GB) |
| **Stage 2 (3D Gen)** | TRELLIS.2 (4B O-Voxel) | NVIDIA RTX 4090 (24GB) | NVIDIA A100 (40GB/80GB) | Remote Cloud GPU | 22 GB - 36 GB VRAM |
| **Stage 2 (3D Gen)** | Hunyuan3D-2.1 | NVIDIA RTX 4090 (24GB) | NVIDIA A10G (24GB) | Remote Cloud GPU | 18 GB - 22 GB VRAM |
| **Stage 2 (Fallback)**| TripoSR (Local) | Apple Silicon M1 (16GB UMA)| Apple M3/M4 Max | Local Workstation | Unified Memory: 6 GB |
| **Stage 3 (Retopo)** | MeshAnything V2 | NVIDIA RTX 3090 (24GB) | NVIDIA A10G (24GB) | Remote Cloud GPU | 14 GB - 18 GB VRAM |
| **Stage 3 (Retopo)** | Blender QuadriFlow | 4-Core CPU, 8GB RAM | Apple M-Series (8+ Cores) | Local Workstation | 0 MB (Host RAM: 500 MB) |
| **Stage 4 (Rigging)**| Landmark PCA & Rigify | 4-Core CPU, 8GB RAM | Apple M-Series (ARM64) | Local Workstation | 0 MB (Host RAM: 300 MB) |
| **Stage 5 (Render)** | Blender EEVEE Next | Apple M1 GPU (Metal RT) | Apple M3/M4 Max (Metal RT) | Local Workstation | GPU VRAM: 2 GB - 4 GB |

---

### 6.2 Cloud Infrastructure & API Cost Projections

Estimated operating costs per creature generation across roadmap phases:

| Stage | Model / Service | Cloud Provider | Compute Tier | Duration | Cost per Asset |
|---|---|---|---|---|---|
| **Stage 1** | FLUX.1-schnell | Replicate / Fal.ai | Serverless GPU | ~ 2.5 s | $0.003 |
| **Stage 2** | TRELLIS.2 4B Mesh Gen | Replicate / RunPod | Dedicated A10G | ~ 45.0 s | $0.038 |
| **Stage 2 (PBR)** | PBR Texture Baking | RunPod Serverless | Dedicated RTX 4090 | ~ 15.0 s | $0.012 |
| **Stage 3** | MeshAnything V2 Retopo | Custom Linux Server | Spot A10G | ~ 30.0 s | $0.018 |
| **Stage 4 & 5** | Rigging & EEVEE Render | Local Workstation | Apple Silicon Metal | ~ 3.5 s | **$0.000** (Local) |
| **TOTAL** | **Full Photorealistic Asset** | **Hybrid Pipeline** | **Tiered Hybrid** | **~ 96.0 s** | **$0.071 / creature** |

*In Phase 1 Mock Mode, generation cost is strictly **$0.0000**.*

---

### 6.3 Security Auditing & Continuous Penetration Testing

To guarantee that the autonomous agent cannot compromise the host environment, all PRs and releases must pass automated security penetration tests (`tests/test_blender_bridge.py`):

1. **Malicious AST Penetration Harness**:
   - `test_block_os_system()`: Injects `import os; os.system('touch /tmp/pwned')`.
   - `test_block_subprocess_popen()`: Injects `import subprocess; subprocess.Popen(['ls'])`.
   - `test_block_dynamic_eval()`: Injects `eval("__import__('os').system('ls')")`.
   - `test_block_dunder_reflection()`: Injects `().__class__.__bases__[0].__subclasses__()`.
   - `test_block_open_filesystem()`: Injects `open('/etc/passwd', 'r').read()`.
2. **Denial-of-Service Fuzzing**:
   - Injects infinite while loops (`while True: pass`). Asserts termination within `timeout_seconds + 1.0` seconds.
   - Injects memory exhaustion arrays (`x = [0] * 10**9`). Asserts process abort without crashing parent server.

---

### 6.4 Semantic Versioning & Release Governance

MorphoMesh adheres strictly to [Semantic Versioning 2.0.0](https://semver.org/):
- **`v0.1.0` (Phase 1 Exit)**: Runnable PoC with FastMCP server, mock inference, headless Blender bridge, AST security guard, and 100% passing test suite.
- **`v0.2.0` (Phase 2 Exit)**: Remote GPU adapters for TRELLIS.2, Hunyuan3D-2.1, FLUX.1, and PBR texture baking.
- **`v0.3.0` (Phase 3 Exit)**: MeshAnything V2 autoregressive retopology, morphological landmark locator, and Rigify creature auto-rigging.
- **`v1.0.0` (Phase 4 Exit / Production)**: Production interactive Blender addon, sub-second viewport feedback, multi-agent director collaboration, and Blender Extensions Platform distribution.

---

*End of Engineering & Research Roadmap — MorphoMesh Architectural Plan `MM-R3-ROAD-001`.*
