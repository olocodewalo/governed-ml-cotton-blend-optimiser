"""Tiny retriever over the fibre-science knowledge base (explainer/kb/*.md).

Tries a local sentence-transformers model for semantic search; if it is not
installed (or offline), falls back to a TF-IDF cosine retriever so the pipeline
still runs. Both are cached in-process.
"""
from __future__ import annotations

import functools
import re
from pathlib import Path

import numpy as np

KB_DIR = Path(__file__).parent / "kb"


def load_kb() -> list[dict]:
    docs = []
    for p in sorted(KB_DIR.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip()
        docs.append(dict(id=p.stem, title=title, text=text, path=str(p)))
    return docs


class _Tfidf:
    def __init__(self, docs):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.docs = docs
        self.vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
        self.mat = self.vec.fit_transform([d["text"] for d in docs])

    def search(self, query, k):
        from sklearn.metrics.pairwise import cosine_similarity
        q = self.vec.transform([query])
        sims = cosine_similarity(q, self.mat)[0]
        idx = np.argsort(sims)[::-1][:k]
        return [(self.docs[i], float(sims[i])) for i in idx]


class _SBert:
    def __init__(self, docs):
        from sentence_transformers import SentenceTransformer
        self.docs = docs
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.emb = self.model.encode([d["text"] for d in docs], normalize_embeddings=True)

    def search(self, query, k):
        q = self.model.encode([query], normalize_embeddings=True)[0]
        sims = self.emb @ q
        idx = np.argsort(sims)[::-1][:k]
        return [(self.docs[i], float(sims[i])) for i in idx]


@functools.lru_cache(maxsize=1)
def _index():
    docs = load_kb()
    try:
        return _SBert(docs), "sentence-transformers/all-MiniLM-L6-v2"
    except Exception:
        return _Tfidf(docs), "tfidf-fallback"


def retrieve(query: str, k: int = 4) -> tuple[list[dict], str]:
    idx, backend = _index()
    hits = idx.search(query, k)
    out = []
    for doc, score in hits:
        out.append(dict(id=doc["id"], title=doc["title"], score=round(score, 3),
                        text=doc["text"]))
    return out, backend


def snippet(text: str, max_chars: int = 700) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= max_chars else text[:max_chars] + " ..."
