# LinkedIn post kit

Everything here is copy-paste ready. **Non-negotiable:** the "prototype on synthetic
data" line stays in the post itself, not only in the comments. Every number below
comes from `eval/baseline.json` (model v2, 50 held-out laydowns).

---

## Post A — the full version (governance + business + technical)

> My first write-up claimed a ~6% cost saving.
> Then I audited my own project, and the number dropped to 3.0%.
>
> That audit is the part I am actually proud of.
>
> **The problem.** Raw cotton is 55-65% of yarn cost in a spinning mill. Every week a
> mixing master decides the bale laydown — which bales, in what proportions — trading
> ₹/kg against spun-yarn quality. That decision usually lives in one expert's head and a
> spreadsheet, is not re-optimised when cotton prices move, and leaves no record of why a
> blend was chosen.
>
> **Why ML earns its place here.** Yarn quality is non-linear in the blend. Short-fibre
> content penalises strength with a power greater than 1. Micronaire *variance* across the
> blend hurts evenness independently of the mean. A linear cost rule cannot see either.
>
> **What I built** (Python, synthetic data, prototype scale):
> → LightGBM multi-output model predicting CSP, U%, imperfections and ends-down, with
> P10-P90 intervals calibrated by 5-fold conformalized quantile regression
> → A cost optimiser that treats quality as a constraint, not an objective: MILP (PuLP/CBC)
> on a linear surrogate, plus a genetic algorithm (DEAP) scoring against the full model
> → A confidence policy, a RAG + Claude explainer that writes the rationale but never
> touches a number, human Approve/Adjust/Reject, and an audit log of every decision
>
> **Then I audited it against my own governance doc. Five gaps:**
>
> 1. The model failed its own policy. I required 70-90% interval coverage; imperfections
> and ends-down sat at 67% and 68%.
> 2. An unapproved model was serving. Training quietly overwrote the "current" pointer, so
> a candidate went live without sign-off.
> 3. Drift detection, an out-of-support check, a price-freshness guard and a contamination
> cap were all written in the policy. None existed in the code.
> 4. The optimiser exploited that. On a 20s Ne scenario it put 54.6% of the blend into the
> one origin a mixing master caps for contamination risk, because it was cheap.
> 5. There was no CI — while the policy said the regression suite "fails CI".
>
> **What changed:**
> → Coverage fixed: 0.76 and 0.80, inside the policy band, with no loss of point accuracy
> → Training now produces a candidate only. Promotion runs the acceptance thresholds and
> the regression gate, and needs a named human approver. It refused my own promotion until
> I recorded why
> → Guards the optimiser cannot bypass: stale prices rejected, contamination-prone origins
> hard-capped
> → Drift monitoring: PSI, rolling MAE, correction count, new-origin triggers
> → Tests from 9 to 40, running in CI
>
> **And the honest headline:** evaluated on all 50 held-out laydowns instead of a
> 15-scenario sample, the saving at strictly matched quality is 3.0% (95% CI 0.8-5.5%),
> and the optimiser lands in the spec band 90% of the time (95% CI 0.79-0.96).
>
> The most uncomfortable finding: 0 of 50 optimiser blends fall inside the model's
> training support. The cheapest in-band blend is, by construction, unlike anything in the
> history the model learned from. I tried constraining blends to look more historical — it
> cost the saving and the in-band rate and fixed nothing. So the system says it out loud
> instead: every recommendation is capped at MEDIUM confidence and goes to a human.
>
> A smaller number I can defend beats a bigger number I cannot.
>
> This is a prototype on synthetic data, built to show the shape of a governed ML decision
> system — not a validated mill result. Code, the full write-up and the honest limitations
> are in the repo (link in the comments).
>
> If you run blending in a mill, I would genuinely like to know: what would you need to see
> before you let a system like this influence a real laydown?

---

## Post B — the short version (if you want higher reach)

> I cut my own project's headline result from 6% to 3%.
>
> It was a cotton blend optimiser for spinning mills: an ML quality model feeding a cost
> optimiser, with a human sign-off step. The first number came from a 15-scenario sample.
> Measured on all 50 held-out laydowns — and with the contamination cap a real mixing
> master would impose — the saving at matched quality is 3.0% (95% CI 0.8-5.5%).
>
> Auditing it also turned up something worse than a shrinking number: my governance doc
> described four controls my code did not implement, and an unapproved model was quietly
> serving predictions. The optimiser had found the gap and put 54.6% of one blend into the
> origin a mill caps for contamination risk.
>
> All five gaps are closed now: conformal intervals that pass their own policy, a
> promotion gate that refused me until a named human recorded a reason, guards the
> optimiser cannot bypass, drift monitoring, and 40 tests in CI.
>
> Prototype on synthetic data — the point is the governance, not the number. Repo in the
> comments.
>
> What would you need to see before letting a model influence a real bale laydown?

---

## First comment (post this yourself, right after publishing)

> Repo: https://github.com/<your-username>/cotton-blend-optimisation
>
> The README carries the full case study, the 90-day delivery plan, the RAID register, the
> model governance policy and the measurement plan. Every number regenerates with
> `make data && make train && make eval`, and `eval/baseline.json` is the frozen baseline
> the regression gate checks against.
>
> To be explicit: this runs on synthetic bale and laydown data generated from a
> hand-written physics surrogate. It is a design and governance demonstration, not a
> validated result from any mill.

---

## Tagging

LinkedIn ranks a post lower when it reads as tag-spam, so keep it to **5-8 mentions**,
and put company tags in the post only where they are genuinely relevant. **Verify every
handle before posting** — type "@" then the name and pick from LinkedIn's own dropdown.
Never tag a company in a way that suggests they were involved, gave data, or endorsed it.

**Tech / tools actually used in the project**
- Anthropic (Claude, used for the rationale layer)
- Streamlit
- Microsoft (LightGBM)
- COIN-OR Foundation (CBC solver, used via PuLP)
- GitHub

**Indian textile industry bodies**
- Confederation of Indian Textile Industry (CITI)
- The Southern India Mills' Association (SIMA)
- Texprocil
- Cotton Association of India
- SITRA / ATIRA / NITRA (textile research associations)

**International**
- International Textile Manufacturers Federation (ITMF)
- International Cotton Association

**Companies working in this space** (fibre testing, blend management, mill software)
- Uster Technologies
- Premier Evolvics
- Trützschler Group
- Rieter
- Lakshmi Machine Works
- Loepfe Brothers
- Datatex
- A.T.E. Group

A better-performing alternative to tagging company pages: tag 2-3 **people** — a spinning
technologist, a mill operations head, a textile-ML researcher — and ask them the closing
question directly. People reply; company pages rarely do.

**Hashtags (5-8 is the sweet spot)**
`#TextileManufacturing #SpinningMill #CottonYarn #MachineLearning #MLOps #OperationsResearch #ResponsibleAI #ManufacturingAnalytics`

---

## Posting checklist

1. **Carousel:** upload `docs/linkedin/slides/slide_1.png` … `slide_6.png` in order as a
   multi-image post, or combine them into one PDF for a document post (document posts
   usually get more dwell time).
2. **Or lead with the app screenshot** `docs/screenshots/01_review_screen.png` — it shows
   the MEDIUM confidence banner, the out-of-support warning and the price-age line, which
   is the whole story in one image.
3. Add alt text to each image (LinkedIn prompts for it); it helps reach and accessibility.
4. Repo link goes in the **first comment**, not the post body — LinkedIn suppresses posts
   with outbound links.
5. Make the repo public *before* posting, and check the README renders.
6. Reply to every comment in the first two hours.
