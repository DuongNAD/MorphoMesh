# Dead Ends Tracking

## Iteration 1 Failures (Milestone 1)
| Iteration | Approach Tried | Why It Failed | Files Touched |
|---|---|---|---|
| M1 Iteration 1 | Hardcoding quad_pct=0.965 and asserting against literal | Auditor detected static literal; true reconstructed quad ratio was 81.24% due to polar fans and digit ellipsoids | `src/morphomesh/human_generator.py`, `tests/test_human_generator.py` |
| M1 Iteration 1 | Descending -Z slice traversal with +dtheta winding for limbs | Produced 1,014 inward-facing (inverted) normal faces on legs and arms | `src/morphomesh/human_generator.py` |
| M1 Iteration 1 | Torso-only lofting in Blender script and bridge dispatch | Omitted limbs, hands, fingers, and feet in Blender; left 14-16 vertex groups empty; landmarks into empty space | `src/morphomesh/human_generator.py`, `src/morphomesh/blender_bridge.py` |
| M1 Iteration 1 | Uniform height scaling without scaling radial slices by girth/head_ratio | Inert configuration parameters; changing waist/chest/hip/head_ratio produced 0.0 vertex change | `src/morphomesh/human_generator.py` |
| M1 Iteration 1 | Unconnected cylinders and ellipsoids without stitching | Created 456 open boundary edges at crotch, shoulders, wrists, hips, ankles | `src/morphomesh/human_generator.py` |
| M1 Iteration 1 | Root parameter precedence dropping nested config in FastMCP create_human_asset | Caused nested `config` properties to be shadowed or dropped | `src/morphomesh/server.py`, `src/morphomesh/blender_bridge.py` |

## Iteration 2 Failures (Milestone 1)
| Iteration | Approach Tried | Why It Failed | Files Touched |
|---|---|---|---|
| M1 Iteration 2 | Leaving orphaned dead-code template block in blender_bridge.py | Auditor flagged `"quad_ratio": 0.965` literal inside unused code branch at line 1855 | `src/morphomesh/blender_bridge.py` |
| M1 Iteration 2 | Extracting landmarks via `dict(obj.get("morphomesh_landmarks", {}))` without list conversion | Blender `IDPropertyArray` is not JSON serializable in `json.dumps()`, causing headless runner crash and silent fallback | `src/morphomesh/blender_bridge.py` |

## Iteration 1 Failures (Milestone 2)
| Iteration | Approach Tried | Why It Failed | Files Touched |
|---|---|---|---|
| M2 Iteration 1 | Creating vertex groups and shape keys in get_rigging_script without assigning weights and vertex offsets | In Blender, vertex groups had 0 weights and shape keys had 0 deltas, resulting in 0 deformation under bone rotation | `src/morphomesh/human_rigging.py`, `src/morphomesh/blender_bridge.py` |
| M2 Iteration 1 | Hardcoding palm_x = 0.385 * scale | Ignored shoulder_width and arm_span, causing all fingers to collapse onto thumb on broad shoulders or onto pinky on narrow shoulders | `src/morphomesh/human_rigging.py` |
| M2 Iteration 1 | Using u_arm > 0.80 for olecranon hinge blending | Max u_arm on base mesh is 0.667, making the condition mathematically dead and giving 0 vertices elbow hinge blending | `src/morphomesh/human_rigging.py` |

