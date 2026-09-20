# Trade-press article — submission package

For Fibre2Fashion, Textile Value Chain, The Indian Textile Journal, Journal of the Textile
Association, Textile Excellence, Textile Today.

**Word count:** ~1,450. **Angle:** not a product pitch — a practitioner's account of
building a blend-planning prototype and then finding five holes in it, written so a mill
reader comes away able to interrogate *any* vendor selling this.

---

## Title options

1. **What I learned auditing my own cotton blend optimiser** *(recommended — the
   self-audit is what makes it publishable rather than promotional)*
2. Before you buy a blend optimiser: five questions your vendor should be able to answer
3. The bale laydown is the most expensive decision in the mill. Can software help?

## Standfirst / dek

> Raw cotton is the largest single cost in a spinning mill, and the weekly bale laydown
> that commits it usually lives in one person's experience. Machine learning can support
> that decision — but a prototype built and then deliberately audited shows where these
> systems quietly go wrong, and what a mill should demand before trusting one.

---

## Article body

### The decision worth the attention

In a ring-spinning mill, raw cotton is typically 55-65% of the cost of the yarn.
Everything else — power, stores, labour, depreciation, packing — competes for the rest. It
follows that the most expensive recurring decision in the plant is not a machine setting
or a maintenance schedule. It is the weekly bale laydown: which bales from the godown go
into the mixing, and in what proportion.

The mixing master is balancing four things at once, usually without writing any of it
down. Cost, because bales differ in rupees per kilo by origin, grade and lot. Quality,
because the yarn has to hit the count's band for CSP, U%, imperfections and ends-down.
Consistency, because the mixing has to stay close to the rolling average of recent
laydowns or the count and dye pick-up will wander between lots. And risk, because
contamination travels with certain origins and cannot be cleaned out downstream — it
appears after dyeing, in the customer's fabric.

Most mills do this well. What most mills do not do is record *why*. When a lot goes
wrong, the reasoning cannot be reconstructed. When the mixing master retires, it leaves
with him. And the laydown is rarely re-planned when cotton prices move mid-week, because
re-doing the whole judgement by hand is not practical.

That gap — not the arithmetic, but the *record* — is what drew me to build a prototype.

### Why a spreadsheet rule is not enough

The obvious approach is a rule: filter bales on micronaire and staple, then buy the
cheapest that pass. Every mill has a version of this. It fails for a specific reason —
yarn quality does not respond to the mixing in a straight line.

Short-fibre content is the clearest case. A mixing at 13% SFC is not "a bit worse" than
one at 9%; the penalty to strength and evenness accelerates. Micronaire is subtler still:
it is not only the average that matters but the *spread*. Two mixings with identical mean
micronaire will spin differently if one blends coarse and fine fibre while the other is
tight around the mean, because the spread drives evenness and neps on its own. And neps
come from two sources — immature fibre and short fibre — that multiply each other rather
than simply adding.

A linear rule cannot see any of that, and a lookup table cannot either, because the
interactions live in a continuous space. This is the narrow case where a learned model
genuinely earns its place: it can approximate that response surface from the mill's own
history, and — this matters more than it sounds — it can be *wrong in measurable ways*.

### What the system actually does

The shape is simple, and the order of the steps is the point.

A quality model predicts CSP, U%, imperfections and ends-down from the mixing's aggregate
fibre profile, and reports a range rather than a single number. A cost optimiser then
finds the cheapest mixing available from today's godown **subject to** that predicted
quality staying inside the count's band, the fibre profile staying within drift limits of
the rolling average, and caps on contamination-prone origins. Quality is a constraint, not
something traded away.

The recommendation then goes to the mixing master with a plain-language explanation of
which limits are binding and why, and he approves it, adjusts it, or rejects it. Every
decision — recommendation, predicted quality, confidence, his choice and his reason — is
written to a log.

The master stays in charge throughout. That is not a courtesy; it is a design requirement,
for reasons the audit made obvious.

### Then I audited my own prototype, and found five holes

I had written a governance policy for the prototype before building it: what accuracy was
acceptable, what had to be checked before a model could be used, what would trigger a
retrain. Then I checked the system against my own document.

**The model failed my own accuracy requirement.** I had required that the predicted range
actually contain the true value about 80% of the time. On two of the four properties it
was managing 67% and 68%. The ranges looked reassuring and were too narrow — which is
worse than no range at all, because the safety check depends on them.

**A model nobody had approved was in use.** Training a new model silently replaced the one
in service. There was no sign-off step in practice, only in the document.

**Four controls existed only on paper.** Drift detection, a check for recommendations that
fall outside anything the model had seen, a refusal to plan against stale prices, and a
cap on contamination-prone origins were all written in the policy. None of them existed in
the running system.

**The optimiser exploited exactly that.** On a coarse-count scenario it put **54.6% of the
mixing into a single origin** — the one a mixing master caps deliberately for
contamination risk. It was cheap, it passed every constraint I had actually implemented,
and it was completely unshippable. No accuracy metric would ever have caught it.

