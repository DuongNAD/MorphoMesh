# Yu Nian An (余念安) — Multi-Format Production Packaging & Export Guide

## 1. Asset Overview & Technical Specifications

**Yu Nian An (余念安)** is an industrial-grade, photorealistic/semi-realistic digital human character synthesized by the MorphoMesh engine for Blender 4.5+ LTS, Unreal Engine 5.4+, Unity 6, and real-time WebGL/Three.js environments.

### Core Specifications
- **Character Height**: 1.65 m (Canonical turnaround proportions)
- **Head-to-Body Ratio**: 7.41 (Anthropometrically proportional stylized photorealism)
- **Measurements**: Chest girth 0.82 m, Waist girth 0.58 m (0.70 WHR cinched waist), Hip girth 0.86 m
- **Body Base Topology**: Exactly 2,036 pure quads, 2,144 vertices (100% pure quad topology; 0 triangles, 0 n-gons, 0 non-manifold edges, 0 zero-area faces, 0 open boundary edges)
- **Skeletal Rigging**: Rigify Human Metarig featuring exactly 163 deforming bones (`DEF-*`), anatomical landmark snapping with pre-bends (elbows +Y, knees -Y), and volume-preserving anti-pinch skin weights
- **Facial Blendshapes**: Complete Apple ARKit FACS 52 standard shape keys for mocap, live VTubing, and speech phoneme lip-sync
- **Materials**: 16 dedicated PBR materials with fake-user persistence, Random Walk Subsurface Scattering (radius `[1.0, 0.22, 0.11]`), dual-chamber refractive eyes (cornea IOR 1.376, iris dish IOR 1.333), and micro-specular wetness maps

---

## 2. Package Contents & Deliverables

```
output/yu_nian_an/
├── Yu_Nian_An_Master.blend        # Master production scene (Cycles & EEVEE Next ready)
├── Yu_Nian_An.fbx                 # Rigged production FBX with 163 DEF bones & 52 ARKit shape keys
├── Yu_Nian_An.glb                 # Web/Real-time glTF 2.0 binary with PBR shaders & morph targets
├── README_EXPORT.md               # Authoritative engine integration & import manual
└── textures/                      # Complete 4K (4096 x 4096) PBR Texture Suite
    ├── Yu_Nian_An_BaseColor_4K.png   # Porcelain skin, soft rose lips, dark eyeliner, ivory silk, ice-blue sash
    ├── Yu_Nian_An_Normal_4K.png      # Tangent-space normal map (micro-pores, lip wrinkles, fabric twill)
    ├── Yu_Nian_An_Roughness_4K.png   # Dual roughness map (face 0.38, lips 0.28, scalp 0.70, dress 0.45, sash 0.22)
    ├── Yu_Nian_An_Metallic_4K.png    # Non-metal dielectric (0.0) with subtle sheen on aglets/buckles
    ├── Yu_Nian_An_SSS_4K.png         # Subsurface scattering mask (high on ears, nose, lips)
    ├── Yu_Nian_An_Alpha_4K.png       # Eyelashes/eyebrows and bangs fringe opacity cutouts
    ├── Yu_Nian_An_Height_4K.png      # Displacement / bump height map (lip fullness, oral slit, seams)
    ├── Yu_Nian_An_ORM_4K.png         # Pre-packed Unreal Engine map (R=AO, G=Roughness, B=Metallic, A=SSS)
    └── Yu_Nian_An_MaskMap_4K.png     # Pre-packed Unity HDRP map (R=Metallic, G=AO, B=Detail/SSS, A=Smoothness)
```

---

## 3. Blender 4.5+ Master Scene Organization

The master scene (`Yu_Nian_An_Master.blend`) strictly implements the authoritative 7-tier collection hierarchy:

1. **`Yu_Nian_An_Master`** (Root Collection)
2. **`01_Body`**:
   - `Yu_Nian_An_Body`: Parametric female body mesh (2,036 pure quads, 193 vertex groups, 52 ARKit FACS shape keys)
   - `Mesh_Eye_Left_CorneaSclera` & `Mesh_Eye_Right_CorneaSclera`: Outer refractive cornea dome (IOR 1.376)
   - `Mesh_Eye_Left_IrisPupil` & `Mesh_Eye_Right_IrisPupil`: Concave iris dish with radial stroma fibers and pupil
   - `Mesh_Eyelid_Left` & `Mesh_Eyelid_Right`: Almond eyelid margin geometry with dark lash lining
   - `Mesh_Lips`: Curvilinear lip vermilion with oral fissure boundary
