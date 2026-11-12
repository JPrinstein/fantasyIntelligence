"""Download the chosen model into a persistent app-owned folder (never benchmark cache)."""
from pathlib import Path
from huggingface_hub import hf_hub_download

REPO = "unsloth/Qwen3.5-4B-GGUF"
FILE = "Qwen3.5-4B-Q4_K_M.gguf"
DEST = Path(__file__).resolve().parents[1] / "models" / "qwen35-4b-q4"

if __name__ == "__main__":
    DEST.mkdir(parents=True, exist_ok=True)
    print("Downloading", REPO, FILE, "to", DEST, flush=True)
    result = hf_hub_download(repo_id=REPO, filename=FILE, local_dir=str(DEST))
    print("Ready:", result, flush=True)
