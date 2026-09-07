import os
import subprocess
import tempfile
import pytest
from morphomesh.character_assembler import (
    MasterAssemblyConfig,
    YuNianAnAssembler,
    get_master_assembly_script,
    ALL_SEVEN_COLLECTIONS,
    MATERIAL_NAMES,
)

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
HAS_BLENDER = os.path.isfile(BLENDER_EXE)

def run_blender_script(script_text: str, blend_file: str = None) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", encoding="utf-8", delete=False) as f:
        f.write(script_text)
        script_path = f.name
    try:
        cmd = [BLENDER_EXE, "--background"]
        if blend_file and os.path.isfile(blend_file):
            cmd.append(blend_file)
        cmd.extend(["--python", script_path])
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return res
    finally:
        if os.path.exists(script_path):
            try:
                os.remove(script_path)
            except OSError:
                pass

class TestAdversarialCharacterAssembler:

    @pytest.mark.skipif(not HAS_BLENDER, reason="Blender 4.5 LTS not installed")
    def test_assembly_alternative_output_path_with_spaces_and_dirs(self, tmp_path):
        """Stress test: execute assembly with deep nested directory containing spaces."""
        custom_out = tmp_path / "Sub Dir With Spaces" / "Deep" / "Custom_Yu_Nian_An.blend"
        cfg = MasterAssemblyConfig(
            character_name="Yu_Nian_An_Test",
            output_blend_path=str(custom_out),
            cycles_samples=32,  # speed up test
        )
        script = get_master_assembly_script(cfg)
        assert len(script) > 5000
        
        # Execute in live Blender
        res = run_blender_script(script)
        assert res.returncode == 0, f"Blender execution failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        assert custom_out.exists(), f"Output blend was not created at {custom_out}"
        assert custom_out.stat().st_size > 1_000_000, "Blend file size unexpectedly small"

        # Verify contents of generated blend
        verify_script = f"""
import bpy
import sys
cols = [c.name for c in bpy.data.collections]
for ec in {list(ALL_SEVEN_COLLECTIONS)}:
    assert ec in cols, f"Missing collection: {{ec}}"
mats = [m.name for m in bpy.data.materials]
for em in {list(MATERIAL_NAMES)}:
    assert em in mats, f"Missing material: {{em}}"
arm = bpy.data.objects.get("Armature_Yu_Nian_An_Test_Rigify") or bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
assert arm is not None, "Armature not found"
def_bones = [b.name for b in arm.data.bones if b.name.startswith("DEF-")]
assert len(def_bones) == 163, f"Expected 163 DEF bones, got {{len(def_bones)}}"
print("STRESS_VERIFY_SUCCESS")
"""
        v_res = run_blender_script(verify_script, blend_file=str(custom_out))
        assert v_res.returncode == 0
        assert "STRESS_VERIFY_SUCCESS" in v_res.stdout

    @pytest.mark.skipif(not HAS_BLENDER, reason="Blender 4.5 LTS not installed")
    def test_assembly_dirty_scene_resilience(self, tmp_path):
        """Stress test: execute assembly in a dirty scene with foreign objects and collections."""
        dirty_blend = tmp_path / "dirty_startup.blend"
        dirty_out = tmp_path / "cleaned_output.blend"
        
        # 1. Create dirty startup blend
        setup_dirty = f"""
import bpy
c = bpy.data.collections.new("Rogue_Foreign_Collection")
bpy.context.scene.collection.children.link(c)
mesh = bpy.data.meshes.new("Foreign_Cube_Mesh")
obj = bpy.data.objects.new("Foreign_Cube", mesh)
c.objects.link(obj)
bpy.ops.wm.save_as_mainfile(filepath=r"{str(dirty_blend)}")
"""
        res_setup = run_blender_script(setup_dirty)
        assert res_setup.returncode == 0
        assert dirty_blend.exists()

        # 2. Run master assembly inside this dirty blend
        cfg = MasterAssemblyConfig(output_blend_path=str(dirty_out))
        script = get_master_assembly_script(cfg)
        res_assembly = run_blender_script(script, blend_file=str(dirty_blend))
        assert res_assembly.returncode == 0
        assert dirty_out.exists()

        # 3. Check that Yu_Nian_An_Master exists and contains expected tiers
        check_script = """
import bpy
master_col = bpy.data.collections.get("Yu_Nian_An_Master")
assert master_col is not None, "Root master collection missing"
assert len(master_col.children) == 6, f"Expected 6 children, got {len(master_col.children)}"
print("DIRTY_CLEANUP_SUCCESS")
"""
        res_check = run_blender_script(check_script, blend_file=str(dirty_out))
        assert res_check.returncode == 0
        assert "DIRTY_CLEANUP_SUCCESS" in res_check.stdout

    @pytest.mark.skipif(not HAS_BLENDER, reason="Blender 4.5 LTS not installed")
    def test_assembly_idempotency_double_execution(self, tmp_path):
        """Stress test: running the script twice in the same session does not crash or corrupt hierarchy."""
        idempotent_out = tmp_path / "idempotent.blend"
        cfg = MasterAssemblyConfig(output_blend_path=str(idempotent_out))
        script = get_master_assembly_script(cfg)
        
        # Execute script twice back-to-back in single python session
        double_script = f"""
# Run 1
{script}

# Run 2
{script}

import bpy
master_col = bpy.data.collections.get("Yu_Nian_An_Master")
assert master_col is not None
# Ensure collections didn't get .001 duplicated names
assert bpy.data.collections.get("01_Body.001") is None, "Collection duplicated as 01_Body.001"
print("IDEMPOTENCY_SUCCESS")
"""
        res = run_blender_script(double_script)
        assert res.returncode == 0, f"Double execution failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        assert "IDEMPOTENCY_SUCCESS" in res.stdout

    @pytest.mark.skipif(not HAS_BLENDER, reason="Blender 4.5 LTS not installed")
    def test_master_blend_arkit_shape_keys_empirical_deltas(self):
        """Assert every single one of the 52 ARKit FACS keys has measurable vertex delta displacement."""
        master_blend = "output/yu_nian_an/Yu_Nian_An_Master.blend"
        assert os.path.isfile(master_blend), f"Master blend not found: {master_blend}"

        check_script = """
import bpy
body = bpy.data.objects.get("Yu_Nian_An_Body")
assert body is not None, "Yu_Nian_An_Body not found"
sk = body.data.shape_keys
assert sk is not None, "No shape keys found on body"
basis = sk.key_blocks.get("Basis")
assert basis is not None, "Basis shape key missing"

basis_coords = [v.co.copy() for v in basis.data]
zero_delta_keys = []
delta_summary = {}

for kb in sk.key_blocks:
    if kb.name == "Basis":
        continue
    max_d = 0.0
    for i, v in enumerate(kb.data):
        d = (v.co - basis_coords[i]).length
        if d > max_d:
            max_d = d
    delta_summary[kb.name] = max_d
    if max_d < 1e-6:
        zero_delta_keys.append(kb.name)

print(f"Verified {len(delta_summary)} non-basis shape keys.")
assert len(zero_delta_keys) == 0, f"Empty/dummy shape keys found: {zero_delta_keys}"
assert len(delta_summary) == 52, f"Expected 52 ARKit keys, got {len(delta_summary)}"
print("ALL_52_SHAPE_KEYS_DEFORM_VERIFIED")
"""
        res = run_blender_script(check_script, blend_file=master_blend)
        assert res.returncode == 0, f"Shape keys inspection failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        assert "ALL_52_SHAPE_KEYS_DEFORM_VERIFIED" in res.stdout

    @pytest.mark.skipif(not HAS_BLENDER, reason="Blender 4.5 LTS not installed")
    def test_master_blend_def_bones_163_exact_inventory(self):
        """Assert all 163 DEF bones match exact Rigify human naming pattern and symmetry."""
        master_blend = "output/yu_nian_an/Yu_Nian_An_Master.blend"
        check_script = """
import bpy
arm = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
assert arm is not None, "Armature object missing"
def_bones = [b.name for b in arm.data.bones if b.name.startswith("DEF-")]
assert len(def_bones) == 163, f"Expected 163 DEF bones, got {len(def_bones)}"

# Check left-right symmetry for bilateral bones
left_bones = [b for b in def_bones if b.endswith(".L")]
right_bones = [b for b in def_bones if b.endswith(".R")]
assert len(left_bones) == len(right_bones), f"Asymmetry: {len(left_bones)} left vs {len(right_bones)} right"

# Check every left bone has a corresponding right bone
for lb in left_bones:
    rb = lb[:-2] + ".R"
    assert rb in def_bones, f"Missing right counterpart for {lb}"

print("DEF_BONES_163_SYMMETRY_VERIFIED")
"""
        res = run_blender_script(check_script, blend_file=master_blend)
        assert res.returncode == 0, f"DEF bones inspection failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        assert "DEF_BONES_163_SYMMETRY_VERIFIED" in res.stdout

    @pytest.mark.skipif(not HAS_BLENDER, reason="Blender 4.5 LTS not installed")
    def test_master_blend_cameras_50mm_and_ndc_framing(self):
        """Assert Camera_FullBody and turnaround cameras have lens 50.0mm and valid NDC framing."""
        master_blend = "output/yu_nian_an/Yu_Nian_An_Master.blend"
        check_script = """
import bpy
from bpy_extras.object_utils import world_to_camera_view

scene = bpy.context.scene
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080

body = bpy.data.objects['Yu_Nian_An_Body']
verts = [body.matrix_world @ v.co for v in body.data.vertices]

# Assert Camera_FullBody has 50mm focal length
cam_fb = bpy.data.objects['Camera_FullBody']
assert cam_fb.data.lens == 50.0, f"Expected 50.0mm lens, got {cam_fb.data.lens}"

cams_to_test = ['Camera_FullBody', 'Camera_Front', 'Camera_ThreeQuarter', 'Camera_Profile', 'Camera_Back']
for c_name in cams_to_test:
    cam = bpy.data.objects[c_name]
    assert cam.data.lens == 50.0, f"{c_name} lens is not 50.0mm"
    ndc = [world_to_camera_view(scene, cam, v) for v in verts if (world_to_camera_view(scene, cam, v)).z > 0]
    min_y = min(c.y for c in ndc)
    max_y = max(c.y for c in ndc)
    assert min_y >= 0.05, f"Foot amputation in {c_name}: min_y={min_y:.4f} < 0.05"
    assert max_y <= 0.95, f"Head decapitation in {c_name}: max_y={max_y:.4f} > 0.95"

print("CAMERAS_50MM_AND_NDC_FRAMING_VERIFIED")
"""
        res = run_blender_script(check_script, blend_file=master_blend)
        assert res.returncode == 0, f"Camera framing inspection failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        assert "CAMERAS_50MM_AND_NDC_FRAMING_VERIFIED" in res.stdout

    @pytest.mark.skipif(not HAS_BLENDER, reason="Blender 4.5 LTS not installed")
    def test_master_blend_strings_and_clearance_adversarial(self):
        """Assert marionette strings snapped to bone tails and wardrobe clearance >= +4mm with 0 penetration."""
        master_blend = "output/yu_nian_an/Yu_Nian_An_Master.blend"
        check_script = """
import bpy
import bmesh
import mathutils

arm = bpy.data.objects['Armature_Yu_Nian_An_Rigify']
strings = bpy.data.objects['Prop_Marionette_Strings']

finger_bones = [
    "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
    "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
]

verts_per_cord = 14
for cord_i, b_name in enumerate(finger_bones):
    bone = arm.data.bones[b_name]
    tail_world = arm.matrix_world @ bone.tail_local
    v0 = strings.matrix_world @ strings.data.vertices[cord_i * verts_per_cord].co
    v1 = strings.matrix_world @ strings.data.vertices[cord_i * verts_per_cord + 1].co
    center = (v0 + v1) * 0.5
    dist = (center - tail_world).length
    assert dist < 0.005, f"String {cord_i} detached from {b_name}: dist={dist*1000:.2f}mm >= 5mm"

body = bpy.data.objects['Yu_Nian_An_Body']
bm_body = bmesh.new()
bm_body.from_mesh(body.data)
bm_body.transform(body.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_body)

for part_name in ['Mesh_Dress_Bodice', 'Mesh_Dress_WaistSash']:
    obj = bpy.data.objects[part_name]
    verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    min_signed = float('inf')
    penetrations = 0
    for v in verts:
        loc, normal, _, dist = bvh.find_nearest(v)
        if loc is not None:
            dot = (v - loc).dot(normal)
            signed = dist if dot >= 0 else -dist
            if signed < min_signed:
                min_signed = signed
            if dot < 0:
                penetrations += 1
    assert penetrations == 0, f"{part_name} has {penetrations} penetrations"
    assert min_signed >= 0.004, f"{part_name} clearance: {min_signed*1000:.2f}mm < 4mm"

print("STRINGS_AND_CLEARANCE_ADVERSARIAL_VERIFIED")
"""
        res = run_blender_script(check_script, blend_file=master_blend)
        assert res.returncode == 0, f"Strings and clearance inspection failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        assert "STRINGS_AND_CLEARANCE_ADVERSARIAL_VERIFIED" in res.stdout
