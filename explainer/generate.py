"""LLM rationale generator (light RAG).

Given an optimiser run, retrieve relevant fibre-science notes and ask Claude for
a 4-6 sentence plain-language rationale, grounded ONLY in the retrieved notes
and the run's numbers. If no ANTHROPIC_API_KEY (or the SDK is missing), fall
back to a deterministic templated rationale so the pipeline never blocks.
"""
from __future__ import annotations

from dataclasses import dataclass

from config import ANTHROPIC_MODEL, QUALITY_TARGETS, anthropic_key
from explainer.retriever import retrieve, snippet

SYSTEM = (
    "You are a spinning-mill blending assistant. Explain a recommended cotton "
    "bale laydown to a mixing master in plain language. Use ONLY the supplied "
    "knowledge-base notes and run numbers. Do not invent figures. 4-6 sentences, "
    "no bullet points, no preamble. Name the binding constraints and why the "
    "fibre science makes them bind."
)


@dataclass
class Explanation:
    rationale: str
    sources: list
    retriever_backend: str
    llm_model: str          # "templated-fallback" when offline
    prompt_chars: int = 0


def _query(scenario, result) -> str:
    parts = [f"yarn count {scenario.target_count}"]
    parts += [b for b in result.binding_constraints]
    prof = result.profile
    parts.append(f"blend micronaire {prof['w_mean_micronaire']:.2f} spread {prof['w_var_micronaire']:.3f}")
    parts.append(f"blend SFC {prof['w_mean_short_fibre_content_pct']:.1f}")
    parts.append("cost vs quality trade-off, long-term blending")
    return "; ".join(parts)


def _facts_block(scenario, result, baseline) -> str:
    spec = scenario.spec
    lines = [f"Target yarn count: {scenario.target_count}",
             f"Spec band: min CSP {spec['min_csp']}, max U% {spec['max_u_pct']}, "
             f"max imperfections {spec['max_imperfections']}, max ends-down {spec['max_ends_down']}",
             f"Recommended blend price: {result.price_inr_per_kg} INR/kg "
             f"over {sum(1 for w in result.weights if w > 1e-4)} bales",
             "Predicted quality (mean [P10-P90]):"]
    for t in QUALITY_TARGETS:
        p = result.predicted[t]
        lines.append(f"  {t}: {p['mean']:.1f} [{p['p10']:.1f}-{p['p90']:.1f}]")
    prof = result.profile
    lines.append(f"Blend fibre profile: micronaire {prof['w_mean_micronaire']:.2f} "
                 f"(spread {prof['w_var_micronaire']:.3f}), staple {prof['w_mean_staple_length_mm']:.1f} mm, "
                 f"strength {prof['w_mean_strength_gtex']:.1f} g/tex, "
                 f"SFC {prof['w_mean_short_fibre_content_pct']:.1f}%")
    rp = scenario.rolling_profile
    lines.append(f"Rolling 30-laydown average: micronaire {rp['w_mean_micronaire']:.2f}, "
                 f"strength {rp['w_mean_strength_gtex']:.1f} g/tex "
                 f"(drift limits +/-{scenario.mic_tol} and +/-{scenario.strength_tol})")
    if baseline is not None:
        saving = baseline.price_inr_per_kg - result.price_inr_per_kg
        band = "in band" if baseline.in_band else ("OUT OF BAND -- not a like-for-like comparison, "
                                                   "do not call the difference a saving")
        lines.append(f"Naive baseline blend: {baseline.price_inr_per_kg} INR/kg ({band}) "
                     f"-> difference {saving:.1f} INR/kg ({100*saving/baseline.price_inr_per_kg:.1f}%)")
    lines.append("Binding / violated constraints: " +
                 (", ".join(result.binding_constraints) or "none (comfortably in band)"))
    return "\n".join(lines)


def _templated(scenario, result, baseline, sources, backend) -> Explanation:
    binding = result.binding_constraints or ["no binding constraints"]
    prof = result.profile
    save_txt = ""
    if baseline is not None:
        s = baseline.price_inr_per_kg - result.price_inr_per_kg
        pct = 100 * s / baseline.price_inr_per_kg
        if baseline.in_band:
            save_txt = (f" It costs {result.price_inr_per_kg:.1f} INR/kg, about "
                        f"{pct:.1f}% below the naive baseline at comparable predicted quality.")
        else:
            save_txt = (f" It costs {result.price_inr_per_kg:.1f} INR/kg against the naive baseline's "
                        f"{baseline.price_inr_per_kg:.1f}, but that baseline is outside the spec band, "
                        f"so the difference is the price of meeting quality, not a saving.")
    csp = result.predicted["csp"]
    txt = (
        f"For {scenario.target_count} the optimiser recommends a {sum(1 for w in result.weights if w>1e-4)}-bale "
        f"blend at weighted micronaire {prof['w_mean_micronaire']:.2f} and strength "
        f"{prof['w_mean_strength_gtex']:.1f} g/tex, staying within the long-term-blend drift limits so yarn "
        f"count stays consistent. Predicted CSP is {csp['mean']:.0f} (P10 {csp['p10']:.0f}) against a floor of "
        f"{scenario.spec['min_csp']}, and evenness/imperfections sit inside the band. "
        f"The active limits are: {'; '.join(binding)}. "
        f"Short-fibre content ({prof['w_mean_short_fibre_content_pct']:.1f}%) and micronaire spread "
        f"({prof['w_var_micronaire']:.3f}) are the fibre properties doing the most to hold quality, because both "
        f"penalise strength and evenness faster than linearly.{save_txt} "
        f"Review the P10-P90 band before approving: a wide band means the blend profile is unusual and warrants a check."
    )
    return Explanation(rationale=txt, sources=sources, retriever_backend=backend,
                       llm_model="templated-fallback")


def explain_blend(scenario, result, baseline=None, k: int = 4) -> Explanation:
    hits, backend = retrieve(_query(scenario, result), k=k)
    sources = [dict(id=h["id"], title=h["title"], score=h["score"]) for h in hits]

    key = anthropic_key()
    if not key:
        return _templated(scenario, result, baseline, sources, backend)

    try:
        import anthropic
    except Exception:
        return _templated(scenario, result, baseline, sources, backend)

    kb_block = "\n\n".join(f"### {h['title']} ({h['id']})\n{snippet(h['text'], 900)}" for h in hits)
    user = (
        f"KNOWLEDGE BASE NOTES:\n{kb_block}\n\n"
        f"THIS RUN:\n{_facts_block(scenario, result, baseline)}\n\n"
        f"Write the rationale for the mixing master now."
    )
    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=ANTHROPIC_MODEL, max_tokens=450, system=SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        return Explanation(rationale=text, sources=sources, retriever_backend=backend,
                           llm_model=ANTHROPIC_MODEL, prompt_chars=len(user))
    except Exception as e:  # network / auth / rate-limit -> graceful fallback
        exp = _templated(scenario, result, baseline, sources, backend)
        exp.rationale += f"\n\n[note: LLM call failed ({type(e).__name__}); templated rationale shown]"
        return exp