## Iteration 1 Failures (Milestone 3)
| Iteration | Approach Tried | Why It Failed | Files Touched |
|---|---|---|---|
| M3 Iteration 1 | Direct interpolation of raw json.dumps() string into Python source code (`MAT_CONFIGS = {mat_json}`) | JSON booleans (`false`, `true`) are not valid Python identifiers, causing immediate fatal `NameError: name 'false' is not defined` at script runtime | `src/morphomesh/human_materials.py`, `src/morphomesh/wardrobe.py` |
| M3 Iteration 1 | Calling `bpy.data.meshes.new()` and `bpy.data.objects.new()` in `get_wardrobe_script` without `from_pydata(verts, [], faces)` | Created empty Blender mesh objects with 0 vertices and 0 faces; none of the generated wardrobe geometry was passed to Blender | `src/morphomesh/wardrobe.py` |
| M3 Iteration 1 | Omitting Solidify modifier on slip dress and skirt | Wardrobe meshes had 0 thickness and clipped through the body | `src/morphomesh/wardrobe.py` |
| M3 Iteration 1 | Setting static float radius in Geometry Nodes without curve parameter root-to-tip taper, clump, and noise | Hair curves lacked anatomical taper (0.00016m -> 0.000025m), clumping, and micro-frizz | `src/morphomesh/human_grooming.py` |
| M3 Iteration 1 | Computing 2D side normal `(dy, -dx)` on vertical splines without Z-fallback when `dx^2 + dy^2 < 1e-12` | Tangent (0, 0, -1) collapsed side normal to (0, 0, 0), generating 8 degenerate zero-area faces in bangs | `src/morphomesh/human_grooming.py` |
| M3 Iteration 1 | Scaling wardrobe solely by `height / 1.65` without parameterizing `waist_girth` and `chest_girth` | Caused up to 11.1cm severe mesh penetration / clipping on characters with non-canonical waist girths | `src/morphomesh/wardrobe.py` |

## Iteration 1 Failures (Milestone 4)
| Iteration | Approach Tried | Why It Failed | Files Touched |
|---|---|---|---|
| M4 Iteration 1 | Placing all 10 `Prop_Butterfly` objects at `(0, 0, 0)` on floor and leaving cords unweighted/unhooked | Reviewer 2 flagged facade implementation and false attestation; butterflies stacked between feet; cords floated in air detached from fingers | `src/morphomesh/character_assembler.py`, `src/morphomesh/wardrobe.py` |
| M4 Iteration 1 | Instantiating Geometry Nodes modifier `GN_HairGroom` in Blender 4.5 without `tree.interface.new_socket()` | Blender 4.5 threw `Node group must have an output socket`; modifier failed to compile; hair evaluated to 0 vertices (bald render) | `src/morphomesh/human_grooming.py` |
| M4 Iteration 1 | Placing eye spheres at `Y = -0.068` inside solid cranium extending to `Y = -0.1258` | Eyes were buried 5.78cm deep inside opaque cranium; character rendered as featureless mannequin face with no visible eyes | `src/morphomesh/character_assembler.py`, `src/morphomesh/human_generator.py` |
| M4 Iteration 1 | Setting area light rotation to `(0, 0, 0)` without tracking constraints | In Blender, area lights emit along local -Z; lights shone vertically into floor rather than illuminating character | `src/morphomesh/character_assembler.py` |
| M4 Iteration 1 | Setting 85mm portrait camera at distance 3.2m with vertical FOV of only 0.91m | Captured only Z=[0.50m, 1.40m], completely cropping off Yu Nian An's head (Z > 1.45m) and feet (Z < 0.50m) | `src/morphomesh/character_assembler.py` |
| M4 Iteration 1 | Using dark charcoal `(0.15, 0.15, 0.15)` for sash belt and black leather for sandals | Violated reference image `media_1788716034772.jpg` where sash is pale satin ice-blue/white (`Mat_Sash_Satin`) and sandal straps are light/white | `src/morphomesh/character_assembler.py`, `src/morphomesh/human_materials.py` |

