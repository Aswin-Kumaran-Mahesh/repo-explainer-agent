import os
import streamlit as st
from src.ts_map import build_route_component_map, render_routes_md
from src.entry_points import detect_entrypoints
from src.docs import generate_repo_explainer_prompt
from src.llm_providers import generate_markdown, API_ERROR_PREFIX, OLLAMA_ERROR_PREFIX

from src.docs import (
    ensure_dir,
    repo_name_from_path,
    write_file,
    generate_files_overview,
    generate_onboarding_md,
    generate_architecture_md,
    is_notebook_ml_repo,
    generate_ml_pipeline_md,
    generate_experiments_md,
    generate_results_summary_md
)
from src.entry_points import detect_entrypoints
from src.ingest import clone_repo
from src.tree_view import build_file_tree
from src.indexer import build_faiss_index
from src.rag import retrieve, format_citations, basic_answer, llm_answer

st.title("GitHub Repo Explainer Agent")

provider = st.selectbox("LLM Provider", ["Local (Ollama)", "Claude (Anthropic)"])
api_key = st.text_input("Claude API Key (required only for Claude)", type="password")
repo_url = st.text_input("Enter GitHub Repo URL")

if "repo_root" not in st.session_state:
    st.session_state.repo_root = None
if "index" not in st.session_state:
    st.session_state.index = None
if "metas" not in st.session_state:
    st.session_state.metas = None
if "model" not in st.session_state:
    st.session_state.model = None
if "tree" not in st.session_state:
    st.session_state.tree = None

if st.button("Analyze Repo"):
    if repo_url:
        with st.spinner("Cloning repo..."):
            repo_root = clone_repo(repo_url)
            st.session_state.repo_root = repo_root

        with st.spinner("Building file tree..."):
            st.session_state.tree = build_file_tree(repo_root)

        with st.spinner("Indexing code for search (RAG)..."):
            index, metas, model = build_faiss_index(repo_root)
            st.session_state.index = index
            st.session_state.metas = metas
            st.session_state.model = model

        st.success("Repo analyzed + indexed!")
    else:
        st.warning("Please enter a valid GitHub URL")

