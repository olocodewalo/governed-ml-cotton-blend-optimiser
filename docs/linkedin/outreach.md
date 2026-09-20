# Getting this in front of people who hire

**The honest starting point.** A LinkedIn post reaches your existing network first. If
that network is mostly IT services, textile decision-makers will never see it, whatever
the hashtags say. The article and the repo are not the distribution — they are the proof
that survives contact with someone who is already interested. Distribution has to be
deliberate.

So: the post is done. The work that produces interview calls is below, in the order that
pays.

---

## 1. Profile, before anything else (30 minutes)

Everyone who sees the post and is interested lands on the profile next. Right now the
profile does not mention the thing they just read.

- **Featured section:** pin the article, and pin the repo link as a second item.
- **Headline:** add the proof domain. Something like
  *"Senior AI Programme Delivery Manager | ML governance for manufacturing decisions |
  Agentic AI, LLM & Intelligent Automation | 19 Yrs | Ahmedabad"*.
  "Agentic AI, LLM" is what everyone claims; "ML governance for manufacturing" is what you
  can now prove.
- **About:** three lines on this project with the repo link — what the decision was, what
  you built, what the audit found.
- **Skills:** add conformal prediction, MLOps, operations research, optimisation.

---

## 2. Direct outreach — this is the actual engine

25-40 personalised messages over two weeks beats any number of impressions. **Ask for
critique, never for a job.** A request for expert opinion gets answered; "any openings?"
does not.

### Who, by group

| Group | Roles to target | Names to start from |
|---|---|---|
| **Spinning mills (India)** | Head of IT / Digital Transformation, CIO, GM Spinning, Head of Quality, VP Ops | Vardhman, Trident, Nahar Spinning, Sutlej, KPR Mill, Nitin Spinners, Sangam India, RSWM, Arvind, Ashima, Chiripal, Welspun, Raymond |
| **Textile tech vendors** | Product managers, heads of digital/software, R&D leads | Uster Technologies, Premier Evolvics, Rieter, Trützschler, Loepfe, Datatex, A.T.E. Group, Lakshmi Machine Works |
| **Research bodies** | Technical directors, heads of research | **ATIRA (Ahmedabad — in your city)**, SITRA (Coimbatore), NITRA (Ghaziabad), BTRA (Mumbai), Textile Association of India |
| **AI/ML employers** | Head of Data/AI, Director of ML, Engineering Managers | Anywhere hiring for ML platform / MLOps / responsible AI |

**ATIRA is the single cheapest high-value move you have.** It is in Ahmedabad, its whole
job is mill technical research, and a face-to-face conversation there is worth more than
10,000 impressions. Ask for 30 minutes to show a prototype and get it torn apart.

### Message templates

**To a mill IT / digital head**

> Hello <name> — I build ML systems for a living and spent the last few weeks on a
> problem from your world: the weekly bale laydown. Cotton is 55-65% of yarn cost, the
> decision usually sits with one experienced person, and almost nothing about it gets
> recorded.
>
> I built a working prototype — quality model, cost optimiser with the spec band as a hard
> constraint, and a review screen where the mixing master approves or adjusts. It runs on
> synthetic data, so I am not claiming a mill result.
>
> What I actually want is a reality check: does the laydown decision work anything like
> this in your plant, and what would make this useless to you? 15 minutes would help me a
> lot. Write-up here if you want to look first: <article link>

**To a textile tech vendor (Uster, Premier, Rieter, Datatex…)**

> Hello <name> — I have been building a decision-support prototype for bale laydown
> planning: LightGBM quality model with calibrated prediction intervals, MILP + GA cost
> optimiser with contamination caps and long-term-blend drift limits, human sign-off, full
> audit trail.
>
> I would value a practitioner's view on where it is naive — particularly on how mills
> really handle HVI/AFIS coverage gaps and price freshness. Code and the full write-up are
> public: <repo link>
>
> If you are ever hiring for people who can sit between mill domain and ML, I would be glad
> to talk.

**To an AI/ML hiring manager**

> Hello <name> — most ML portfolio projects report accuracy. I wrote one up that reports
> the opposite: I audited my own project and my headline saving dropped from 6.4% to 3.0%
> once I measured it on the full held-out set and added a constraint a real plant would
> impose.
>
> The interesting part is the governance: a promotion gate that refused my own model until
> a named human recorded a reason, conformal intervals that pass the policy I had written,
> drift triggers, and 40 tests in CI. <article link>
>
> If that is the kind of engineering your team cares about, I would like to talk.

**To a consulting / AI services leader**

> Hello <name> — I put together an end-to-end case study on a manufacturing decision:
> cotton bale blending, where the raw material is 55-65% of product cost. It covers the
> whole delivery shape, not just a model: 90-day plan, RAID register, RACI, model
> governance policy, cost model, value hypothesis — plus working code and CI.
>
> It is the artefact I would want to hand a client in week one of a discovery. Happy to
> walk you through it: <article link>

---

## 3. Trade media — where textile decision-makers actually read

Higher-value reach for this audience than LinkedIn. These publications take contributed
technical articles. **Verify current submission contacts before pitching** — editors and
addresses change.

- **Fibre2Fashion** (India, very large reach in textiles)
- **Textile Value Chain** (Mumbai; technical + management readership)
- **The Indian Textile Journal**
- **Textile Excellence**
- **Journal of the Textile Association** (TAI — peer-reviewed, strong technical credibility)
- **Textile Today** (South Asia)
- **Textile World** (US/global)

Pitch angle: *"Where machine learning actually earns its place in blend planning — and the
five governance gaps I found in my own prototype."* The self-audit angle is what makes it
publishable rather than promotional.

A trade article needs a rewrite: mill language, no code, no CI badges, 1,200-1,500 words.
Worth doing once and submitting to two or three of the above.

---

## 4. Conferences and bodies

A 15-minute technical talk in front of mill technical heads beats months of posting.

- Textile Association of India (TAI) conferences and local chapter meets
- ATIRA / SITRA / NITRA technical seminars
- India ITME, ITMA side events and technical sessions
- CITI, SIMA, TEXPROCIL events

Pitch the same self-audit angle. Bodies are short of speakers who can talk about ML
without selling something.

---

## 5. Post cadence — one post proves nothing

One post is an event; a series is a position. Four to six posts over three weeks, each
carrying **one** finding, each aimed at a different audience:

| # | Angle | Audience | Status |
|---|---|---|---|
| 1 | The audit — 6.4% became 3.0% | Everyone | Published |
| 2 | 54.6% of a blend went into a contamination-capped origin | Mill people | Draft below |
| 3 | Narrow prediction intervals are worse than none | ML people | Draft below |
| 4 | 0 of 50 recommendations were inside training support | ML / governance | Draft below |
| 5 | What I would need from a mill to make this real | Mill people, invites conversation | Draft below |

Drafts live in `followups.md`.

---

## What not to do

- Engagement pods and bought engagement. Textile leaders are a small world; it shows.
- Mass-tagging companies. It reads as spam and LinkedIn discounts it.
- DMing recruiters with "any openings?". Zero reply rate, and it wastes the artefact.
- Claiming mill results. Everything here is synthetic. The credibility comes from saying
  so — that is the whole point of the post.
