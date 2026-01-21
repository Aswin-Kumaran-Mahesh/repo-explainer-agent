import os
from git import Repo
from src.file_filter import should_ignore

BASE_DIR = os.path.join("data", "repos")

def clone_repo(url: str) -> str:
    repo_name = url.strip().split("/")[-1].replace(".git", "")
    target_path = os.path.join(BASE_DIR, repo_name)

    os.makedirs(BASE_DIR, exist_ok=True)

    # If already cloned, reuse it
    if os.path.exists(target_path) and os.path.isdir(target_path):
        return target_path

    Repo.clone_from(url, target_path)
    return target_path


def get_all_files(repo_path: str):
    all_files = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not should_ignore(d)]
        for f in files:
            if should_ignore(f):
                continue
            all_files.append(os.path.join(root, f))
    return all_files
