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

def scan_for_framework_imports(repo_root: str) -> str:
    """Scan Python files for framework imports to detect FastAPI, Flask, Django."""
    framework_patterns = {
        "FastAPI": ["from fastapi import", "import fastapi"],
        "Flask": ["from flask import", "import flask"],
        "Django": ["from django", "import django"],
    }

    # Check common entry files first
    check_files = ["main.py", "app.py", "server.py", "run.py", "wsgi.py", "asgi.py"]

    for filename in check_files:
        filepath = os.path.join(repo_root, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                    for framework, patterns in framework_patterns.items():
                        for pattern in patterns:
                            if pattern in content:
                                return framework
            except Exception:
                continue

    return None


def find_entry_files_recursive(repo_root: str, search_dirs: list, filenames: list) -> list:
    """Search for specific filenames recursively under given directories."""
    found = []
    for search_dir in search_dirs:
        dir_path = os.path.join(repo_root, search_dir)
        if not os.path.isdir(dir_path):
            continue
        for root, dirs, files in os.walk(dir_path):
            # Skip hidden directories and common non-source dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'node_modules', '.git')]
            for filename in filenames:
                if filename in files:
                    rel_path = os.path.relpath(os.path.join(root, filename), repo_root)
                    found.append(rel_path.replace("\\", "/"))
    return found


def detect_python_entrypoints(repo_root: str):
    candidates = []

    # Check root-level entry files
    for name in ["main.py", "app.py", "server.py", "run.py", "wsgi.py", "asgi.py"]:
        path = os.path.join(repo_root, name)
        if os.path.exists(path):
            candidates.append(name)

    # Search for __main__.py, wsgi.py, asgi.py under src/** and tests/**
    deep_entry_files = ["__main__.py", "wsgi.py", "asgi.py"]
    search_dirs = ["src", "tests"]
    deep_found = find_entry_files_recursive(repo_root, search_dirs, deep_entry_files)
    candidates.extend(deep_found)

    # Detect specific framework
    detected_framework = scan_for_framework_imports(repo_root)

    # Check if this is a library/framework (pyproject.toml + src/<pkg>/__init__.py)
    is_library = False
    has_pyproject = exists(repo_root, "pyproject.toml")
    if has_pyproject and os.path.isdir(os.path.join(repo_root, "src")):
        for item in os.listdir(os.path.join(repo_root, "src")):
            pkg_init = os.path.join(repo_root, "src", item, "__init__.py")
            if os.path.isfile(pkg_init):
                is_library = True
                break

    notes = []
    run_cmds = []

    if detected_framework == "FastAPI":
        framework = "FastAPI"
        notes.append("Detected FastAPI framework. Look for `FastAPI()` app instance and route decorators (`@app.get`, `@app.post`).")
        run_cmds.append("uvicorn main:app --reload  (or uvicorn app:app --reload)")
    elif detected_framework == "Flask":
        framework = "Flask"
        notes.append("Detected Flask framework. Look for `Flask(__name__)` app instance and route decorators (`@app.route`).")
        run_cmds.append("flask run  (or python app.py)")
    elif detected_framework == "Django":
        framework = "Django"
        notes.append("Detected Django framework. Look for `manage.py` and `settings.py`.")
        run_cmds.append("python manage.py runserver")
        if exists(repo_root, "manage.py"):
            candidates.append("manage.py")
    elif is_library:
        framework = "Python Library/Framework"
        notes.append("Detected Python library/framework structure (pyproject.toml + src/<package>/).")
        run_cmds.append("pip install -e .")
        run_cmds.append("python -m pytest")
        # Check for __main__.py to add run command
        for c in candidates:
            if "__main__.py" in c:
                pkg_name = c.split("/")[1] if "/" in c else None
                if pkg_name:
                    run_cmds.append(f"python -m {pkg_name}")
                break
    else:
        framework = "Python (generic)"
        if candidates:
            notes.append("Detected common Python entrypoint filenames.")
        else:
            notes.append("No common Python entrypoint filenames found. Entry may be inside a package or configured via pyproject/cli.")

    return {
        "framework": framework,
        "entry_files": candidates,
        "run_commands": run_cmds,
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
