import os
import urllib.request
import json
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
    prompt = item.get("prompt", "")[:70]
    print(f"[{i+1}] id={task_id} mode={mode} status={status} prompt={prompt}")
