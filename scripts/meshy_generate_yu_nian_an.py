import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

API_KEY = os.environ.get('MESHY_API_KEY', 'msy_3EH0wmTqFmJQm3RJcpbXxc26b96yVcXK37x6')
HEADERS = {
    'Authorization': f'Bearer {API_KEY}',
    'User-Agent': 'MorphoMesh-Pipeline/2.0',
    'Content-Type': 'application/json',
}

def generate_3d_from_concept():
    concept_path = r'E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Gemini_Concept.jpg'
    if not os.path.isfile(concept_path):
        print(f'Error: {concept_path} not found!')
        return

    print('=' * 70)
    print('PHASE 2: CLOUD IMAGE-TO-3D VIA MESHY AI API')
    print('=' * 70)
    print(f'Loading concept art: {concept_path} ({os.path.getsize(concept_path):,} bytes)')

    with open(concept_path, 'rb') as f:
        b64_data = base64.b64encode(f.read()).decode('ascii')
    data_uri = f'data:image/jpeg;base64,{b64_data}'

    payload = {
        'image_url': data_uri,
        'enable_pbr': True,
        'should_remesh': True,
        'topology': 'quad',
        'target_polycount': 30000,
    }

    print('[1/3] Submitting task to Meshy API (POST /openapi/v1/image-to-3d)...')
    req = urllib.request.Request(
        'https://api.meshy.ai/openapi/v1/image-to-3d',
        data=json.dumps(payload).encode('utf-8'),
        headers=HEADERS,
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_data = json.loads(resp.read().decode('utf-8'))
            task_id = resp_data.get('result') or resp_data.get('id')
            print(f'Task successfully created! Task ID: {task_id}')
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='replace')
        print(f'HTTP Error {e.code}: {e.reason}\nDetails: {err_body}')
        return
    except Exception as e:
        print(f'Request error: {e}')
        return

    # Poll status
    print('[2/3] Polling generation status...')
    poll_url = f'https://api.meshy.ai/openapi/v1/image-to-3d/{task_id}'
    start_time = time.time()
    last_progress = -1

    while True:
        try:
            req_poll = urllib.request.Request(poll_url, headers=HEADERS)
            with urllib.request.urlopen(req_poll, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f'Poll notice: {e}')
            time.sleep(3)
            continue

        status = data.get('status', 'PENDING')
        progress = data.get('progress', 0)

        if progress != last_progress:
            elapsed = round(time.time() - start_time, 1)
            print(f' - [{elapsed}s] Status: {status} | Progress: {progress}%')
            last_progress = progress

        if status == 'SUCCEEDED':
            elapsed = round(time.time() - start_time, 1)
            print(f'\n[OK] Meshy 3D generation SUCCEEDED in {elapsed}s!')
            break
        elif status in ('FAILED', 'CANCELED'):
            err = data.get('task_error', {}).get('message', 'Unknown failure')
            print(f'\n[FAIL] Meshy task failed: {err}')
            return

        time.sleep(3)

    # Download GLB and assets
    print('[3/3] Downloading generated 3D assets...')
    model_urls = data.get('model_urls', {})
    glb_url = model_urls.get('glb')
    if not glb_url:
        print('Error: glb URL not found in model_urls!')
        print('Available URLs:', model_urls)
        return

    out_dir = r'E:\tool\mcp\MorphoMesh\output\yu_nian_an'
    out_glb = os.path.join(out_dir, 'Yu_Nian_An_Meshy.glb')
    dl_req = urllib.request.Request(glb_url, headers={'User-Agent': 'MorphoMesh-Download/2.0'})
    with urllib.request.urlopen(dl_req, timeout=60) as resp, open(out_glb, 'wb') as f:
        f.write(resp.read())

    print(f'Downloaded GLB: {out_glb} ({os.path.getsize(out_glb):,} bytes)')
    
    # Save metadata JSON
    meta_path = os.path.join(out_dir, 'Yu_Nian_An_Meshy_meta.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f'Saved task metadata: {meta_path}')

if __name__ == '__main__':
    generate_3d_from_concept()