if st.session_state.tree:
    st.subheader("Repository Structure")
    st.json(st.session_state.tree)
    if st.button("Find Entry Points"):
        info = detect_entrypoints(st.session_state.repo_root)
        st.subheader("Entry Point Detection")
        st.write("**Framework:**", info["framework"])

        st.write("**Entry files:**")
        if info["entry_files"]:
            for f in info["entry_files"]:
                st.write("- " + f)
        else:
            st.write("- (none detected)")

        st.write("**Run commands:**")
        if info["run_commands"]:
            for cmd in info["run_commands"]:
                st.write("- " + cmd)
        else:
            st.write("- (none detected)")

        st.write("**Notes:**")
        for n in info["notes"]:
            st.write("- " + n)
    
    # Docs button

    if st.session_state.repo_root:
        if st.button("Generate Onboarding Docs + Diagram"):
            repo_root = st.session_state.repo_root
            repo_name = repo_name_from_path(repo_root)
            tree = st.session_state.tree

            out_dir = os.path.join("outputs", repo_name)
            ensure_dir(out_dir)

            # Check if this is an ML notebook repo
            if is_notebook_ml_repo(repo_root, tree):
                # Generate ML-specific docs
                ml_pipeline = generate_ml_pipeline_md(repo_name, tree)
                experiments = generate_experiments_md(repo_name, tree)
                results = generate_results_summary_md(repo_name, tree)
                files = generate_files_overview(tree)

                write_file(os.path.join(out_dir, "ML_PIPELINE.md"), ml_pipeline)
                write_file(os.path.join(out_dir, "EXPERIMENTS.md"), experiments)
                write_file(os.path.join(out_dir, "RESULTS_SUMMARY.md"), results)
                write_file(os.path.join(out_dir, "FILES_OVERVIEW.md"), files)

                st.success(f"ML Notebook docs generated in: {out_dir}")
                st.write("Generated files:")
                st.write("- ML_PIPELINE.md")
                st.write("- EXPERIMENTS.md")
                st.write("- RESULTS_SUMMARY.md")
                st.write("- FILES_OVERVIEW.md")
            else:
                # Standard onboarding docs
                entry_info = detect_entrypoints(repo_root)
                run_commands = entry_info.get("run_commands", [])
                routes = build_route_component_map(repo_root)
                routes_md = render_routes_md(routes)

                onboarding = generate_onboarding_md(
                    repo_name,
                    repo_root=repo_root,
                    run_commands=run_commands,
                    routes_md=routes_md
                )
                arch = generate_architecture_md(repo_name, repo_root)
                files = generate_files_overview(tree)

                write_file(os.path.join(out_dir, "ONBOARDING.md"), onboarding)
                write_file(os.path.join(out_dir, "ARCHITECTURE.md"), arch)
                write_file(os.path.join(out_dir, "FILES_OVERVIEW.md"), files)

                st.success(f"Docs generated in: {out_dir}")
                st.write("Generated files:")
                st.write("- ONBOARDING.md")
                st.write("- ARCHITECTURE.md")
                st.write("- FILES_OVERVIEW.md")



        if st.button("Explain This Repo"):
            if provider == "Claude (Anthropic)" and not api_key.strip():
                st.warning("Paste your Claude API key to use Claude provider.")
            else:
                repo_root = st.session_state.repo_root
                repo_name = repo_name_from_path(repo_root)

                out_dir = os.path.join("outputs", repo_name)
                ensure_dir(out_dir)

                # Build context
                entry = detect_entrypoints(repo_root)
                routes = build_route_component_map(repo_root)
                routes_md = render_routes_md(routes)
                files_md = generate_files_overview(st.session_state.tree)

                # Grab top code chunks as grounding
                chunks = retrieve(
                    "Explain the main app flow and key logic modules",
                    st.session_state.index,
                    st.session_state.metas,
                    st.session_state.model,
                    top_k=6
                )
                top_code = "\n\n---\n\n".join(
                    [f"FILE: {c.file_path} (lines {c.start_line}-{c.end_line})\n{c.text[:1200]}" for c in chunks]
                )

                prompt = generate_repo_explainer_prompt(
                    repo_name=repo_name,
                    run_cmds=entry.get("run_commands", []),
                    routes_md=routes_md,
                    files_md=files_md,
                    top_code_snippets=top_code
                )

                spinner_msg = "Ollama is writing the explainer..." if provider == "Local (Ollama)" else "Claude is writing the explainer..."
                with st.spinner(spinner_msg):
                    md = generate_markdown(provider, prompt, api_key)

                if md.startswith(API_ERROR_PREFIX):
                    st.error(md.replace(API_ERROR_PREFIX, "").strip())
                elif md.startswith(OLLAMA_ERROR_PREFIX):
                    st.error(md.replace(OLLAMA_ERROR_PREFIX, "").strip())
                else:
                    write_file(os.path.join(out_dir, "REPO_EXPLAINER.md"), md)
                    st.success(f"Generated: {os.path.join(out_dir, 'REPO_EXPLAINER.md')}")
                    st.write(md)

    

        if st.button("Generate Route + Component Map"):
            repo_root = st.session_state.repo_root
            repo_name = repo_name_from_path(repo_root)

            out_dir = os.path.join("outputs", repo_name)
            ensure_dir(out_dir)

            routes = build_route_component_map(repo_root)
            md = render_routes_md(routes)

            write_file(os.path.join(out_dir, "ROUTES_COMPONENTS.md"), md)
            st.success(f"Route map generated in: {out_dir}")
            st.write("- ROUTES_COMPONENTS.md")







st.divider()
st.subheader("Ask questions about this repo")

q = st.text_input("Ask a question (e.g., 'Where is the main entry point?')")

if st.button("Ask"):
    if not st.session_state.index:
        st.warning("Analyze a repo first.")
    elif not q.strip():
        st.warning("Type a question.")
    else:
        chunks = retrieve(
            q,
            st.session_state.index,
            st.session_state.metas,
            st.session_state.model,
            top_k=6
        )
        cites = format_citations(chunks, st.session_state.repo_root)


        with st.spinner("Thinking..."):
            q_lower = q.lower()

            # Route "entry point" questions to deterministic detector
            if "entry point" in q_lower or "main file" in q_lower or "start" in q_lower:
                info = detect_entrypoints(st.session_state.repo_root)
                answer_lines = []
                answer_lines.append(f"Framework: {info['framework']}")
                answer_lines.append("Entry files:")
                if info["entry_files"]:
                    for f in info["entry_files"]:
                        answer_lines.append(f"- {f}")
                else:
                    answer_lines.append("- (none detected)")
                if info["run_commands"]:
                    answer_lines.append("Run commands:")
                    for cmd in info["run_commands"]:
                        answer_lines.append(f"- {cmd}")
                if info["notes"]:
                    answer_lines.append("Notes:")
                    for n in info["notes"]:
                        answer_lines.append(f"- {n}")

                answer = "\n".join(answer_lines)

                # Use detector output as citations (simple)
                cites = info["entry_files"] if info["entry_files"] else cites

            else:
                if api_key.strip():
                    answer = llm_answer(q, chunks, api_key)
                else:
                    answer = basic_answer(q, chunks)

        if answer.startswith(API_ERROR_PREFIX):
            st.error(answer.replace(API_ERROR_PREFIX, "").strip())
        else:
            st.write(answer)
            st.markdown("**Citations:**")
            for c in cites:
                st.write("- " + c)
