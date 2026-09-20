# Follow-up posts

One finding each, one audience each, spaced two to four days apart. Every number comes
from `eval/baseline.json`. Run `python docs/linkedin/check.py` after edits — it checks
these blocks against the 3,000-character limit too.

Each ends with a question, because a post without one gets read and scrolled past.

---

## Post 2 — for mill people

> My optimiser tried to put 54.6% of a cotton blend into a single origin.
>
> Not because it was good. Because it was cheap.
>
> The origin in question is one that mixing masters cap on purpose — it carries
> contamination risk (polypropylene, hair, coloured fibre) that no amount of cleaning
> removes. It surfaces after dyeing, in the customer's fabric. A mill that has been burned
> once never forgets it.
>
> My cost optimiser did not know that. It saw a price discount and a fibre profile that
> passed the quality model, and it went straight for the corner. Every constraint I had
> given it was satisfied. The blend was "optimal" and completely unshippable.
>
> This is the part of ML that no accuracy metric catches. The model was fine. The
> optimiser was doing exactly what I asked. The gap was between what the mill knows and
> what I had written down.
>
> The fix was not a better model. It was a hard cap, in code, on that origin's share of any
> blend — applied regardless of price, in both optimisers, with a test that fails if it is
> ever removed.
>
> Every experienced operator carries a list of rules like this. Most of them have never
> been written down anywhere, which means an optimiser will violate every one of them on
> day one.
>
> If you run blending: what is the constraint you apply that has never made it into any
> system?
>
> Full write-up: <article link>
>
> #TextileIndustry #SpinningMill #CottonYarn #ManufacturingAnalytics #MachineLearning

---

## Post 3 — for ML people

> A prediction interval that is too narrow is worse than having no interval at all.
>
> My quality model predicts spun-yarn properties and gives a P10-P90 band for each. The
> band is not decoration: the confidence policy gates on the P10. If the mean clears the
> spec floor but the P10 does not, that is roughly a one-in-ten chance of shipping
> out-of-spec yarn, and the system must escalate to a human.
>
> So the band is the safety mechanism. And mine was lying.
>
> LightGBM quantile heads trained on ~400 rows overfit in-sample. The bands came out too
> narrow: 67% and 68% empirical coverage on two of the four targets, against a policy I had
> written myself demanding 70-90%. The gate meant to catch risk was manufacturing
> confidence instead.
>
> The fix was 5-fold cross-conformalized quantile regression: train the quantile heads
> out-of-fold, compute conformity scores max(lo − y, y − hi), take the finite-sample
> corrected quantile, widen the band additively. Distribution-free coverage under
> exchangeability, and about forty lines of code.
>
> Coverage went to 0.76 and 0.80. Point accuracy did not move at all — because the
> predictions were never the problem. The honesty about them was.
>
> If your model ships an uncertainty estimate, do you know its empirical coverage on
> held-out data? Not the nominal level. The measured one.
>
> Details: <article link>
>
> #MachineLearning #ConformalPrediction #MLOps #DataScience #ResponsibleAI

---

## Post 4 — for ML / governance people

> 0 of 50.
>
> That is how many of my optimiser's recommendations fell inside the region its own model
> was trained on.
>
> It makes sense in hindsight. The cheapest blend that still meets the quality spec is, by
> construction, unlike anything in the history: it concentrates on cheap bales and unusual
> origin mixes. No mixing master ever produced those blends, so the model never learned
> them. Every recommendation was an extrapolation.
>
> I only knew because I measured it: mean distance from the candidate blend to its five
> nearest training laydowns in standardised feature space, over the 99th percentile of that
> same distance within the training set. Ratio above 1 means the model is guessing.
>
> Then I tried to fix it — constrain blends to look more historical by tightening the
> per-bale share cap. It cut the in-band rate from 0.90 to 0.82, pushed the cost saving to
> roughly zero, and lifted in-support blends only to 8%. A bad trade. I reverted it and kept
> the measurement.
>
> So the system says it out loud instead: no out-of-support blend is ever rated HIGH
> confidence, which makes human review mandatory, and the reason is written into the audit
> log with the decision.
>
> This is the uncomfortable pattern in optimisation-over-ML generally. The optimiser's job
> is to find the extreme corner. The model is weakest exactly there. If you are running an
> optimiser on top of a learned model and not measuring support, you are trusting a guess.
>
> Are you measuring it?
>
> Write-up: <article link>
>
> #MachineLearning #MLOps #AIGovernance #ResponsibleAI #OperationsResearch

---

## Post 5 — for mill people, and an open invitation

> I built a blend optimiser on synthetic data. Here is what I would need from a real mill
> to make it real — and why the modelling is the easy part.
>
> 1. **Twelve months of laydowns linked to spun-yarn QC.** Not bale tests in one system and
> QC in another. The join. Which bales, what proportions, and what the yarn actually
> measured. This link is where most projects die.
>
> 2. **HVI coverage per bale, and honesty about AFIS.** Short-fibre content and maturity are
> the strongest non-linear drivers in the physics, and they are the ones most often missing.
> If AFIS coverage is thin, the model can estimate SFC from length uniformity and
> micronaire — with a documented error term and wider uncertainty, flagged as estimated.
>
> 3. **Agreed spec bands per count.** CSP floor, U% ceiling, imperfections, ends-down. In
> writing, signed by whoever owns quality — not inferred from history.
>
> 4. **Bale-level or lot-level price at planning time.** With a date on it. My system
> refuses to run on prices older than seven days, because an optimiser minimising against
> a stale price sheet is optimising fiction.
>
> 5. **Two hours a week of the mixing master's time.** For a shadow period where the system
> recommends and he decides, and nobody is asked to trust anything yet.
>
> That list is the 90-day plan, and four of the five items are data and agreement, not
> modelling. The ML is a few hundred lines. The reason these projects fail is item 1.
>
> If you run spinning: which of those five would be hardest in your plant? I would
> genuinely like to know which one I am underestimating.
>
> Full write-up and code: <article link>
>
> #SpinningMill #TextileIndustry #CottonYarn #ManufacturingAnalytics #MLOps
