IGNORE_EXTENSIONS = [
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".exe", ".dll", ".so", ".bin",
    ".zip", ".tar", ".gz", ".7z",
    ".pdf", ".lock"
]
IGNORE_FOLDERS = [
    ".git", "node_modules", "dist", "build", ".venv", "__pycache__",
    ".idea", ".vscode", ".next", "out", "public"
]

def should_ignore(name: str) -> bool:
    # Folder exact match
    if name in IGNORE_FOLDERS:
        return True

    # Extension match
    lower = name.lower()
    for ext in IGNORE_EXTENSIONS:
        if lower.endswith(ext):
            return True

    return False