**And the most uncomfortable finding:** when I measured how similar each recommendation was
to the mill's historical mixings, *none* of them were close. That is not a bug — the
cheapest acceptable mixing is by construction unlike anything a master has run before. But
it means every recommendation is the model working beyond its experience. I tried forcing
the recommendations to look more historical; it cost the saving and the quality hit rate
and fixed nothing. So the system now declares it instead: any such recommendation is
capped at medium confidence and cannot bypass the human.

### The number that got smaller

My first write-up claimed roughly a 6% cost saving at matched quality. That figure came
from fifteen test scenarios.

Measured across all fifty held-out historical laydowns, with the contamination cap a real
mill would impose, the saving is **3.0%, with a 95% confidence interval of 0.8% to 5.5%**.
The optimiser's pick met the quality band 90% of the time. Nothing about the system got
worse between the two numbers. The measurement got honest.

This is worth dwelling on, because it is exactly how impressive numbers are produced —
a small sample, a favourable configuration, and no interval. **All of this runs on
synthetic data generated from a simplified physics model, not on any mill's records.** The
only number that would mean anything commercially is one measured in a shadow pilot
against the mixing master's own choices, at matched quality.

### What a mill would actually need

If a mill wanted to make this real, four of the five requirements are not about modelling
at all.

Twelve months of laydowns **linked** to the spun-yarn QC of what they produced — not bale
tests in one system and yarn results in another, but the join between them. Honest HVI
coverage, and clarity about AFIS: short-fibre content and maturity are the strongest
drivers in the physics and the most commonly missing measurements; where they are absent
they can be estimated, but the estimate must be flagged and the uncertainty widened.
Agreed spec bands per count, in writing, owned by whoever is accountable for quality.
Bale or lot price available at planning time, with a date attached. And two hours a week
of the mixing master's time during a shadow period in which the system recommends, he
decides, and nobody is asked to trust anything yet.

In most projects of this kind, the first item is where it stops.

### Questions worth asking any vendor

- On how many laydowns was your saving measured, and what is the confidence interval?
- Was quality held equal in that comparison, or only "within spec"?
- What does the system do when the recommendation is unlike anything in its training data?
- How does it handle a bale with no AFIS data?
- What happens if the price sheet is two weeks old?
- Who approves a new model version before it influences a laydown, and where is that
  recorded?
- Show me the log of a recommendation that the mixing master rejected, and why.

A vendor who can answer those is worth talking to. One who leads with an accuracy figure
is not yet ready for your plant.

### What it is really for

The saving is the easy thing to sell and the hardest thing to prove. The durable value is
different: a mill that runs a system like this ends up with a written record of every
blending decision, the reasoning behind it, and what the yarn actually did. That record is
the thing that survives a retirement, settles an argument about a bad lot, and turns one
person's judgement into something the plant owns.

The technology for this is not the obstacle. The data discipline is.

---

## Author bio (include at the end)

> Ankit Nandkishor Agrawal is an AI programme delivery manager based in Ahmedabad with 19
> years in technology delivery. The prototype described here — a quality model, a
> constrained cost optimiser and a human-review workflow for bale laydown planning — was
> built on synthetic data as an engineering study. The code and the full technical write-up
> are public at github.com/olocodewalo/governed-ml-cotton-blend-optimiser.

## Pull quotes for layout

> "It was cheap, it passed every constraint I had actually implemented, and it was
> completely unshippable."

> "Nothing about the system got worse between the two numbers. The measurement got honest."

> "The technology for this is not the obstacle. The data discipline is."

## Images to submit

| File | Caption |
|---|---|
| `docs/screenshots/01_review_screen.png` | The review screen: recommended mixing, predicted quality with its range, the confidence level and the reasons behind it, and the age of the prices it planned against. |
| `docs/linkedin/slides/slide_9.png` | Every headline figure before and after the audit, measured on fifty held-out laydowns. |
| `docs/linkedin/slides/slide_6.png` | Two optimisers: a fast linear solver for explainability, a slower search that scores against the full non-linear model. |

---

## Pitch email to the editor

> Subject: Article submission — what I learned auditing my own cotton blend optimiser
>
> Dear <editor>,
>
> I have written a 1,450-word piece for <publication> on decision support for bale laydown
> planning, from the perspective of someone who built a prototype and then audited it
> against his own governance standards — and found five holes, including an optimiser that
> put 54.6% of a mixing into a contamination-capped origin because it was cheap.
>
> It is not a product pitch; I have nothing to sell. The aim is to give mill readers a set
> of questions to put to anyone selling this kind of system, and an honest account of what
> the data requirements really are. The prototype runs on synthetic data and the article
> says so plainly.
>
> The piece, three images with captions and a short author bio are attached. Happy to
> adjust length or angle to suit the issue.
>
> Regards,
> Ankit Nandkishor Agrawal
> Ahmedabad | <phone> | <email>
