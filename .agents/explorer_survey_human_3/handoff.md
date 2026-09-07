# Final Handoff Report: Visual Aesthetics, Reference Art Analysis, Shading, Grooming & Magic Props Specification for Yu Nian An (余念安)

**Agent**: Explorer 3 (Visual Aesthetics, Reference Art, Shading, Grooming & Props Explorer)  
**Parent**: `orchestrator_human_1` (Conversation ID: `fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\explorer_survey_human_3`  
**Reference Image**: `C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788716034772.jpg`  
**Status**: Completed / Ready for M2 Implementation  

---

## 1. Observation

### 1.1 Source Documents and Reference Assets Inspected
1. `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md`:
   - Line 189: "Nâng cấp MorphoMesh thành pipeline tạo mô hình người 3D chân thực đạt chuẩn công nghiệp (Photorealistic Digital Human Pipeline)... tạo mô hình 3D hoàn chỉnh của nhân vật Dư Niệm An (余念安 - Yu Nian An) theo phong cách bán thực tế cao cấp (Semi-Realistic / Stylized Photorealism) bám sát tuyệt đối bản vẽ tham chiếu."
   - Line 199: "Xây dựng hệ thống vật liệu da người PBR với Subsurface Scattering (Random Walk), mắt 2 buồng khúc xạ, tóc sợi hạt (Geometry Nodes Curves) và trang phục động (`src/morphomesh/human_materials.py`, `src/morphomesh/human_grooming.py`, `src/morphomesh/wardrobe.py`)."
   - Line 203-205: "giữ trọn vẹn nét thanh tú thuần khiết, đôi mắt có hồn và biểu cảm tĩnh lặng/u buồn... váy hai dây trắng thắt đai eo và dép bệt... bàn tay mảnh mai gắn các sợi chỉ đỏ ma thuật điều khiển đàn bướm trắng phát sáng theo concept... tóc đen dài mái bằng (hime cut / straight bangs)."
   - Line 227: "File dự án `.blend` hoàn chỉnh được lưu lại với cấu trúc phân tầng rõ ràng (Collection: Body, Hair, Dress, Accessories, Armature, Lights/Camera)."

2. Reference Art Image `media_1788716034772.jpg` (Direct visual inspection of 4 full-body views and detail insets):
   - **Sheet Title**: 余念安 3D模型参考图 (Yu Nian An 3D Model Reference Sheet).
   - **Vertical Scale Ruler (0.0 to 10.0 scale units)**:
     - Total character height: `10.0` units (standard target scale = 1.62m, 1 unit = 0.162m).
     - Head top / Crown: `Z = 10.0`.
     - Chin / Jaw base: `Z = 8.65` -> Head vertical length = `1.35` units.
     - Height-to-head ratio: $10.0 / 1.35 \approx 7.41$ heads tall (slender, graceful female proportions).
     - Shoulder / Clavicle line: `Z = 8.00`.
     - Bust center: `Z = 7.30`.
     - High waist sash / Empire belt: `Z = 6.10 - 6.35`.
     - Natural waist / Hip joint level: `Z = 5.00`.
     - Skirt hem: `Z = 3.40` (settles gracefully right below the patella/kneecap).
     - Kneecap center: `Z = 3.70`.
     - Ankle malleolus: `Z = 0.85`.
     - Ground / Sandal sole: `Z = 0.00`.
     - Hands in casting gesture: elevated to `Z = 5.60 - 6.20`, abducted laterally by ~35°.

### 1.2 Multi-Angle Visual Breakdown (Row 1: Full-Body Turnaround)
1. **Front View (正面 - CHÍNH DIỆN)**:
   - Pose: Upright standing posture, feet parallel at hip width, arms gently elevated and spread outward in a puppeteer / spellcasting gesture.
   - Arms & Hands: Slender forearms, delicate hands with ten tapered fingers spread, fingertips tethered to taut crimson marionette cords that radiate downwards and outwards.
   - Dress: Pure white sleeveless dress with two thin shoulder straps; high waist sash with twin vertical ribbon streamers cascading down the center; flared A-line skirt with soft box/knife pleats ending just below the knees.
   - Legs & Feet: Bare calves and ankles, minimal flat slip-on white sandals exposing toes and heel.
   - Hair: Straight fringe bangs (hime cut) brushing the eyebrow ridge, two face-framing sidelocks descending to the chest, long silky dark hair draped behind.
   - Magic Props: Luminous white butterflies hovering around hands and resting on glowing red strings.

2. **3/4 Front View (3/4正面 - 3/4 CHÍNH DIỆN)**:
   - Silhouette: Slender S-curve spine posture; subtle bust projection cleanly fitted into bodice; graceful neck angle.
   - Dress volume: High waist belt cinch creates clear transition into a bell-shaped flared skirt with rhythmic vertical shadow valleys along the pleats.
   - Hair separation: Clean separation between front bangs, face-framing sidelocks (tóc mai) falling in front of the shoulders, and the voluminous rear hair mass falling down the back.

3. **Side Profile View (侧面 - GÓC NGANG)**:
   - Cranial & Facial Profile: Rounded occipital skull; gentle slope from brow to delicate nasal bridge; refined upturned nose tip with subtle supratip break; soft lips with upper lip slightly projecting over lower lip; refined chin with subtle mental crease.
   - Posture & Spine: Natural cervical lordosis and thoracic kyphosis; slender arms hanging with slight natural elbow bend.
   - Dress Profile: Front bodice follows bust contour; vertical back strap anchors straight into horizontal back bodice line; skirt flares symmetrically fore and aft.
   - Footwear: Ultra-thin sandal sole (~12mm), slender metatarsal strap arching over the instep.

4. **Back View (背面 - PHÍA SAU)**:
   - Hair Cascade: Magnificent waterfall of jet-black / dark charcoal hair fanning out over the scapulae and tapering gently down to `Z = 3.80` (mid-thigh level).
   - Upper Back: Bare shoulders and upper back; clean straight shoulder straps spanning from clavicle to the horizontal back bodice line.
   - Skirt: Flared skirt pleats radiate cleanly from beneath the rear waist sash.

### 1.3 Close-up Facial Features & Detail Insets (Row 2 & Row 3)
1. **Facial Expression (Mặt và Biểu cảm)**:
   - Mood: Quiet, melancholic, serene, introverted, pure (thanh tú, thuần khiết, u buồn, tĩnh lặng).
   - Eyes: Almond-shaped anime/semi-realistic eyes; dark charcoal/slate iris with deep pupils; delicate double eyelid crease; thick, soft upper eyeliner; introspective, slightly downward-forward gaze.
   - Eyebrows: Soft, thin, natural arched brows, subtly drooping at outer tail, partially veiled by straight bangs.
   - Nose: Small, delicate, narrow nasal bridge, softly rounded tip with minimal nostril flair.
   - Lips: Natural rosy pink tint, soft bow at cupid's bow, subtle philtrum, slightly parted neutral line.
   - Skin Texture Insets (`Chi Tiết Da` & `Chi Tiết Mặt`):
     - Porcelain fair skin tone with high translucency.
     - Very soft peach/rose flush on cheeks, nose tip, and lips.
     - Smooth micro-specular sheen with zero visible coarse pores; subtle anatomical definition along the sternocleidomastoid tendons and clavicle hollows.

2. **Signature Magic Props Insets (`Chi Tiết Tay` & `Các Loại Bướm`)**:
   - Marionette Strings: Thin glowing red threads (`#FF1744`) looped around each finger of both hands, extending in taut straight lines down towards the skirt hem, intersecting and forming geometric puppeteer web lines.
   - White Butterflies:
     - 4 distinct flight/perched configurations: Spread gliding (dorsal), 3/4 angled flap, folded wings (profile perched), fluttering flutter.
     - Morphology: Delicate swallowtail / pierid wings with translucent pearl white membrane, delicate radial veins, and soft radiant bloom.
   - Wardrobe Details (`Chi Tiết Trang Phục`):
     - Bodice: Sweetheart scoop neckline, twin flat straps (width ~1.2cm).
     - Waist Belt: Wide sash wrapped tightly beneath bust with two dangling ribbon tails.
     - Sandals: Minimalist flat sole with single strap over foot arch.

---

## 2. Logic Chain

From the direct visual observations above, we systematically derive the exact technical specifications for Blender 4.5+ PBR shading, Geometry Nodes hair grooming, wardrobe tailoring, and magic prop rigging.

```
[Observation: Porcelain skin with translucent peach flush and soft specular sheen]
   ↳ [Logic Step 1]: Implement Principled BSDF v2 with Random Walk (Skin) Subsurface Scattering,
                     calibrated SSS radius [1.0, 0.22, 0.11] (deep red penetration, fast blue/green absorption),
                     dual roughness (0.48 base, 0.18 lips/moisture), and clearcoat on wet zones.

[Observation: Deep, soulful, melancholic eyes with glass-like reflections and dark slate iris]
   ↳ [Logic Step 2]: Implement dual-chamber eye architecture:
                     - Outer Cornea: Transmissive shell (IOR 1.376, Roughness 0.015).
                     - Inner Iris: Sunken concave parabolic dish (1.8mm depth) with dark slate stroma and pupil hole.
                     - Tear Meniscus: Wet geometry strip along lid margins (IOR 1.333).

[Observation: Silky jet-black hair with straight hime bangs, sidelocks, and long cascade]
   ↳ [Logic Step 3]: Build a 6-layer Blender 4.5+ Curves system governed by Geometry Nodes:
                     Interpolate Hair Curves (2,500 guides -> 95,000 strands) + Clump + Noise + Set Curve Profile.
                     Material: Principled Hair BSDF with high melanin (0.88) and low radial roughness (0.22)
                     for the iconic silk "Angel Ring" sheen.

[Observation: White sleeveless dress with empire waist sash, pleated skirt, and flat sandals]
   ↳ [Logic Step 4]: Model quad-dominant garment conforming to body mesh; assign ivory silk PBR
                     with velvet sheen (0.55) and subtle backlight SSS (0.12); satiny ribbon sash; flat sandals.

[Observation: Taut glowing red marionette cords and luminous white fluttering butterflies]
   ↳ [Logic Step 5]: Procedural curve splines anchored to fingertip bones with high-intensity red emission (strength 6.5);
                     Instanced butterfly quad meshes with pearl-translucent SSS and soft white emission (strength 3.0).

[Observation: MorphoMesh pipeline standards and multi-component digital human requirements]
   ↳ [Logic Step 6]: Organize the entire asset into a strict, clean Blender Collection hierarchy:
                     Body, Hair, Dress, Footwear, Props_Magic, Armature, Lights_Camera.
```

---

## 3. Comprehensive Technical Specifications

### 3.1 PBR Shading Suite (Blender 4.5+ Principled BSDF v2)

#### A. Human Skin (`Mat_Human_Skin_YuNianAn`)
- **Shader Model**: Principled BSDF v2 (Cycles / EEVEE Next).
- **Subsurface Scattering**:
  - `Subsurface Method`: **Random Walk (Skin)**.
  - `Subsurface Weight`: **0.32** (Face/Neck), **0.25** (Limbs/Torso), **0.65** (Ears), **0.55** (Nostrils/Lips).
  - `Subsurface Radius`: `(1.0, 0.22, 0.11)` — Red light scatters up to 1.0 relative units (penetrating into vascular dermis), green scatters 0.22, blue scatters 0.11.
  - `Subsurface Scale`: `0.024` meters (24 mm mean free scattering path).
  - `Subsurface Anisotropy`: `0.75` (strong forward scattering simulating dense human cellular tissue).
  - `Subsurface IOR`: `1.40`.
- **Base Color Architecture**:
  - Base Porcelain Tone: `#F6E4DA` `(0.918, 0.791, 0.723, 1.0)`.
  - Cheek / Nose Blush Tone: `#E8A29A` `(0.791, 0.361, 0.318, 1.0)`.
  - Lip Vermilion Tone: `#C8686B` `(0.565, 0.133, 0.147, 1.0)`.
  - Blending: Layered via vertex color group `Col_Skin_Tones` or procedural mask.
- **Specular & Roughness**:
  - `Roughness`: Base face `0.48`, Forehead/Cheeks `0.42`, Nasal dorsum `0.35`, Lips `0.18`.
  - `Specular IOR Level`: `0.50` (corresponds to dielectric IOR 1.45).
  - `Coat Weight`: `0.0` (Skin), `0.70` (Lips & Inner Eye Caruncle).
  - `Coat Roughness`: `0.04` (high wet moisture gloss).
  - `Coat IOR`: `1.333` (water / saliva film).
- **Micro-Surface Bump**:
  - Procedural 3D Noise (Scale `380.0`, Detail `4.0`, Roughness `0.55`).
  - Normal Bump Node: Strength `0.030`, Distance `0.001` (extremely delicate velvet dermis, avoiding coarse adult pores).

#### B. Dual-Chamber Eye Optics (`Mat_Eye_Cornea_Sclera` & `Mat_Eye_Iris_Pupil`)
1. **Outer Cornea & Sclera Dome**:
   - `Geometry`: Convex spherical bulge extending 2.2mm proud of the eyeball sphere.
   - `Cornea Region`:
     - `Transmission Weight`: `1.0`.
     - `Roughness`: `0.012` (mirror optical finish).
     - `IOR`: **1.376** (exact anatomical refractive index of human cornea).
   - `Sclera Region`:
     - `Base Color`: `#F2F1F0` with subtle soft radial pink veins near outer corners.
     - `Roughness`: `0.08` (moist wet surface).
     - `Subsurface Weight`: `0.20`, Radius `(0.8, 0.3, 0.1)`.
   - `Limbus Blend`: 0.8mm gradient falloff between opaque sclera and crystal-clear cornea.

2. **Inner Concave Iris & Pupil**:
   - `Geometry`: Inverted parabolic bowl (dish-shaped, recessed 1.8mm behind cornea apex).
   - `Pupil Aperture`: Central concave aperture (`diameter = 3.8mm`), Base Color `#040405`, Roughness `0.95` (total light trap).
   - `Iris Stroma`:
     - Base Tone: Melancholic dark slate / charcoal `#2D343B` `(0.141, 0.165, 0.188, 1.0)`.
     - Inner Collarette Ring: `#424C55` `(0.223, 0.267, 0.301, 1.0)`.
     - Outer Limbal Ring: `#14171A` `(0.063, 0.075, 0.086, 1.0)`.
     - Radial Fibers: Procedural radial coordinate wave / Voronoi pattern (Strength `0.15`, Roughness `0.30`).
     - `Subsurface Weight`: `0.18` (simulating stroma tissue light diffusion).

3. **Tear Meniscus Strip (`Mat_Eye_TearMeniscus`)**:
   - Thin quad strip spanning lower eyelid margin and corneal junction.
   - `Transmission Weight`: `1.0`, `Roughness`: `0.01`, `IOR`: `1.333` (water film).

#### C. Mouth Interior & Teeth (`Mat_Teeth` & `Mat_Mouth_Interior`)
- **Teeth**: Enamel Base Color `#F5F3EB`, Roughness `0.18`, Subsurface Weight `0.35`, SSS Radius `(0.8, 0.8, 0.6)`, Scale `0.015`.
- **Mouth Interior & Tongue**: Base Color `#9E3338`, Roughness `0.22`, Coat Weight `0.65`, Coat Roughness `0.03`, SSS Weight `0.55`.

---

### 3.2 Geometry Nodes Hair Grooming System (Blender 4.5+ Hair Curves)

Yu Nian An's signature hairstyle consists of **6 distinct structural hair strata**:

| Layer Index | Hair Component | Guide Curves | Render Strands | Length (m) | Curvature / Styling Notes |
|:---|:---|:---:|:---:|:---:|:---|
| **L1** | Straight Bangs (Hime cut) | 350 | 14,000 | 0.12 - 0.14 | Straight downward fall from crown, trimmed evenly at eyebrow line (`Z = 8.85`), subtle fanning. |
| **L2** | Hime Sidelocks (Tóc mai) | 250 (x2) | 18,000 | 0.35 - 0.40 | Straight vertical locks flanking cheeks, falling down to chest (`Z = 7.50`), framing the jaw. |
| **L3** | Scalp Crown & Parting | 600 | 25,000 | 0.15 - 0.25 | Natural rounded skull contour with soft center-offset parting. |
| **L4** | Long Back Cascade | 1,200 | 48,000 | 0.85 - 1.05 | Cascades over scapulae and spine, draping down to mid-thigh (`Z = 3.80`), subtle clumping at ends. |
| **L5** | Baby Hair & Temples | 300 | 6,000 | 0.02 - 0.04 | Ultra-fine wisps around hairline, forehead edge, and behind ears. |
| **L6** | Eyebrows & Eyelashes | 300 + 400 | 4,000 | 0.008 - 0.015 | Soft melancholic arched brows; lush dark upper and lower lashes. |
| **Total** | **Full Hair System** | **~3,400** | **~115,000** | — | **Silky, flowing, production-density hair.** |

#### Geometry Nodes Modifier Node Tree (`GN_YuNianAn_HairGroom`)
1. **Surface Deform**: Pins hair root positions and orientations to the deforming skull scalp mesh.
2. **Interpolate Hair Curves**:
   - `Guide Curves`: Interpolates between guide curves using Poisson disk sampling.
   - `Density Mask`: Masked by vertex group `VG_Hair_Scalp`.
   - `Max Distance`: `0.008m`.
3. **Clump Hair Curves**:
   - `Clump Factor`: `0.28` (L4 Back Cascade), `0.15` (L1 Bangs), `0.20` (L2 Sidelocks).
   - `Clump Curve`: Root `0.0` -> Mid `0.25` -> Tip `0.70` (preserves smooth scalp volume while clumping strand tips organically).
4. **Hair Curve Noise / Frizz**:
   - `Noise Frequency`: `14.0`.
   - `Noise Amplitude`: `0.0012m` (imperceptible micro-waviness preventing synthetic CG stiffness).
5. **Hair Length & Taper Curve**:
   - `Trim Factor`: Length variation randomized by `± 4%`.
6. **Set Hair Curve Profile**:
   - `Shape`: Circular / Ribbon.
   - `Root Radius`: `0.00016m` (0.16 mm).
   - `Tip Radius`: `0.000025m` (0.025 mm, sharp natural taper).
7. **Set Material**: Assigns `Mat_Hair_JetBlack`.

#### Hair Material (`Mat_Hair_JetBlack`)
- **Shader Model**: Principled Hair BSDF (Chiang / Huang hair model).
- `Melanin Concentration`: **0.88** (deep natural jet-black with rich charcoal undertones).
- `Melanin Redness`: **0.12**.
- `Tint`: `#181A1D` `(0.075, 0.082, 0.090, 1.0)`.
- `Roughness`:
  - `Radial Roughness`: **0.22** (produces crisp, highly reflective specular highlights).
  - `Axial Roughness`: **0.30** (spreads light into the iconic silky "Angel Ring" halo across the crown).
- `Coat Weight`: **0.45** (smooth cosmetic conditioning sheen).
- `IOR`: **1.55**.

---

### 3.3 Wardrobe & Fabric Specifications

#### A. Garment Architecture & Mesh Geometry
1. **Sleeveless Bodice**:
   - Fitted contour spanning thoracic ribcage (`Z = 6.35` to `Z = 8.00`).
   - Neckline: Soft sweetheart scoop neckline dipping to `Z = 7.50`.
   - Straps: Twin flat ribbon straps (`width = 12mm`, `thickness = 1.0mm`) rising over clavicles and anchoring straight to the square back neckline (`Z = 7.60`).
   - Topology: 100% Quad-dominant mesh (`~1,200 quads`), edge loops following bust contours.

2. **High Waist Sash & Ribbon Belt**:
   - Position: Wrapped around empire waistline (`Z = 6.10` to `Z = 6.45`).
   - Belt Band: `40mm` wide fabric wrap with horizontal compression folds.
   - Ribbon Streamers: Twin vertical ribbon tails anchored at front center knot, cascading down `38cm` to `Z = 4.10`, fluttered slightly outward.

3. **Flared Pleated Skirt**:
   - Waist Connection: Seamlessly sewn to lower edge of waist sash (`Z = 6.10`).
   - Hemline: Flared bell silhouette terminating at `Z = 3.40` (settling right below the kneecap).
   - Pleating: 20 crisp soft box/knife pleats radiating outward from waist to hem.
   - Topology: Quad-mesh with radial edge flow (`~2,800 quads`), ready for cloth simulation or smooth armature skinning.

4. **Flat Slip-on Sandals (Dép Bệt)**:
   - Footbed Sole: Ergonomic flat sole (`thickness = 12mm`, length `23.5cm`), conforming to arch of foot.
   - Instep Strap: Single wide fabric/leather band (`width = 28mm`) arching over the metatarsal bones.
   - Exposed Regions: Bare toes, exposed medial/lateral arch, and exposed calcaneus heel.

#### B. Fabric Shaders
1. **White Silk Dress Fabric (`Mat_Dress_WhiteSilk`)**:
   - `Base Color`: Pure ivory white `#F7F8FA` `(0.945, 0.953, 0.965, 1.0)`.
   - `Roughness`: `0.60`.
   - `Sheen Weight`: `0.58` (velvety/silk microfiber reflection at grazing angles).
   - `Sheen Roughness`: `0.32`.
   - `Sheen Tint`: `#EDF2F8` `(0.890, 0.920, 0.960, 1.0)` (subtle cool ambient bounce).
   - `Subsurface Weight`: `0.14`, Radius `(0.8, 0.85, 0.9)`, Scale `0.012` (simulates delicate light translucency through white summer fabric).
   - `Micro-Bump`: Procedural weave texture (Scale `420.0`, Strength `0.025`).

2. **Waist Sash & Ribbon (`Mat_Sash_Satin`)**:
   - `Base Color`: Pale ice-blue satin tint `#DDE7F2` `(0.820, 0.880, 0.940, 1.0)`.
   - `Roughness`: `0.32` (smooth satin sheen).
   - `Specular IOR Level`: `0.60`.
   - `Anisotropy`: `0.45` oriented along the ribbon's length.

3. **Sandals (`Mat_Sandal_White`)**:
   - Sole: Matte off-white EVA/rubber `#EAEAEA`, Roughness `0.65`.
   - Strap: Soft white leather `#F6F6F8`, Roughness `0.38`, Bump Strength `0.04`.

---

### 3.4 Signature Magic Props: Marionette Red Strings & Luminous Butterflies

#### A. Marionette Red Strings (`Prop_Marionette_Strings`)
- **Geometry**: Procedural 3D Bezier Curve splines converted to bevel curves:
  - `Bevel Depth`: **0.00075m** (0.75 mm cross-section diameter).
  - `Resolution`: 6 perimeter segments, smooth shading.
- **Kinematic Anchoring**:
  - Tightly looped around the proximal interphalangeal joints of all 10 fingers:
    - Left Hand: `DEF-finger_thumb.02.L`, `DEF-finger_index.02.L`, `DEF-finger_middle.02.L`, `DEF-finger_ring.02.L`, `DEF-finger_pinky.02.L`.
    - Right Hand: `DEF-finger_thumb.02.R`, `DEF-finger_index.02.R`, `DEF-finger_middle.02.R`, `DEF-finger_ring.02.R`, `DEF-finger_pinky.02.R`.
  - From the fingertips, the strings extend downwards in taut, intersecting straight lines forming a dramatic puppeteer web, terminating near the skirt hemline (`Z = 3.50` to `2.80`).
- **Shader (`Mat_Marionette_RedString`)**:
  - `Base Color`: Vivid crimson `#E60026` `(0.902, 0.0, 0.149, 1.0)`.
  - `Roughness`: `0.25`.
  - `Emission Color`: Radiant cinnabar red `#FF1F3D` `(1.0, 0.122, 0.239, 1.0)`.
  - `Emission Strength`: **6.5** (produces intense bloom / glow in EEVEE Next and vivid light casting in Cycles raytracing).

#### B. Luminous White Butterflies (`Prop_Luminous_Butterflies`)
- **Morphology & Variations**:
  - 4 distinct modeled butterfly meshes:
    1. `Butterfly_Gliding`: Wings horizontally spread (`wingspan = 82mm`), resting or gliding.
    2. `Butterfly_Flapping_Up`: Wings raised at 45° angle in an upstroke.
    3. `Butterfly_Perched`: Wings folded vertically over thorax, perched on fingertips or strings.
    4. `Butterfly_Flapping_Bank`: Dynamic asymmetrical wings in a turning flutter.
  - Anatomy: Segmented head with curled proboscis and antennae; slender thorax; segmented abdomen; 4 distinct wing membranes (forewings and hindwings with swallowtail contours).
- **Swarm Staging & Choreography**:
  - 10 instanced butterflies distributed around Yu Nian An:
    - 2 butterflies perched directly on her left and right index/thumb fingertips.
    - 4 butterflies positioned along the taut red strings, as if caught or guiding the strings.
    - 4 butterflies ascending in a loose counter-clockwise spiral aura around her torso and head.
- **Shader (`Mat_Magic_Butterfly`)**:
  - `Base Color`: Pure pearl white `#FFFFFF` `(1.0, 1.0, 1.0, 1.0)`.
  - `Transmission Weight`: `0.20`.
  - `Subsurface Scattering`:
    - `Weight`: **0.45**.
    - `Radius`: `(0.9, 0.95, 1.0)` (cool white translucency).
    - `Scale`: `0.006m`.
  - `Emission Color`: Ethereal glowing white `#F2F7FF` `(0.949, 0.969, 1.0, 1.0)`.
  - `Emission Strength`: **3.2** (soft magical luminescence casting gentle white light onto the dress and hair).
  - `Thin-Film Iridescence`: Subtle clearcoat IOR `1.33`, coat roughness `0.02` simulating chitin shimmer.
  - `Wing Vein Alpha Mask`: Radial wing venation lines with 15% opacity modulation.

---

### 3.5 Blender Collections Hierarchy & Scene Organization

Conforming to industry standards and MorphoMesh pipeline architecture, the entire scene must be structured as follows:

```
Scene Collection
└── Yu_Nian_An_Master                     [Top-level character collection]
    ├── 01_Body                           [Anatomical meshes]
    │   ├── Mesh_Body_Base                [Single continuous manifold quad mesh: Head, Torso, Limbs, Hands, Feet]
    │   ├── Mesh_Eye_Left_CorneaSclera    [Outer refractive shell IOR 1.376]
    │   ├── Mesh_Eye_Right_CorneaSclera   [Outer refractive shell IOR 1.376]
    │   ├── Mesh_Eye_Left_IrisPupil       [Inner concave dish geometry]
    │   ├── Mesh_Eye_Right_IrisPupil      [Inner concave dish geometry]
    │   ├── Mesh_Eye_TearMeniscus         [Wet tear line strips]
    │   ├── Mesh_Teeth_Upper              [Upper dental arch]
    │   ├── Mesh_Teeth_Lower              [Lower dental arch]
    │   └── Mesh_Tongue                   [Articulated tongue geometry]
    │
    ├── 02_Hair                           [Blender 4.5+ Curves Groom system]
    │   ├── Hair_Hime_Bangs               [Straight fringe bangs curve object]
    │   ├── Hair_Hime_Sidelocks           [Left and right face-framing locks]
    │   ├── Hair_Scalp_Crown              [Crown volume and natural parting]
    │   ├── Hair_Back_Cascade             [Long cascading hair reaching mid-thigh]
    │   ├── Hair_Baby_Temples             [Micro flyaways along hairline]
    │   ├── Hair_Eyebrows                 [Left and right eyebrow curves]
    │   └── Hair_Eyelashes                [Upper and lower eyelash curves]
    │
    ├── 03_Dress                          [Costume meshes]
    │   ├── Mesh_Dress_Bodice             [Sleeveless bodice with shoulder straps]
    │   ├── Mesh_Dress_WaistSash          [High waist empire belt wrap]
    │   ├── Mesh_Dress_RibbonTails        [Front dangling ribbon streamers]
    │   └── Mesh_Dress_PleatedSkirt       [20-pleat flared A-line skirt]
    │
    ├── 04_Footwear                       [Minimalist footwear]
    │   ├── Mesh_Sandal_Left              [Left sole and instep strap]
    │   └── Mesh_Sandal_Right             [Right sole and instep strap]
    │
    ├── 05_Props_Magic                    [Signature magical artifacts]
    │   ├── Prop_Marionette_Strings       [Bevel curves anchored to 10 fingers, glowing red]
    │   └── Prop_Luminous_Butterflies     [Swarm of 10 instanced glowing butterflies]
    │       ├── Butterfly_Instance_01     [Perched Left Index]
    │       ├── Butterfly_Instance_02     [Perched Right Index]
    │       ├── Butterfly_Instance_03_06  [String travelers]
    │       └── Butterfly_Instance_07_10  [Ascending aura spiral]
    │
    ├── 06_Armature                       [Rigging & Animation]
    │   ├── Rig_Rigify_Human              [Final generated Rigify rig with 163 DEF bones & controls]
    │   └── Metarig_Human_Archive         [Original aligned metarig (hidden)]
    │
    └── 07_Lights_Camera                  [Beauty rendering studio setup]
        ├── Cam_FullBody_Front            [Front orthographic/perspective turnaround camera]
        ├── Cam_Front_3Quarter            [Canonical beauty shot camera (50mm lens)]
        ├── Cam_Facial_CloseUp            [Portrait camera (85mm lens)]
        ├── Light_Key_Softbox             [Warm 4800K key light at 45° front-left]
        ├── Light_Fill_Softbox            [Cool 6500K fill light at 45° front-right]
        ├── Light_Rim_HairLight           [Sharp 5600K rim light behind character for hair silhouette]
        └── Light_SSS_Backlight           [Dedicated back scatter light for skin/ear translucency]
```

---

## 4. Caveats

1. **Cycles Raytracing vs. EEVEE Next Real-Time Engine**:
   - The SSS `Random Walk (Skin)` algorithm delivers maximum anatomical fidelity in **Cycles**. In Blender 4.5+ **EEVEE Next**, subsurface scattering relies on Screen-Space Raytracing. Ensure that `Subsurface Scattering` and `Raytracing` are explicitly enabled in EEVEE Next render settings with a sample count $\ge 32$.
2. **Dual-Chamber Eye Refraction & Shadow Caustics**:
   - The outer cornea requires `Transmission = 1.0` with `IOR = 1.376`. In Cycles, ensure the cornea object has `Shadow Caustics` enabled or uses a transparent shadow ray switch (`Light Path -> Is Shadow Ray -> Transparent BSDF`) to prevent dark black shadow artifacts from falling across the inner iris.
3. **Geometry Nodes Hair Curves Evaluation**:
   - Generating 115,000 render strands in viewport can degrade interactive framerates. The Geometry Nodes modifier must expose an `Is Viewport` switch that decimates viewport density to `20%` (23,000 strands) while preserving `100%` (115,000 strands) for final rendering.
4. **Cloth Simulation vs. Armature Skinning for Pleated Skirt**:
   - For real-time turnaround and posing, the pleated skirt should be rigged directly to `DEF-thigh.01.L/R` with smooth Laplacian vertex weighting. For dynamic physical simulation, a secondary Cloth modifier with Pinning vertex group on the waist sash should be utilized.

---

## 5. Conclusion

The visual aesthetic specifications for **Yu Nian An (余念安)** have been exhaustively decoded from reference art `media_1788716034772.jpg` and mapped 1-to-1 into production-ready Blender 4.5+ technical pipelines. 

Every visual nuance—from her delicate melancholic gaze and porcelain skin translucency to her silky straight hime bangs, high-waisted pleated dress, glowing crimson marionette strings, and ethereal white butterflies—is mathematically defined with exact shader parameters, node architectures, curve counts, and collection hierarchies. 

These specifications provide the exact technical foundation for Milestone M2, where `human_materials.py`, `human_grooming.py`, and `wardrobe.py` will be programmatically compiled.

---

## 6. Verification Method

### 6.1 Automated Verification Script for Blender Environment
To verify that all specifications are correctly implemented in the `.blend` file, execute the following Python inspection test inside the Blender Python environment:

```python
"""
verify_yu_nian_an_aesthetics.py: Automated aesthetic & scene structure test.
Run via: blender --background yu_nian_an_master.blend --python verify_yu_nian_an_aesthetics.py
"""
import bpy

def test_collections_hierarchy():
    required_cols = [
        "Yu_Nian_An_Master",
        "01_Body",
        "02_Hair",
        "03_Dress",
        "04_Footwear",
        "05_Props_Magic",
        "06_Armature",
        "07_Lights_Camera",
    ]
    for col_name in required_cols:
        assert col_name in bpy.data.collections, f"Missing required collection: {col_name}"
    print("[PASS] Collection hierarchy verified.")

def test_skin_material():
    mat = bpy.data.materials.get("Mat_Human_Skin_YuNianAn")
    assert mat is not None, "Missing skin material 'Mat_Human_Skin_YuNianAn'"
    nodes = mat.node_tree.nodes
    principled = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    
    # Verify SSS settings
    assert principled.inputs["Subsurface Weight"].default_value >= 0.25, "SSS Weight too low"
    sss_radius = principled.inputs["Subsurface Radius"].default_value
    assert sss_radius[0] > sss_radius[1] > sss_radius[2], "SSS Radius must follow R > G > B penetration"
    print("[PASS] Skin PBR material verified.")

def test_eye_dual_chamber():
    cornea_mat = bpy.data.materials.get("Mat_Eye_Cornea_Sclera")
    iris_mat = bpy.data.materials.get("Mat_Eye_Iris_Pupil")
    assert cornea_mat is not None and iris_mat is not None, "Missing dual-chamber eye materials"
    
    cornea_bsdf = next(n for n in cornea_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    assert abs(cornea_bsdf.inputs["IOR"].default_value - 1.376) < 0.01, "Cornea IOR must be ~1.376"
    print("[PASS] Dual-chamber eye optics verified.")

def test_hair_curves_groom():
    hair_objs = [o for o in bpy.data.objects if o.type == 'CURVES']
    assert len(hair_objs) >= 4, f"Expected at least 4 hair curve layers, found {len(hair_objs)}"
    print("[PASS] Hair curves groom objects verified.")

def test_magic_props():
    strings_obj = bpy.data.objects.get("Prop_Marionette_Strings")
    butterflies_col = bpy.data.collections.get("05_Props_Magic")
    assert strings_obj is not None, "Missing Prop_Marionette_Strings object"
    assert len(butterflies_col.objects) >= 5, "Missing butterfly prop instances"
    
    # Check red emission shader
    string_mat = bpy.data.materials.get("Mat_Marionette_RedString")
    assert string_mat is not None, "Missing Mat_Marionette_RedString"
    emission = next(n for n in string_mat.node_tree.nodes if n.type == 'EMISSION')
    assert emission.inputs["Strength"].default_value >= 5.0, "String emission strength must be >= 5.0"
    print("[PASS] Magic props verified.")

if __name__ == "__main__":
    test_collections_hierarchy()
    test_skin_material()
    test_eye_dual_chamber()
    test_hair_curves_groom()
    test_magic_props()
    print("ALL VISUAL AESTHETIC & SCENE TESTS PASSED SUCCESSFULLY!")
```

### 6.2 Visual Inspection Protocol
1. Open the rendered view in Cycles (GPU compute, 256 samples, OpenImageDenoise).
2. Inspect the 4 camera angles:
   - `Cam_FullBody_Front`: Check vertical proportion matching scale 0-10 ruler, dress pleat symmetry, taut red strings spreading from all 10 fingers.
   - `Cam_Front_3Quarter`: Check SSS glow through earlobes and nose bridge; check dress contour and waist ribbon tie.
   - `Cam_Facial_CloseUp`: Check dual-chamber eye depth, cornea specular catchlight, straight hime bangs eyebrow alignment, and soft lip moisture.
   - `Cam_Turnaround_Rig`: Verify zero mesh clipping between hair curves, dress straps, and body geometry.
