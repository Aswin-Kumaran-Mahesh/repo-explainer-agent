import os
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from src.file_filter import should_ignore


@dataclass
class ChunkMeta:
    file_path: str
    start_line: int
    end_line: int
    text: str


def read_text_file(path: str, max_chars: int = 200_000) -> str:
    # Avoid huge files killing memory
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
            return data[:max_chars]
    except Exception:
        return ""


def chunk_by_lines(text: str, lines_per_chunk: int = 200, overlap: int = 30) -> List[Tuple[int, int, str]]:
    lines = text.splitlines()
    chunks = []
    i = 0
    n = len(lines)
    while i < n:
        start = i
        end = min(i + lines_per_chunk, n)
        chunk_text = "\n".join(lines[start:end]).strip()
        if chunk_text:
            chunks.append((start + 1, end, chunk_text))  # 1-indexed lines
        i = end - overlap
        if i < 0:
            i = 0
        if end == n:
            break
    return chunks


def collect_code_files(repo_path: str) -> List[str]:
    files_out = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not should_ignore(d)]
        for f in files:
            if should_ignore(f):
                continue
            full = os.path.join(root, f)
            # skip very large files
            try:
                if os.path.getsize(full) > 2_000_000:  # 2MB
                    continue
            except Exception:
                continue
            files_out.append(full)
    return files_out


def build_faiss_index(repo_path: str, model_name: str = "all-MiniLM-L6-v2"):
    model = SentenceTransformer(model_name)

    code_files = collect_code_files(repo_path)

    metas: List[ChunkMeta] = []
    texts: List[str] = []

    for fp in code_files:
        txt = read_text_file(fp)
        if not txt.strip():
            continue
        for (s, e, chunk_text) in chunk_by_lines(txt):
            metas.append(ChunkMeta(file_path=fp, start_line=s, end_line=e, text=chunk_text))
            texts.append(chunk_text)

    if not texts:
        raise ValueError("No indexable text found in repo (maybe only binaries or ignored files).")

    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)
    dim = embeddings.shape[1]

    index = faiss.IndexFlatIP(dim)  # cosine similarity via normalized + inner product
    index.add(embeddings.astype(np.float32))

    return index, metas, model