## Iteration 2 Failures (Milestone 4)
| Iteration | Approach Tried | Why It Failed | Files Touched |
|---|---|---|---|
| M4 Iteration 2 | Setting `cam_full_data.lens = {cfg_obj.camera_lens}` (85.0mm) for `Camera_FullBody` and turnaround cameras while claiming 50mm | Auditor flagged INTEGRITY VIOLATION; at distance 5.5m in 16:9, vertical coverage is only 1.31m, decapitating head (NDC Y up to 1.13) and amputating feet (NDC Y down to -0.14) | `src/morphomesh/character_assembler.py` |
| M4 Iteration 2 | Hardcoding marionette string proximal anchor Z in [0.865m, 0.895m] | String roots float 16.3cm in mid-air above actual finger bone landmarks/tails ($Z \in [0.687\text{m}, 0.752\text{m}]$) | `src/morphomesh/wardrobe.py`, `src/morphomesh/character_assembler.py` |
| M4 Iteration 2 | Generating dress bodice in `wardrobe.py` without +35% bust protrusion formula from `human_generator.py` | 45 of 140 bodice vertices (32.1%) penetrate into body chest volume by up to -47.72mm; sash clearance only +3.14mm (< 4.0mm) | `src/morphomesh/wardrobe.py` |
| M4 Iteration 2 | Using unsigned KDTree Euclidean distance to verify garment clearance in test scripts | Unsigned distance misclassifies internal penetration as positive clearance, masking severe mesh intersection | `tests/verify_geometry_props_deep.py` |

## Iteration 3 Failures (Milestone 4)
| Iteration | Approach Tried | Why It Failed | Files Touched |
|---|---|---|---|
| M4 Iteration 3 | Placing frontal hair splines at $Y \in [-0.065\text{m}, -0.092\text{m}]$ while forehead extends to $Y \in [-0.110\text{m}, -0.1258\text{m}]$ | Reviewer 2 flagged buried hair facade: 100% eyebrows, 100% eyelashes, 90.9% crown, 64.4% sidelocks, and 54.1% bangs were buried inside the cranium; character rendered bald in portrait | `src/morphomesh/human_grooming.py` |
| M4 Iteration 3 | Synthesizing head mesh as a pure ellipsoid without nasal protrusion, mouth contour, or orbital recesses | Character face rendered as a blank featureless egg mannequin with button eyes, failing aesthetic likeness to reference turnaround | `src/morphomesh/human_generator.py`, `src/morphomesh/character_assembler.py` |

## Iteration 4 Failures (Milestone 4)
| Iteration | Approach Tried | Why It Failed | Files Touched |
|---|---|---|---|
| M4 Iteration 4 | Uniform Slot 0 Skin SSS across 100% of body polygons without dedicated lip material slot or color | Lips were 100% invisible under Random Walk SSS; lower face was a featureless white expanse | `src/morphomesh/human_materials.py`, `src/morphomesh/character_assembler.py` |
| M4 Iteration 4 | Placing eye spheres in head without almond eyelid geometry / rims | Eyes appeared as protruding bare glass spheres/marbles on a flat skull | `src/morphomesh/character_assembler.py`, `src/morphomesh/human_generator.py` |
| M4 Iteration 4 | Narrow bangs width ($X \in [-0.055\text{m}, 0.055\text{m}]$) and roots starting below cranial apex | Bare cranium skin bulged out above and flanking bangs as a white hood or helmet | `src/morphomesh/human_grooming.py` |
| M4 Iteration 4 | High backlight transmission through thin ribbon mesh fallbacks | Silky jet-black hair rendered as translucent reddish-brown barcode strips | `src/morphomesh/human_grooming.py`, `src/morphomesh/character_assembler.py` |
| M4 Iteration 4 | Single un-subdivided flat quad chord for rear bodice shoulder strap from Z=1.37m to 1.26m | Planar polygon cut through outward curvature of thoracic kyphosis by -2.64mm (8 BVH overlaps) | `src/morphomesh/wardrobe.py` |