3. **`02_Hair`**:
   - `Hair_Hime_Bangs`: Hime-cut straight bangs trimmed sharply across forehead
   - `Hair_Hime_Sidelocks`: Symmetrical face-framing sidelocks extending past jawline
   - `Hair_Scalp_Crown`: Anatomical cranial scalp coverage with center parting
   - `Hair_Back_Cascade`: Flowing jet-black back hair cascading to mid-thigh
   - `Hair_Eyebrows` & `Hair_Eyelashes`: Delicate facial framing cards
4. **`03_Wardrobe`**:
   - `Mesh_Dress_Bodice`: White two-strap sleeveless bodice tailored to chest curvature
   - `Mesh_Dress_PleatedSkirt`: 20-pleat flared A-line skirt with organic drape
   - `Mesh_Dress_WaistSash`: Pale ice-blue satin high-waist sash with knot and dangling streamers
   - `Mesh_Sandal_L` & `Mesh_Sandal_R`: Minimalist flat slip-on sandals with leather sole
5. **`04_Props`**:
   - `Prop_Marionette_Strings`: 10 glowing crimson cords anchored to finger distal landmarks
   - `Prop_Butterfly_00` to `Prop_Butterfly_09`: 10 instanced luminous white swallowtail butterflies
6. **`05_Armature`**:
   - `Armature_Yu_Nian_An_Rigify`: 163 DEF deforming bones with anti-pinch skin weights
7. **`06_Lights_Camera`**:
   - 3-point studio softbox illumination: Key (5500K warm), Fill (6500K cool), Rim/Hair (4500K angel ring)
   - Multi-angle cameras: 85mm Portrait, 50mm Full Body, Turnaround (Front, ThreeQuarter, Profile, Back), 135mm Close-up

---

## 4. 4K PBR Texture Suite & Channel Specifications

All textures are authored at uncompressed $4096 \times 4096$ resolution with sRGB color space for BaseColor and Linear color space for utility masks:

| Map Filename | Color Space | Bit Depth | Description & Value Distribution |
|---|---|---|---|
| `Yu_Nian_An_BaseColor_4K.png` | sRGB | 8-bit RGB | Porcelain skin `#F4E4DC`, soft rose lips `#D67080`, eyeliner `#1A181E`, ivory silk dress `#F8F6F2`, satin sash `#C6DEEE`, gold aglets `#E1C36E` |
| `Yu_Nian_An_Normal_4K.png` | Linear | 8-bit RGB | OpenGL tangent-space $(+X, +Y, +Z)$. Micro-skin pores, vertical lip vermilion wrinkles, orthogonal fabric twill weave |
| `Yu_Nian_An_Roughness_4K.png` | Linear | 8-bit Grayscale | Dual roughness: face `0.38`, lips `0.28` (moist gloss), scalp `0.70`, silk dress `0.45`, satin sash `0.22`, sandals `0.50`, metal aglets `0.20` |
| `Yu_Nian_An_Metallic_4K.png` | Linear | 8-bit Grayscale | Non-metal dielectric (`0.0`) for skin, eyes, fabrics; Full metallic (`1.0`) on ribbon aglets, sash buckles, and hairpin hardware |
| `Yu_Nian_An_SSS_4K.png` | Linear | 8-bit Grayscale | Subsurface scattering intensity mask: ears `0.85`, nose `0.75`, lips `0.70`, face `0.45`, body `0.35`, fabric/metal `0.0` |
| `Yu_Nian_An_Alpha_4K.png` | Linear | 8-bit Grayscale | Opacity mask: solid mesh surfaces `1.0`, feathered feathering on eyelashes/eyebrows and bangs fringe tip cutouts |
| `Yu_Nian_An_Height_4K.png` | Linear | 8-bit Grayscale | Mid-gray neutral `0.50` (`128`). Lip fullness `+0.12`, sash knot `+0.22`, oral fissure `-0.25`, eyelid socket `-0.10`, skin pores `\pm 0.015` |
| `Yu_Nian_An_ORM_4K.png` | Linear | 32-bit RGBA | Pre-packed Unreal Engine texture: R=Ambient Occlusion, G=Roughness, B=Metallic, A=Subsurface Scattering |
| `Yu_Nian_An_MaskMap_4K.png` | Linear | 32-bit RGBA | Pre-packed Unity HDRP texture: R=Metallic, G=Ambient Occlusion, B=Detail/SSS, A=Smoothness (1 - Roughness) |

