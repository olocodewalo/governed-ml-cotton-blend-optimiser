"""RAG quality check for the LLM explainer (faithfulness + answer relevance).

Uses Ragas if installed and an ANTHROPIC_API_KEY is present. Otherwise runs a
lightweight lexical-overlap proxy so `make eval` still produces a number.

Run: ``python -m eval.ragas_eval``
"""
from __future__ import annotations

import json

from config import anthropic_key
from explainer.generate import explain_blend
from explainer.retriever import retrieve
from optimiser.common import load_current_model, make_scenario, naive_baseline
from optimiser.lp import solve_lp

N_RUNS = 10
COUNTS = ["20s_Ne", "30s_Ne", "40s_Ne", "60s_Ne"]


def _samples():
    model = load_current_model()
    out = []
    for i in range(N_RUNS):
        count = COUNTS[i % len(COUNTS)]
        sc = make_scenario(count, inventory_size=110, seed=1000 + i,
                           bias=("cheap" if i % 2 else None))
        res = solve_lp(sc, model)
        base = naive_baseline(sc, model)
        exp = explain_blend(sc, res, base)
        contexts = [h["text"] for h in retrieve(f"{count} blend rationale", k=4)[0]]
        out.append(dict(question=f"Why is this blend recommended for {count}?",
                        answer=exp.rationale, contexts=contexts,
                        llm_model=exp.llm_model))
    return out


def _proxy_scores(samples):
    """Cheap proxy: token-overlap of answer with its retrieved contexts
    (faithfulness) and with the question (relevance)."""
    import re

    def toks(s):
        return set(re.findall(r"[a-z]{4,}", s.lower()))

    faith, rel = [], []
    for s in samples:
        a = toks(s["answer"])
        ctx = set().union(*[toks(c) for c in s["contexts"]]) if s["contexts"] else set()
        q = toks(s["question"])
        faith.append(len(a & ctx) / max(len(a), 1))
        rel.append(len(a & q) / max(len(q), 1))
    return dict(faithfulness_proxy=round(sum(faith) / len(faith), 3),
                answer_relevance_proxy=round(sum(rel) / len(rel), 3))


def main() -> None:
    samples = _samples()
    result = dict(n=len(samples), llm_model=samples[0]["llm_model"])

    used_ragas = False
    if anthropic_key():
        try:
            from datasets import Dataset
            from ragas import evaluate
            from ragas.metrics import answer_relevancy, faithfulness
            ds = Dataset.from_list([{k: s[k] for k in ("question", "answer", "contexts")}
                                    for s in samples])
            scores = evaluate(ds, metrics=[faithfulness, answer_relevancy])
            result["ragas"] = {k: round(float(v), 3) for k, v in scores.items()}
            used_ragas = True
        except Exception as e:  # pragma: no cover
            result["ragas_error"] = f"{type(e).__name__}: {e}"

    if not used_ragas:
        result["proxy"] = _proxy_scores(samples)
        result["note"] = "Ragas unavailable or no API key -- lexical proxy shown."

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
