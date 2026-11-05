import os
import sys

from huggingface_hub import HfApi

token = os.environ.get("HF_TOKEN")
user = os.environ.get("HF_USER")
ui = os.environ.get("HF_CLIENT", "asr-ui")
if not token or not user:
    sys.exit("нужны HF_TOKEN и HF_USER")

api = HfApi(token=token)
repo = f"{user}/{ui}"
api.create_repo(repo, repo_type="space", space_sdk="static", exist_ok=True)
api.upload_folder(folder_path="web", repo_id=repo, repo_type="space")
print("UI=https://" + user.lower() + "-" + ui.lower() + ".hf.space")