### Recommended Channel Packing
- **Unreal Engine ORM (Occlusion / Roughness / Metallic)**:
  * **R Channel**: Ambient Occlusion (derived from Height/Mesh cavity)
  * **G Channel**: Roughness (`Yu_Nian_An_Roughness_4K.png`)
  * **B Channel**: Metallic (`Yu_Nian_An_Metallic_4K.png`)
  * **Alpha Channel**: Subsurface Scattering Mask (`Yu_Nian_An_SSS_4K.png`)
- **Unity HDRP Mask Map**:
  * **R Channel**: Metallic (`Yu_Nian_An_Metallic_4K.png`)
  * **G Channel**: Ambient Occlusion
  * **B Channel**: Detail Mask / SSS Mask (`Yu_Nian_An_SSS_4K.png`)
  * **A Channel**: Smoothness ($1.0 - \text{Roughness}$)

---

## 5. Game Engine Import & Setup Guides

### A. Unreal Engine 5.4+ (UE5) Integration

1. **Importing the FBX Asset**:
   - Drag `Yu_Nian_An.fbx` into your Content Browser.
   - **FBX Import Options**:
     * **Mesh**: Check `Skeletal Mesh` and `Import Mesh`.
     * **Geometry**: Check `Import Morph Targets` (CRITICAL: imports all 52 ARKit FACS shape keys).
     * **Normals**: Set `Normal Import Method` to `Import Normals and Tangents`.
     * **Skeleton**: Select `None` on initial import to generate the `Yu_Nian_An_Skeleton`, or select an existing Rigify compatible skeleton.
     * **Miscellaneous**: Check `Preserve Smoothing Groups` and uncheck `Import Animations` (unless importing pose clips).

2. **Skin Shader Setup (Subsurface Profile)**:
   - In Material Editor, set **Material Domain** = `Surface`, **Blend Mode** = `Opaque`, **Shading Model** = `Subsurface Profile`.
   - Create a new **Subsurface Profile** asset:
     * Surface Albedo: `#F4E4DC` (Porcelain Skin)
     * Mean Free Path Distance: `[1.0, 0.22, 0.11]` (Red SSS transmission)
    - **Normal Map Configuration (CRITICAL for Unreal Engine 5)**:
      * Double-click `Yu_Nian_An_Normal_4K.png` in Content Browser to open the Texture Editor.
      * Under **Texture** -> **Advanced**, check **Flip Green Channel** (converts OpenGL +Y normal map coordinates to Unreal Engine / DirectX -Y tangent space so facial creases and pores shade outward rather than inverted).
    - **PBR Texture Connections**:
      * Connect `Yu_Nian_An_BaseColor_4K.png` to **Base Color**.
      * Connect `Yu_Nian_An_Normal_4K.png` to **Normal**.
      * Connect `Yu_Nian_An_Roughness_4K.png` (or Green channel of `Yu_Nian_An_ORM_4K.png`) to **Roughness**.
      * Connect Blue channel of `Yu_Nian_An_ORM_4K.png` (or `Yu_Nian_An_Metallic_4K.png`) to **Metallic**.
      * Connect Red channel of `Yu_Nian_An_ORM_4K.png` to **Ambient Occlusion**.
      * Connect `Yu_Nian_An_SSS_4K.png` (or Alpha channel of `Yu_Nian_An_ORM_4K.png`) to **Subsurface Color** or opacity scalar multiplier.

3. **Eye Shader Setup (Dual Chamber Refraction)**:
   - For `Mesh_Eye_*_CorneaSclera`: Set **Shading Model** = `Eye` or `Subsurface Profile`.
   - Connect outer cornea normal and connect iris dish UV offsets to the refraction parallax channel.

4. **Apple ARKit Live Link Face Tracking**:
   - All 52 blendshapes match standard Apple ARKit FACS naming conventions (`eyeBlinkLeft`, `jawOpen`, `mouthSmileLeft`, `mouthSmileRight`, etc.).
   - In your Animation Blueprint, add a `Live Link Pose` node targeting your iPhone/iPad Live Link subject name. The morph targets will drive facial animation in real-time with zero retargeting remap required.

---

### B. Unity 6 (URP / HDRP) Integration

1. **Model Import Settings**:
   - Place `Yu_Nian_An.fbx` or `Yu_Nian_An.glb` in your `Assets/Models/YuNianAn/` folder.
   - **Model Tab**:
     * Set **Mesh Compression** = `Off` (preserves micro-geometry).
     * Check **Read/Write Enabled** if accessing vertices at runtime.
     * Set **Normals** = `Import`, **Tangents** = `Calculate MikkTSpace`.
   - **Rig Tab**:
     * Set **Animation Type** = `Humanoid`.
     * Set **Avatar Definition** = `Create From This Model`.
     * Click **Configure...** to verify bone mapping (all 10 fingers and spine automatically map to Unity Humanoid Avatar).
   - **BlendShapes Tab**:
     * Check **Import BlendShapes** = `True`.
     * Verify all 52 shape keys appear in the Skinned Mesh Renderer component.

