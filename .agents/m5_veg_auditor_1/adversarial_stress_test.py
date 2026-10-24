
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, 'teamwork_projects/vegetation_library')
from vegetation_pipeline.validator import validate_geometry, validate_static_mesh_invariants, validate_pbr_textures

print('Running Adversarial Stress-Tests on validator.py...')

# Test 1: Floating roots
pos = np.ones((5000, 3), dtype=np.float32)
pos[:, 2] += 1.0
norms = np.tile(np.array([0.0, 0.0, 1.0], dtype=np.float32), (5000, 1))
tri = np.arange(4998, dtype=np.int32).reshape(-1, 3)
checks, metrics, errors, _ = validate_geometry(pos, norms, tri)
assert not checks['ground_contact_base_aligned'], 'Failed to catch floating roots!'
print('Test 1: Floating roots caught correctly: PASS')

# Test 2: Low vertex count
pos_cube = np.zeros((8, 3), dtype=np.float32)
norms_cube = np.tile(np.array([0.0, 0.0, 1.0], dtype=np.float32), (8, 1))
tri_cube = np.array([[0, 1, 2]], dtype=np.int32)
checks, metrics, errors, _ = validate_geometry(pos_cube, norms_cube, tri_cube)
assert not checks['vertex_count_budget'], 'Failed to catch low vertex count!'
print('Test 2: Vertex budget underflow caught correctly: PASS')

# Test 3: NaN coordinates
pos_nan = np.zeros((4000, 3), dtype=np.float32)
pos_nan[10, 0] = np.nan
checks, metrics, errors, _ = validate_geometry(pos_nan, norms, tri[:1333])
assert not checks['zero_nan_inf_coordinates'], 'Failed to catch NaN coordinates!'
print('Test 3: NaN coordinates caught correctly: PASS')

# Test 4: Skeletal rigging injection
gltf_rigged = {'skins': [{'joints': [0, 1]}], 'nodes': [{'skin': 0}]}
checks, metrics, errors, _ = validate_static_mesh_invariants(gltf_rigged)
assert not checks['n_bones_strictly_zero'], 'Failed to catch injected armature!'
print('Test 4: Injected armature caught correctly: PASS')

# Test 5: Solid black albedo
from PIL import Image
black_img = Image.new('RGB', (512, 512), (0, 0, 0))
normal_img = Image.new('RGB', (512, 512), (128, 128, 255))
rough_img = Image.new('L', (512, 512), 128)
metal_img = Image.new('L', (512, 512), 0)
embedded = {'albedo': black_img, 'normal': normal_img, 'roughness': rough_img, 'metallic': metal_img}
checks, metrics, errors, _ = validate_pbr_textures(textures_dir=None, embedded_images=embedded)
assert not checks['texture_albedo_plausible'], 'Failed to catch solid black albedo!'
print('Test 5: Solid black albedo caught correctly: PASS')

# Test 6: High metallic
metal_high = Image.new('L', (512, 512), 240)
alb_good = Image.new('RGB', (512, 512), (80, 120, 50))
embedded_metal = {'albedo': alb_good, 'normal': normal_img, 'roughness': rough_img, 'metallic': metal_high}
checks, metrics, errors, _ = validate_pbr_textures(textures_dir=None, embedded_images=embedded_metal)
assert not checks['texture_metallic_dielectric'], 'Failed to catch high metallic foliage!'
print('Test 6: Conductive metal foliage caught correctly: PASS')

print('ALL 6 ADVERSARIAL STRESS-TESTS PASSED EMPIRICALLY! ZERO FALSE PASSES.')