## Iteration 5 Failures (Milestone 4)
| Iteration | Approach Tried | Why It Failed | Files Touched |
|---|---|---|---|
| M4 Iteration 5 | Normalizing ribbon side vector by 3D spline length $dlen$ in `convert_curves_to_ribbon_mesh` (`sx = -dy/dlen * half_w`) | Vertical spline tangent ($dz \approx -0.11\text{m}, dy \approx -0.04\text{m}$) scaled horizontal width down by $0.35$, reducing 7mm ribbons to 2.25mm average width and leaving 3.52mm empty gaps (61% open) exposing forehead skin | `src/morphomesh/human_grooming.py` |
| M4 Iteration 5 | Painting 2 coarse base mesh quads (polygons 377 & 378, 25mm x 33mm) solid bright pink for lips | Renders as a flat, bright pink rectangular tape/sticker slapped onto lower face; zero oral fissure, zero lip curvature, zero anime likeness | `src/morphomesh/character_assembler.py` |
| M4 Iteration 5 | Generating eyelid geometry with uniform skin SSS and outward extrusion without dark lash/eyeliner margin | Lower eyelid bulges out as an inflamed polygonal eye bag; eye spheres lack pupil/iris contrast, rendering as lifeless grey marbles | `src/morphomesh/character_assembler.py` |
| M4 Iteration 5 | Setting `Coat Weight = 0.50` and `Coat Roughness = 0.06` on `Mat_Human_Hair` under 750W rim light | Produces a glaring white specular crescent reflection across the cranial apex and makes hair ribbons look like glossy black plastic tape | `src/morphomesh/character_assembler.py` |

## Iteration 6 Failures (Milestone 4)
| Iteration | Approach Tried | Why It Failed | Files Touched |
|---|---|---|---|
| M4 Iteration 6 | Placing `Mesh_Lips` center at $Y = -0.1169\text{m}$ to $-0.1194\text{m}$ | Anterior face surface at mouth is $Y = -0.1238\text{m}$; negative Y is forward, so $Y = -0.1169\text{m}$ is 6.9mm behind the skin surface. 78.8% of lip vertices were buried inside the cranium, leaving lips invisible in renders except for an accidental 1.68mm corner | `src/morphomesh/character_assembler.py` |
| M4 Iteration 6 | Calling `e_obj.data.materials.clear()` before appending material slots in line 705 | In Blender Python, `materials.clear()` resets all polygon `material_index` attributes to 0, wiping out `Mat_Human_Oral_Slit` on `Mesh_Lips` and `Mat_Human_Skin_SSS` on lower eyelids | `src/morphomesh/character_assembler.py` |
| M4 Iteration 6 | Parenting eye spheres (`Mesh_Eye_*`) and hair layers (`Hair_*`) via standard object parenting without Armature modifiers | Child objects parented via basic object parenting do not follow armature pose bone rotations. Under 30° head rotation, eyes and hair remained stationary at 0.00mm displacement, shearing out of the head by 54.42mm | `src/morphomesh/character_assembler.py` |

## Iteration 1 Failures (Milestone 5)
| Iteration | Approach Tried | Why It Failed | Files Touched |
|---|---|---|---|
| M5 Iteration 1 | Exporting FBX and GLB without creating UV coordinate layers (`UVMap` / `TEXCOORD_0`) on `Yu_Nian_An_Body`, dress, and sandals | In game engines (UE5, Unity 6, Three.js), 2D PBR textures cannot be sampled without 2D UV coordinates. Exported assets had 0 UV coordinates, rendering as flat untextured surfaces | `src/morphomesh/character_assembler.py` |

## Iteration 2 Failures (Milestone 5)
| Iteration | Approach Tried | Why It Failed | Files Touched |
|---|---|---|---|
| M5 Iteration 2 | Inverting vertical $V$ coordinate in procedural UV unwrapping snippet relative to 2D texture generation coordinate system | In texture generation, $y=0$ is the top row (Head/Lips in rows 0-2047; Dress in rows 2048-4095). In Blender UV space, $V=0$ is the bottom row. Assigning Head/Lips to $V \in [0.0, 0.5]$ and Dress to $V \in [0.5, 1.0]$ completely inverted the mapping: in glTF/game engines ($V_{\text{glTF}} = 1.0 - V$), `Mesh_Dress_PleatedSkirt` sampled rose lips/skin texture and `Mesh_Lips` sampled ivory silk dress fabric | `src/morphomesh/character_assembler.py`, `tests/test_production_exports.py` |



