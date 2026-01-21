import os
from datetime import datetime

from src.diagram import (
    build_dependency_edges,
    mermaid_from_edges,
    build_ts_dependency_edges,
    mermaid_from_ts_edges,
    is_ts_repo
)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def repo_name_from_path(repo_root: str) -> str:
    return os.path.basename(os.path.abspath(repo_root))


def write_file(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def generate_files_overview(tree: dict) -> str:
    # Simple markdown rendering of the tree dict
    def render(node, indent=0):
        lines = []
        for k, v in node.items():
            if isinstance(v, dict):
                lines.append("  " * indent + f"- **{k}/**")
                lines.extend(render(v, indent + 1))
            else:
                lines.append("  " * indent + f"- {k}")
        return lines

    return "# Files Overview\n\n" + "\n".join(render(tree)) + "\n"


def is_nextjs_app_router(repo_root: str) -> bool:
    """Check if repo is a Next.js App Router project."""
    if not repo_root:
        return False
    layout_path = os.path.join(repo_root, "app", "layout.tsx")
    return os.path.isfile(layout_path)


def generate_onboarding_md(
    repo_name: str,
    repo_root: str = None,
    run_commands: list = None,
    routes_md: str = None
) -> str:
    """Generate onboarding markdown. Next.js-aware if App Router detected."""

    if repo_root and is_nextjs_app_router(repo_root):
        return _generate_nextjs_onboarding(repo_name, repo_root, run_commands, routes_md)

    return _generate_generic_onboarding(repo_name, repo_root, run_commands)


def _generate_nextjs_onboarding(
    repo_name: str,
    repo_root: str,
    run_commands: list = None,
    routes_md: str = None
) -> str:
    """Generate Next.js App Router specific onboarding guide."""

    run_cmds = run_commands or ["npm install", "npm run dev"]
    run_cmds_md = "\n".join([f"{i+1}. `{cmd}`" for i, cmd in enumerate(run_cmds)])

    routes_section = ""
    if routes_md:
        routes_section = f"""
## Routes & Components Overview

{routes_md}
"""

    return f"""# Onboarding Guide: {repo_name}

Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}

This is a **Next.js App Router** project.

## Quick Start

{run_cmds_md}
{len(run_cmds) + 1}. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Structure

### Core Files

- **`app/layout.tsx`** - Root layout component. Wraps all pages, defines global UI shell (nav, footer), providers, and metadata. Changes here affect the entire app.

- **`app/page.tsx`** - Home page component. This renders at the `/` route. Each folder inside `app/` with a `page.tsx` becomes a route.

### Key Directories

- **`app/components/`** - Reusable React components shared across pages
- **`lib/`** - Utility functions, API clients, helpers, and shared logic
- **`app/`** - All routes and pages (folder-based routing)

## Files to Read First

1. `app/layout.tsx` - Understand the app shell and providers
2. `app/page.tsx` - See the home page implementation
3. `package.json` - Check dependencies and available scripts
4. `lib/` folder - Review shared utilities and API logic
5. `app/components/` - Browse reusable UI components

## Common Dev Tasks

| Task | Command |
|------|---------|
| Install dependencies | `npm install` |
| Start dev server | `npm run dev` |
| Build for production | `npm run build` |
| Run production build | `npm start` |
| Run linter | `npm run lint` |

## How Routing Works

Next.js App Router uses **file-based routing**:
- `app/page.tsx` → `/`
- `app/about/page.tsx` → `/about`
- `app/blog/[slug]/page.tsx` → `/blog/:slug` (dynamic route)
{routes_section}
## Next Steps

1. Run the dev server and explore the app in browser
2. Trace the data flow from a page to its components
3. Check `lib/` for API integrations or data fetching
4. Review any middleware or API routes in `app/api/`
"""


def _detect_project_type(repo_root: str) -> str:
    """Detect if project is Python, Node.js, or unknown."""
    if not repo_root:
        return "unknown"

    has_package_json = os.path.isfile(os.path.join(repo_root, "package.json"))
    has_requirements = os.path.isfile(os.path.join(repo_root, "requirements.txt"))
    has_pyproject = os.path.isfile(os.path.join(repo_root, "pyproject.toml"))
    has_setup_py = os.path.isfile(os.path.join(repo_root, "setup.py"))

    if has_requirements or has_pyproject or has_setup_py:
        return "python"
    if has_package_json:
        return "node"
    return "unknown"


def _generate_generic_onboarding(repo_name: str, repo_root: str = None, run_commands: list = None) -> str:
    """Generate generic onboarding guide, adapting to Python or Node.js."""

    project_type = _detect_project_type(repo_root)

    if project_type == "python":
        run_cmds = run_commands or []
        run_cmds_section = "\n".join([f"4. `{cmd}`" for cmd in run_cmds]) if run_cmds else "4. Run the project (check README / entry points)"

        return f"""# Onboarding Guide: {repo_name}

Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Quick Start

1. Create and activate a Python virtual environment
```bash
python -m venv venv
# Windows
venv\\Scripts\\activate
# macOS/Linux
source venv/bin/activate
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Run the project
{run_cmds_section}

## What this repo likely contains
- Core logic in `src/` or main package folder
- Configuration via `.env`, `config.*`, or YAML/JSON
- Tests in `tests/` (if present)

## Suggested first steps for a new developer
1. Read `README.md`
2. Identify the entry point (main script / app server)
3. Run tests (if available)
4. Trace one key workflow end-to-end
"""

    elif project_type == "node":
        run_cmds = run_commands or []
        run_cmds_md = "\n".join([f"- `{cmd}`" for cmd in run_cmds]) if run_cmds else "- Check `package.json` scripts"

        return f"""# Onboarding Guide: {repo_name}

Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Quick Start

1. Install dependencies
```bash
npm install
```

2. Run the project
{run_cmds_md}

## What this repo likely contains
- Source code in `src/` or root
- Configuration via `.env`, `config.*`, or JSON files
- Tests in `__tests__/` or `test/` (if present)

## Suggested first steps for a new developer
1. Read `README.md`
2. Check `package.json` for available scripts
3. Run tests (if available): `npm test`
4. Trace one key workflow end-to-end
"""

    else:
        return f"""# Onboarding Guide: {repo_name}

Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Quick Start
1. Check for dependency files (requirements.txt, package.json, etc.)
2. Install dependencies
3. Run the project (check README / entry points)

## What this repo likely contains
- Core logic in `src/` or main folder
- Configuration via `.env`, `config.*`, or YAML/JSON
- Tests in `tests/` or `test/` (if present)

## Suggested first steps for a new developer
1. Read `README.md`
2. Identify the entry point
3. Run tests (if available)
4. Trace one key workflow end-to-end
"""


# =============================================================================
# ML Notebook Mode
# =============================================================================

def _find_notebooks_in_tree(tree: dict, prefix: str = "") -> list:
    """Recursively find all .ipynb files in tree."""
    notebooks = []
    for k, v in tree.items():
        path = f"{prefix}/{k}" if prefix else k
        if isinstance(v, dict):
            notebooks.extend(_find_notebooks_in_tree(v, path))
        elif k.endswith(".ipynb"):
            notebooks.append(path)
    return notebooks


def _has_folder_in_tree(tree: dict, folder_names: list) -> bool:
    """Check if any of the folder names exist at root level of tree."""
    for name in folder_names:
        if name in tree and isinstance(tree[name], dict):
            return True
    return False


def is_notebook_ml_repo(repo_root: str, tree: dict) -> bool:
    """
    Detect if repo is an ML/notebook-based project.
    Returns True if:
    - Any .ipynb file exists in the tree, OR
    - Folders like notebooks/, nbs/, or experiments/ exist
    - Has requirements.txt with ML-related dependencies (bonus check)
    """
    if not tree:
        return False

    # Check for notebook folders
    notebook_folders = ["notebooks", "nbs", "notebook", "experiments", "jupyter"]
    if _has_folder_in_tree(tree, notebook_folders):
        return True

    # Check for any .ipynb files
    notebooks = _find_notebooks_in_tree(tree)
    if len(notebooks) > 0:
        return True

    # Check requirements.txt for ML libraries as additional signal
    if repo_root:
        req_path = os.path.join(repo_root, "requirements.txt")
        if os.path.isfile(req_path):
            try:
                with open(req_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                    ml_indicators = ["torch", "tensorflow", "keras", "scikit-learn", "sklearn", "pandas", "numpy", "jupyter", "notebook"]
                    ml_count = sum(1 for lib in ml_indicators if lib in content)
                    # If 3+ ML libraries found, likely an ML repo even without notebooks
                    if ml_count >= 3:
                        return True
            except Exception:
                pass

    return False


def generate_ml_pipeline_md(repo_name: str, tree: dict) -> str:
    """Generate ML pipeline documentation."""
    notebooks = _find_notebooks_in_tree(tree)
    notebooks_list = "\n".join([f"- `{nb}`" for nb in notebooks]) if notebooks else "- (no notebooks found)"

    return f"""# ML Pipeline: {repo_name}

Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}

This repository contains **Jupyter notebooks** for machine learning experiments.

## Notebooks in this Repository

{notebooks_list}

## Environment Setup

### Step 1: Create Virtual Environment
```bash
python -m venv venv
# Windows
venv\\Scripts\\activate
# macOS/Linux
source venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Launch Jupyter
```bash
# Option A: Jupyter Notebook
jupyter notebook

# Option B: JupyterLab (recommended)
jupyter lab
```

## Typical ML Pipeline Stages

| Stage | Description | Look For |
|-------|-------------|----------|
| **Data Loading** | Import and initial exploration | `pd.read_csv()`, `load_dataset()` |
| **Preprocessing** | Cleaning, feature engineering | `fit_transform()`, `fillna()`, `encode` |
| **Model Training** | Algorithm selection, fitting | `.fit()`, `train_test_split()` |
| **Evaluation** | Metrics, validation | `accuracy_score()`, `confusion_matrix()` |
| **Inference** | Predictions on new data | `.predict()`, `model.save()` |

## Key Files to Check

1. `requirements.txt` - Python dependencies
2. `README.md` - Project overview and instructions
3. `data/` folder - Dataset files (if present)
4. `models/` folder - Saved model artifacts (if present)
5. `src/` or `lib/` - Reusable Python modules

## Common Dependencies

Most ML notebooks use:
- **pandas** / **numpy** - Data manipulation
- **scikit-learn** - Classical ML algorithms
- **matplotlib** / **seaborn** - Visualization
- **torch** / **tensorflow** - Deep learning (if applicable)
"""


def generate_experiments_md(repo_name: str, tree: dict) -> str:
    """Generate experiments documentation."""
    notebooks = _find_notebooks_in_tree(tree)

    notebook_details = []
    for i, nb in enumerate(notebooks, 1):
        name = nb.split("/")[-1].replace(".ipynb", "")
        notebook_details.append(f"""### {i}. `{nb}`
- **Purpose**: (Review notebook for details)
- **Key outputs**: (Check cell outputs)
- **Status**: To be documented
""")

    notebooks_section = "\n".join(notebook_details) if notebook_details else "No notebooks found."

    return f"""# Experiments Log: {repo_name}

Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Overview

This document tracks experiments and notebooks in the repository.

## Notebooks

{notebooks_section}

## Experiment Tracking Checklist

For each experiment, document:

- [ ] **Objective**: What question are you answering?
- [ ] **Dataset**: Which data split/version?
- [ ] **Model/Method**: Algorithm and hyperparameters
- [ ] **Metrics**: Evaluation criteria
- [ ] **Results**: Key findings
- [ ] **Next Steps**: Follow-up experiments

## Reproducing Experiments

1. Clone the repository
2. Set up environment (see ML_PIPELINE.md)
3. Run notebooks in order (if sequential dependencies)
4. Compare outputs with documented results

## Notes

- Document any random seeds used for reproducibility
- Track data versions if datasets change over time
- Save model checkpoints for important experiments
"""


def generate_results_summary_md(repo_name: str, tree: dict) -> str:
    """Generate results summary documentation."""
    notebooks = _find_notebooks_in_tree(tree)
    notebooks_list = "\n".join([f"| `{nb}` | - | - | - |" for nb in notebooks]) if notebooks else "| (none) | - | - | - |"

    return f"""# Results Summary: {repo_name}

Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Model Performance Overview

| Notebook | Model | Primary Metric | Score |
|----------|-------|----------------|-------|
{notebooks_list}

> **Note**: Fill in results after running experiments.

## Data Summary

| Aspect | Details |
|--------|---------|
| **Dataset** | (Describe dataset source) |
| **Size** | (Number of samples) |
| **Features** | (Number and types) |
| **Target** | (Classification/Regression target) |
| **Train/Val/Test Split** | (e.g., 70/15/15) |

## Best Model Configuration

```
Model: (e.g., RandomForest, XGBoost, Neural Network)
Hyperparameters:
  - param1: value
  - param2: value
Performance:
  - Metric1: score
  - Metric2: score
```

## Key Findings

1. (Finding 1)
2. (Finding 2)
3. (Finding 3)

## Limitations

- (Limitation 1: e.g., dataset size, class imbalance)
- (Limitation 2: e.g., missing feature types)
- (Limitation 3: e.g., compute constraints)

## Future Work

- [ ] Try additional models
- [ ] Feature engineering improvements
- [ ] Hyperparameter tuning
- [ ] Cross-validation analysis
- [ ] Deploy best model

## How to Update This Document

After running experiments:
1. Fill in the performance table with actual metrics
2. Document the best model configuration
3. Add key findings and insights
4. Note any limitations discovered
"""


def generate_architecture_md(repo_name: str, repo_root: str) -> str:
    if is_ts_repo(repo_root):
        nodes, edges = build_ts_dependency_edges(repo_root)
        mermaid = mermaid_from_ts_edges(nodes, edges)
        lang_note = "TypeScript/TSX"
        extra_note = "Prioritizes files in `app/`, `lib/`, `src/`, and `components/` folders."
    else:
        nodes, edges = build_dependency_edges(repo_root)
        mermaid = mermaid_from_edges(nodes, edges)
        lang_note = "Python"
        extra_note = "Entry point detection + API route tracing available for FastAPI/Flask."

    return f"""# Architecture: {repo_name}

## Auto-generated dependency diagram ({lang_note})
{mermaid}

## Notes
- Diagram is derived from `import` statement parsing.
- {extra_note}
"""
def generate_repo_explainer_prompt(repo_name: str, run_cmds: list, routes_md: str, files_md: str, top_code_snippets: str) -> str:
    cmds = "\n".join([f"- {c}" for c in run_cmds]) if run_cmds else "- (not found)"
    return f"""
You are a senior engineer writing a clear repo explainer for onboarding.

Write a markdown document named REPO_EXPLAINER.md.

Rules:
- Use ONLY the information provided below.
- If something is missing, say "Not found in repo context".
- Keep it concise but actually useful.

Must include sections:
1) What this project is
2) Tech stack (infer only from package.json scripts/deps if present in context)
3) How to run locally (use run commands below)
4) Main entry points and flow
5) Routes and key UI components
6) Key logic modules (lib/)
7) Suggested improvements (5 bullet points)

Repo Name:
{repo_name}

Run Commands:
{cmds}

Routes + Components Map:
{routes_md}

Files Overview:
{files_md}

Relevant Code Snippets (grounding):
{top_code_snippets}
"""

