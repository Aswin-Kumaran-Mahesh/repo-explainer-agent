from typing import List
import os
import numpy as np
import anthropic

from src.indexer import ChunkMeta


def retrieve(question: str, index, metas: List[ChunkMeta], model, top_k: int = 6):
    q_emb = model.encode([question], convert_to_numpy=True, normalize_embeddings=True)
    q_emb = q_emb.astype(np.float32)

    scores, ids = index.search(q_emb, top_k)

    results = []
    for idx in ids[0]:
        if idx == -1:
            continue
        results.append(metas[int(idx)])

    return results


def format_citations(chunks: List[ChunkMeta], repo_root: str):
    citations = []
    for c in chunks:
        rel = os.path.relpath(c.file_path, repo_root)
        citations.append(f"{rel} (lines {c.start_line}-{c.end_line})")

    # remove duplicates while preserving order
    seen = set()
    unique = []
    for c in citations:
        if c not in seen:
            unique.append(c)
            seen.add(c)

    return unique


def basic_answer(question: str, chunks: List[ChunkMeta]):
    context = "\n\n---\n\n".join([c.text[:1200] for c in chunks])

    return f"""
MVP LOCAL ANSWER (no external LLM):

Question: {question}

Relevant code snippets:

{context}
"""


API_ERROR_PREFIX = "[API_ERROR]"


def llm_answer(question: str, chunks: List[ChunkMeta], api_key: str):
    client = anthropic.Anthropic(api_key=api_key)

    context_blocks = []
    for c in chunks:
        context_blocks.append(
            f"FILE: {c.file_path} (lines {c.start_line}-{c.end_line})\n{c.text[:1500]}"
        )

    context = "\n\n---\n\n".join(context_blocks)

    prompt = f"""
You are a senior software engineer helping onboard a new developer.

Rules:
- Use ONLY the provided code context.
- If the answer is not clearly in the context, say you cannot confirm.
- Cite file paths and line ranges inline (example: src/main.py:10-42).

QUESTION:
{question}

CODE CONTEXT:
{context}

Provide a clear, structured explanation.
"""

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except anthropic.BadRequestError as e:
        if "credit balance is too low" in str(e):
            return f"{API_ERROR_PREFIX} Your Anthropic credit balance is too low. Please add credits at console.anthropic.com to continue using Claude."
        raise


def claude_generate_markdown(prompt: str, api_key: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1400,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except anthropic.BadRequestError as e:
        if "credit balance is too low" in str(e):
            return f"{API_ERROR_PREFIX} Your Anthropic credit balance is too low. Please add credits at console.anthropic.com to continue using Claude."
        raise
