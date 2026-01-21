import os
import re
from typing import Set, Tuple, List

from src.file_filter import should_ignore

PY_IMPORT_RE = re.compile(r"^\s*(import\s+([\w\.]+)|from\s+([\w\.]+)\s+import\s+)", re.MULTILINE)

# TS/TSX import patterns for relative imports
# Matches: import X from "./x" or import { A } from "../lib/foo"
TS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[\w{},\s*]+\s+from\s+)?['"](\.[^'"]+)['"]|import\s*\(['"](\.[^'"]+)['"]\))""",
    re.MULTILINE
)

# Folders to ignore for TS diagrams
TS_IGNORE_FOLDERS = {"node_modules", ".next", "out", "public", "dist", "build", ".git"}

def rel_module_from_path(file_path: str, repo_root: str) -> str:
    rel = os.path.relpath(file_path, repo_root).replace("\\", "/")
    if rel.endswith(".py"):
        rel = rel[:-3]
    return rel.replace("/", ".")

def parse_python_imports(text: str) -> Set[str]:
    imports = set()
    for m in PY_IMPORT_RE.finditer(text):
        mod = m.group(2) or m.group(3)
        if mod:
            imports.add(mod.split(".")[0])  # keep top-level for readability
    return imports

def collect_python_files(repo_root: str) -> List[str]:
    out = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if not should_ignore(d)]
        for f in files:
            if should_ignore(f):
                continue
            if f.endswith(".py"):
                out.append(os.path.join(root, f))
    return out

def build_dependency_edges(repo_root: str) -> Tuple[Set[str], Set[Tuple[str, str]]]:
    py_files = collect_python_files(repo_root)

    nodes: Set[str] = set()
    edges: Set[Tuple[str, str]] = set()

    for fp in py_files:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            continue

        src_mod = rel_module_from_path(fp, repo_root)
        nodes.add(src_mod)

        imported = parse_python_imports(text)
        for imp in imported:
            edges.add((src_mod, imp))

    return nodes, edges

def collect_ts_files(repo_root: str) -> List[str]:
    """Collect all .ts and .tsx files, prioritizing app/ and lib/ folders."""
    out = []
    for root, dirs, files in os.walk(repo_root):
        # Filter out ignored folders
        dirs[:] = [d for d in dirs if d not in TS_IGNORE_FOLDERS and not should_ignore(d)]

        for f in files:
            if should_ignore(f):
                continue
            if f.endswith(".ts") or f.endswith(".tsx"):
                out.append(os.path.join(root, f))
    return out


def parse_ts_imports(text: str) -> Set[str]:
    """Parse relative imports from TS/TSX file content."""
    imports = set()
    for m in TS_IMPORT_RE.finditer(text):
        path = m.group(1) or m.group(2)
        if path and (path.startswith("./") or path.startswith("../")):
            imports.add(path)
    return imports


def resolve_ts_import(import_path: str, source_file: str, repo_root: str) -> str:
    """Resolve a relative import path to an actual file path."""
    source_dir = os.path.dirname(source_file)

    # Normalize the import path
    resolved = os.path.normpath(os.path.join(source_dir, import_path))

    # Try different extensions and index files
    candidates = [
        resolved + ".ts",
        resolved + ".tsx",
        resolved + ".js",
        resolved + ".jsx",
        os.path.join(resolved, "index.ts"),
        os.path.join(resolved, "index.tsx"),
        os.path.join(resolved, "index.js"),
        os.path.join(resolved, "index.jsx"),
    ]

    for candidate in candidates:
        if os.path.isfile(candidate):
            return os.path.relpath(candidate, repo_root).replace("\\", "/")

    # Return the import path as-is if not resolved
    return os.path.relpath(resolved, repo_root).replace("\\", "/")


def rel_ts_path(file_path: str, repo_root: str) -> str:
    """Convert file path to relative path for display."""
    rel = os.path.relpath(file_path, repo_root).replace("\\", "/")
    return rel


def build_ts_dependency_edges(repo_root: str) -> Tuple[Set[str], Set[Tuple[str, str]]]:
    """Build dependency graph for TypeScript/TSX files."""
    ts_files = collect_ts_files(repo_root)

    nodes: Set[str] = set()
    edges: Set[Tuple[str, str]] = set()

    for fp in ts_files:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            continue

        src_rel = rel_ts_path(fp, repo_root)
        nodes.add(src_rel)

        imported = parse_ts_imports(text)
        for imp in imported:
            resolved = resolve_ts_import(imp, fp, repo_root)
            if resolved and not resolved.startswith(".."):  # Keep only internal imports
                edges.add((src_rel, resolved))
                nodes.add(resolved)

    return nodes, edges


def is_ts_repo(repo_root: str) -> bool:
    """Check if repo is TypeScript/Next.js based."""
    indicators = [
        "tsconfig.json",
        "next.config.ts",
        "next.config.js",
        "next.config.mjs",
    ]
    for indicator in indicators:
        if os.path.exists(os.path.join(repo_root, indicator)):
            return True
    return False


def mermaid_from_ts_edges(nodes: Set[str], edges: Set[Tuple[str, str]], max_nodes: int = 40) -> str:
    """Generate Mermaid diagram from TS dependency edges, prioritizing app/ and lib/."""

    def node_id(name: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        return safe[:60]

    def priority_score(path: str) -> int:
        """Lower score = higher priority."""
        if path.startswith("app/"):
            return 0
        if path.startswith("lib/"):
            return 1
        if path.startswith("src/"):
            return 2
        if path.startswith("components/"):
            return 3
        return 10

    # Filter and prioritize nodes
    sorted_nodes = sorted(nodes, key=lambda n: (priority_score(n), n))
    priority_nodes = set(sorted_nodes[:max_nodes])

    # Filter edges to only include priority nodes
    filtered_edges = {(a, b) for a, b in edges if a in priority_nodes and b in priority_nodes}

    node_map = {n: node_id(n) for n in priority_nodes}

    lines = ["```mermaid", "graph TD"]

    for n in sorted(priority_nodes):
        # Shorten display name for readability
        display = n
        if len(display) > 40:
            display = "..." + display[-37:]
        lines.append(f'  {node_map[n]}["{display}"]')

    for a, b in sorted(filtered_edges):
        if a in node_map and b in node_map:
            lines.append(f"  {node_map[a]} --> {node_map[b]}")

    lines.append("```")
    return "\n".join(lines)


def mermaid_from_edges(nodes: Set[str], edges: Set[Tuple[str, str]]) -> str:
    def node_id(name: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        return safe[:60]

    node_map = {n: node_id(n) for n in nodes}

    lines = ["```mermaid", "graph TD"]

    for n in sorted(nodes):
        lines.append(f'  {node_map[n]}["{n}"]')

    for a, b in sorted(edges):
        target = None
        for n in nodes:
            if n.startswith(b + ".") or n == b:
                target = n
                break
        if target and a in node_map and target in node_map:
            lines.append(f"  {node_map[a]} --> {node_map[target]}")

    lines.append("```")
    return "\n".join(lines)
