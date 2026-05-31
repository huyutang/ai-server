import os
import sys
from huggingface_hub import snapshot_download

# Step 1: Set the environment variable to target the mirror network
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# Step 2: Define the target models and their specific directories
models_to_download = [
    {
        "repo_id": "Qwen/Qwen3.5-35B-A3B-FP8",
        "local_dir": "/Users/tom/projects/ai-server/models/Qwen3.5-35B-A3B-FP8"
    },
    {
        "repo_id": "Qwen/Qwen3.5-35B-A3B",
        "local_dir": "/Users/tom/projects/ai-server/models/Qwen3.5-35B-A3B"
    },
    {
        "repo_id": "casperhansen/deepseek-r1-distill-qwen-32b-awq",
        "local_dir": "/Users/tom/projects/ai-server/models/DeepSeek-R1-Distill-Qwen-32B-AWQ"
    }
]

def download_all_models():
    print("Initializing model downloads using the regional mirror proxy...")

    for model in models_to_download:
        repo = model["repo_id"]
        target_dir = model["local_dir"]

        print(f"\n{'='*60}")
        print(f"Starting Download: {repo}")
        print(f"Destination: {target_dir}")
        print(f"{'='*60}")

        try:
            # Using snapshot_download with required parameters
            snapshot_download(
                repo_id=repo,
                local_dir=target_dir,
                resume_download=True,             # Ensures paused downloads resume seamlessly
                local_dir_use_symlinks=False,    # Downloads the actual weights files straight to the path
                max_workers=4                    # Parallel file downlader worker thread limit
            )
            print(f"Successfully finished downloading: {repo}")

        except Exception as e:
            print(f"An error occurred while downloading {repo}: {e}", file=sys.stderr)
            print("You can safely rerun this script to pick up where it left off.", file=sys.stderr)

if __name__ == "__main__":
    download_all_models()