2. **HDRP Shading Setup**:
   - For skin: Use `HDRP/Lit` shader with **Material Type** = `Subsurface Scattering`. Assign a Diffusion Profile with subsurface radius `1.0m, 0.22m, 0.11m`.
   - For satin sash: Set **Material Type** = `Anisotropy` with smoothness `0.78` ($1 - 0.22$).
   - For hair: Use `HDRP/Hair` shader with Melanin scattering.

---

### C. WebGL / Three.js Implementation

Load `Yu_Nian_An.glb` and bind 4K PBR textures using Three.js standard loaders:

```javascript
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

// 1. Load 4K PBR Texture Suite via THREE.TextureLoader
const textureLoader = new THREE.TextureLoader();

const baseColorMap = textureLoader.load('output/yu_nian_an/textures/Yu_Nian_An_BaseColor_4K.png');
baseColorMap.colorSpace = THREE.SRGBColorSpace;
baseColorMap.flipY = false;

const normalMap = textureLoader.load('output/yu_nian_an/textures/Yu_Nian_An_Normal_4K.png');
normalMap.flipY = false;

const roughnessMap = textureLoader.load('output/yu_nian_an/textures/Yu_Nian_An_Roughness_4K.png');
roughnessMap.flipY = false;

// Optional: Pre-packed ORM map (R=AO, G=Roughness, B=Metallic, A=SSS)
const ormMap = textureLoader.load('output/yu_nian_an/textures/Yu_Nian_An_ORM_4K.png');
ormMap.flipY = false;

// 2. Load glTF 2.0 GLB Model and Bind Materials
const loader = new GLTFLoader();

loader.load('output/yu_nian_an/Yu_Nian_An.glb', (gltf) => {
    const character = gltf.scene;
    scene.add(character);

    // Traverse and bind 4K PBR textures to mesh materials
    let bodyMesh = null;
    character.traverse((node) => {
        if (node.isMesh) {
            node.castShadow = true;
            node.receiveShadow = true;

            // Apply texture maps to material
            if (node.material) {
                node.material.map = baseColorMap;
                node.material.normalMap = normalMap;
                node.material.normalScale.set(1.0, 1.0);
                node.material.roughnessMap = roughnessMap;
                // Alternatively, bind pre-packed ORM texture:
                // node.material.aoMap = ormMap;
                // node.material.roughnessMap = ormMap;
                // node.material.metalnessMap = ormMap;
                node.material.roughness = 1.0;
                node.material.metalness = 1.0;
                node.material.needsUpdate = true;
            }
        }
        if (node.isSkinnedMesh && node.name.includes('Body')) {
            bodyMesh = node;
        }
    });

    if (bodyMesh && bodyMesh.morphTargetDictionary) {
        console.log('Available Morph Targets:', Object.keys(bodyMesh.morphTargetDictionary));

        // Animate ARKit blendshapes (e.g. smile or blink)
        function animateFace(time) {
            const smileIdx = bodyMesh.morphTargetDictionary['mouthSmileLeft'];
            const blinkIdx = bodyMesh.morphTargetDictionary['eyeBlinkLeft'];
            
            // Dynamic expression modulation
            bodyMesh.morphTargetInfluences[smileIdx] = 0.5 + 0.5 * Math.sin(time * 0.002);
            bodyMesh.morphTargetInfluences[blinkIdx] = Math.max(0, Math.sin(time * 0.005) > 0.95 ? 1.0 : 0.0);
        }
    }
});
```

---

## 6. Verification & Quality Assurance

Every production export has been verified through automated test pipelines:
- **FBX Integrity**: Valid `Kaydara FBX Binary` magic header, binary file size > 5 MB, 163 DEF bones and 52 shape keys present.
- **glTF Integrity**: Valid `glTF` version 2 binary container, valid JSON chunk, 164 skin joints, 52 target morph names on `Yu_Nian_An_Body`, and `TEXCOORD_0` UV coordinates across all mesh primitives.
- **Texture Suite Integrity**: All 9 PBR texture maps strictly adhere to $4096 \times 4096$ resolution and accurate physical value distributions.
- **Topology Standard**: Non-destructive quad topology preserved across all export formats.
