import os
from src.file_filter import should_ignore

def build_file_tree(base_path: str):
    tree = {}

    for root, dirs, files in os.walk(base_path):
        # filter ignored dirs
        dirs[:] = [d for d in dirs if not should_ignore(d)]

        rel_root = os.path.relpath(root, base_path)

        # walk to the correct subtree
        subtree = tree
        if rel_root != ".":
            for part in rel_root.split(os.sep):
                subtree = subtree.setdefault(part, {})

        # add files
        for f in files:
            if should_ignore(f):
                continue
            subtree[f] = "file"

    return tree
