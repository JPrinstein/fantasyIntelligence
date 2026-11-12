"""Conservative model-cache accounting and targeted Hugging Face deletion."""
from pathlib import Path


def checked_hub_path(root):
    """Reject symlinked cache roots and any unexpected path redirection."""
    root = Path(root)
    if root.is_symlink() or (root / "hub").is_symlink():
        raise ValueError("Benchmark cache root must not be a symlink")
    hub = root / "hub"
    if hub.exists() and not hub.is_dir():
        raise ValueError("Benchmark HF cache path is not a directory")
    return hub


def directory_size_bytes(root):
    """Count only regular files directly under the designated root."""
    import os
    total = 0
    if not Path(root).exists():
        return 0
    for directory, subdirs, files in os.walk(root, followlinks=False):
        subdirs[:] = [name for name in subdirs if not (Path(directory) / name).is_symlink()]
        for name in files:
            path = Path(directory) / name
            if not path.is_symlink():
                try:
                    total += path.stat().st_size
                except FileNotFoundError:
                    pass
    return total


def cleanup_repo(benchmark_cache_root, model_id):
    """Remove only a specific HF repo's revisions from the benchmark-owned cache.

    Does not touch the user's default HF cache, another model, or result logs.
    """
    from huggingface_hub import scan_cache_dir

    hub = checked_hub_path(benchmark_cache_root)
    if not hub.exists():
        return {"deleted_revisions": 0, "freed_bytes": 0}
    info = scan_cache_dir(cache_dir=hub)
    match = [repo for repo in info.repos if repo.repo_type == "model" and repo.repo_id == model_id]
    revisions = [revision.commit_hash for repo in match for revision in repo.revisions]
    if not revisions:
        return {"deleted_revisions": 0, "freed_bytes": 0}
    strategy = info.delete_revisions(*revisions)
    freed = strategy.expected_freed_size
    strategy.execute()
    return {"deleted_revisions": len(revisions), "freed_bytes": freed}
