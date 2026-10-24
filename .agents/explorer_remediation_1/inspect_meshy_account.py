import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("MESHY_API_KEY")

url = "https://api.meshy.ai/openapi/v2/text-to-3d?pageNum=1&pageSize=100"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode("utf-8"))

print(f"Total tasks on account: {len(res)}")
for i, item in enumerate(res):
    task_id = item.get("id")
    mode = item.get("mode")
    status = item.get("status")
    progress = item.get("progress")
    prompt = item.get("prompt", "")
    created_at = item.get("created_at")
    print(f"[{i:02d}] id={task_id} mode={mode} status={status} progress={progress} prompt={prompt[:70]}")
