import os
import re
from typing import Dict, List, Set, Tuple

from src.file_filter import should_ignore

IMPORT_RE = re.compile(r'^\s*import\s+.*?\s+from\s+["\'](.+?)["\']\s*;?\s*$', re.MULTILINE)

def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""

def collect_ts_files(repo_root: str) -> List[str]:
    out = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if not should_ignore(d)]
        for f in files:
            if should_ignore(f):
                continue
            if f.endswith((".ts", ".tsx")):
                out.append(os.path.join(root, f))
    return out

def is_app_route_file(rel_path: str) -> bool:
    # Next.js App Router: routes live under app/.../page.tsx
    rel = rel_path.replace("\\", "/")
    return rel.startswith("app/") and rel.endswith(("/page.tsx", "/page.jsx", "/page.ts", "/page.js")) or rel == "app/page.tsx"

def route_from_app_page(rel_path: str) -> str:
    # app/page.tsx -> /
    # app/foo/page.tsx -> /foo
    # app/foo/bar/page.tsx -> /foo/bar
    rel = rel_path.replace("\\", "/")
    rel = rel[len("app/"):]  # strip app/
    rel = rel.replace("/page.tsx", "").replace("/page.ts", "").replace("/page.jsx", "").replace("/page.js", "")
    if rel == "page.tsx" or rel == "page.ts" or rel == "page.jsx" or rel == "page.js" or rel == "":
        return "/"
    return "/" + rel

def resolve_relative_import(from_file_rel: str, import_path: str) -> str:
    # Only resolve local relative imports like ./x or ../lib/y
    if not import_path.startswith("."):
        return ""
    base_dir = os.path.dirname(from_file_rel).replace("\\", "/")
    joined = os.path.normpath(os.path.join(base_dir, import_path)).replace("\\", "/")
    return joined

def guess_ts_file(repo_root: str, rel_no_ext: str) -> str:
    # try common extensions
    for ext in [".ts", ".tsx", ".js", ".jsx"]:
        candidate = os.path.join(repo_root, rel_no_ext + ext)
        if os.path.exists(candidate):
            return rel_no_ext + ext
    # also allow index files
    for ext in [".ts", ".tsx", ".js", ".jsx"]:
        candidate = os.path.join(repo_root, rel_no_ext, "index" + ext)
        if os.path.exists(candidate):
            return rel_no_ext + "/index" + ext
    return ""

def parse_imports(text: str) -> List[str]:
    return IMPORT_RE.findall(text)

def build_route_component_map(repo_root: str) -> Dict[str, Dict[str, List[str]]]:
    """
    Returns:
    {
      "/": { "route_file": "app/page.tsx", "imports": [...resolved local files...] },
      "/foo": { ... }
    }
    """
    routes: Dict[str, Dict[str, List[str]]] = {}
    ts_files = collect_ts_files(repo_root)

    # Build quick set for existence checks
    existing_rel = set([os.path.relpath(p, repo_root).replace("\\", "/") for p in ts_files])

    for abs_path in ts_files:
        rel_path = os.path.relpath(abs_path, repo_root).replace("\\", "/")
        if not is_app_route_file(rel_path):
            continue

        route = route_from_app_page(rel_path)
        text = read_text(abs_path)
        imports = parse_imports(text)

        resolved_local: List[str] = []
        for imp in imports:
            rel_no_ext = resolve_relative_import(rel_path, imp)
            if not rel_no_ext:
                continue
            guess = guess_ts_file(repo_root, rel_no_ext)
            if guess and guess in existing_rel:
                resolved_local.append(guess)

        # de-dupe preserve order
        seen = set()
        uniq = []
        for x in resolved_local:
            if x not in seen:
                uniq.append(x)
                seen.add(x)

        routes[route] = {"route_file": rel_path, "imports": uniq}

    return routes

def render_routes_md(routes: Dict[str, Dict[str, List[str]]]) -> str:
    lines = ["# Routes + Component Map (Next.js App Router)\n"]
    if not routes:
        lines.append("No App Router `app/**/page.*` routes detected.\n")
        return "\n".join(lines)

    for route in sorted(routes.keys()):
        info = routes[route]
        lines.append(f"## Route: `{route}`")
        lines.append(f"- Route file: `{info['route_file']}`")
        if info["imports"]:
            lines.append("- Local imports used by this route:")
            for imp in info["imports"]:
                lines.append(f"  - `{imp}`")
        else:
            lines.append("- Local imports used by this route: (none detected)")
        lines.append("")

    return "\n".join(lines)