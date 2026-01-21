import os
import json

def exists(repo_root: str, rel_path: str) -> bool:
    return os.path.exists(os.path.join(repo_root, rel_path))

def read_json(repo_root: str, rel_path: str):
    path = os.path.join(repo_root, rel_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def detect_nextjs_entrypoints(repo_root: str):
    # Next.js App Router
    app_router = exists(repo_root, "app/layout.tsx") or exists(repo_root, "app/layout.jsx")
    pages_router = exists(repo_root, "pages/index.tsx") or exists(repo_root, "pages/index.jsx") or exists(repo_root, "pages/_app.tsx")

    entry_files = []
    notes = []
    run_cmds = []

    pkg = read_json(repo_root, "package.json")
    if pkg and "scripts" in pkg:
        scripts = pkg["scripts"]
        # common run commands
        if "dev" in scripts:
            run_cmds.append(f"npm run dev  (runs: {scripts['dev']})")
        if "build" in scripts:
            run_cmds.append(f"npm run build (runs: {scripts['build']})")
        if "start" in scripts:
            run_cmds.append(f"npm run start (runs: {scripts['start']})")

    if app_router:
        notes.append("Detected Next.js App Router (`app/` directory). Root route is `app/page.*` and root layout is `app/layout.*`.")
        for p in ["app/layout.tsx", "app/layout.jsx", "app/page.tsx", "app/page.jsx"]:
            if exists(repo_root, p):
                entry_files.append(p)

    if pages_router:
        notes.append("Detected Next.js Pages Router (`pages/` directory). Root route is `pages/index.*` and app wrapper is `pages/_app.*`.")
        for p in ["pages/_app.tsx", "pages/_app.jsx", "pages/index.tsx", "pages/index.jsx"]:
            if exists(repo_root, p):
                entry_files.append(p)

    if not entry_files and exists(repo_root, "next.config.ts"):
        notes.append("Found `next.config.*` but no clear `app/` or `pages/` router entry files were detected.")

    return {
        "framework": "Next.js",
        "entry_files": entry_files,
        "run_commands": run_cmds,
        "notes": notes
    }

def detect_python_entrypoints(repo_root: str):
    candidates = []
    for name in ["main.py", "app.py", "server.py", "run.py", "wsgi.py", "asgi.py"]:
        path = os.path.join(repo_root, name)
        if os.path.exists(path):
            candidates.append(name)

    notes = []
    if candidates:
        notes.append("Detected common Python entrypoint filenames.")
    else:
        notes.append("No common Python entrypoint filenames found. Entry may be inside a package or configured via pyproject/cli.")

    return {
        "framework": "Python (generic)",
        "entry_files": candidates,
        "run_commands": [],
        "notes": notes
    }

def detect_entrypoints(repo_root: str):
    if exists(repo_root, "package.json") and (exists(repo_root, "next.config.js") or exists(repo_root, "next.config.ts")):
        return detect_nextjs_entrypoints(repo_root)

    if exists(repo_root, "package.json") and exists(repo_root, "app"):
        # still likely Next.js, even without next.config in some cases
        return detect_nextjs_entrypoints(repo_root)

    if exists(repo_root, "requirements.txt") or exists(repo_root, "pyproject.toml") or exists(repo_root, "setup.py"):
        return detect_python_entrypoints(repo_root)

    return {
        "framework": "Unknown",
        "entry_files": [],
        "run_commands": [],
        "notes": ["Could not detect framework reliably. Next upgrade: add more detectors (React/Vite, Spring, Django, etc.)."]
    }
