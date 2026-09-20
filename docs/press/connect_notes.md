# Connection notes and follow-ups

**Limits:** a connection note is **300 characters**. A LinkedIn message after they accept
is 8,000. An InMail (Premium) is 1,900 in the body plus a subject line.

**The rule that makes this work:** the note does not ask them to read anything. Reading a
1,400-word article is a large favour to ask a stranger. The note asks a **question they
can answer from experience in one line** — that is a small favour, and it flatters their
expertise rather than borrowing their attention. The article goes in the follow-up, after
they have accepted and ideally replied.

Never mention a job in the first two messages. You are asking for a critique. If the
conversation goes well, the job conversation starts itself.

**Volume:** 10-15 a week, each with the first clause genuinely personalised — their mill,
their count range, something they posted. A batch of identical notes is visible from
orbit and burns the list.

Run `python docs/linkedin/check.py` after editing; it enforces the 300-character limit on
every note below.

---

## Connection notes (300 characters max)

**Connect 1 — mill technical head / GM spinning**

> <Name>, I build ML systems and spent a month on a mill problem — the weekly bale
> laydown. My prototype put 54.6% of a mixing into one contamination-risk origin because
> it was cheap. Would value your view on what else it would get wrong in a real plant.

**Connect 2 — mill IT / digital transformation head**

> <Name>, I built a decision-support prototype for laydown planning: quality model, cost
> optimiser with the spec band as a hard constraint, mixing master approves or rejects.
> Synthetic data, nothing to sell. Would value 15 minutes of criticism from your side.

**Connect 3 — director / owner**

> <Name>, cotton is 55-65% of yarn cost, yet the weekly laydown decision rarely leaves any
> record of why. I built a prototype that recommends it and logs the reasoning, then
> published what it got wrong. You would spot the holes faster than I did.

**Connect 4 — head of quality / yarn QC**

> <Name>, a question from a prototype I built: if predicted CSP clears the floor but the
> lower bound of the range does not, does your QC treat that as acceptable risk or reject
> it? I had to pick a rule and I would rather hear yours.

**Connect 5 — textile machinery / instrument vendor (Uster, Premier, Rieter, Datatex)**

> <Name>, I have built an open prototype for bale laydown optimisation — calibrated
> quality ranges, cost optimiser, contamination caps, human sign-off. I would value a
> practitioner's view on where it is naive, particularly around AFIS coverage gaps.

**Connect 6 — research body (ATIRA, SITRA, NITRA, TAI)**

> <Name>, I am in Ahmedabad and have built a blend-optimisation prototype on synthetic
> data, with the governance wrapper rather than just a model. I would value 30 minutes
> with someone at <body> to have the physics assumptions torn apart.

**Connect 7 — short, highest accept rate**

> <Name>, I built a bale-laydown optimiser and then audited it until my own headline
> number halved. I am looking for critique from people who actually plan mixings — would
> value your view, even if it is that the whole idea is wrong.

---

## Follow-up, after they accept

Send this within a day of acceptance. Still no job mention.

> Thank you for connecting, <name>.
>
> Short version of what I built: a quality model that predicts CSP, U%, imperfections and
> ends-down from a mixing's fibre profile, a cost optimiser that finds the cheapest
> mixing with the spec band as a hard constraint rather than a target, and a review screen
> where the mixing master approves, adjusts or rejects — with every decision logged.
>
> Then I audited it against my own standards and it failed in five places. The one that
> stayed with me: it put 54.6% of a mixing into a single contamination-risk origin,
> because it was cheap and every constraint I had actually implemented was satisfied.
>
> It runs on synthetic data, so I am not claiming a mill result — my measured saving is
> 3.0% at matched quality, with a wide confidence interval, and that is exactly the kind
> of number I think mills should interrogate when a vendor quotes one.
>
> Write-up here if it is useful: <article link>
>
> What I would really value is 15 minutes of your criticism — particularly on what a
> system like this would get wrong in your plant. Happy to work around your schedule.

## Follow-up, if they reply but have no time

> Completely understood, <name>. If it is ever easier, one question by message would help
> me more than nothing: of these five, which would be hardest in your plant —
> (1) linking twelve months of laydowns to the yarn QC they produced, (2) AFIS coverage,
> (3) agreed spec bands per count in writing, (4) bale-level price with a date on it, or
> (5) two hours a week of the mixing master's time?
>
> Whatever you pick, I will know which part of my plan is naive.

---

## InMail version (Premium, 1,900 characters — for people you cannot connect with)

**Subject:** A blend-planning prototype, and the five holes I found in it

> <Name>, I am writing because you have run mixings at a scale I have only modelled.
>
> I spent the last month building a decision-support prototype for the weekly bale
> laydown: a model that predicts CSP, U%, imperfections and ends-down from the mixing's
> fibre profile, a cost optimiser that minimises rupees per kilo with the count's spec
> band as a hard constraint, and a review screen where the mixing master approves,
> adjusts or rejects — with every recommendation and decision logged.
>
> Then I audited it against the governance standards I had written for myself, and it
> failed in five places. Four of them were controls that existed only in my document and
> not in the running system. The fifth was the optimiser exploiting exactly that gap: on a
> coarse count it put 54.6% of the mixing into a single contamination-risk origin,
> because it was cheap and every constraint I had actually implemented was satisfied.
>
> It runs on synthetic data, so I am not claiming a mill result. The measured saving at
> strictly matched quality is 3.0%, with a 95% confidence interval from 0.8% to 5.5% —
> and my first, smaller-sample version of that number was nearly double.
>
> I am not selling anything. I would value 15 minutes of your criticism on what this would
> get wrong in a real plant, and which of the data requirements is least realistic.
>
> Write-up: <article link>
>
> Thank you for reading this far.

---

## Who to send to, in order

1. **ATIRA, Ahmedabad** — in your city, research is their job, and a face-to-face beats
   every message here.
2. Heads of quality and GM spinning at mills running 20s-60s Ne counts.
3. IT / digital transformation heads at the larger groups — they own the budget for this
   kind of system.
4. Product and R&D leads at the instrument and machinery vendors.
5. Directors and owners last. They reply least often, and a reply from their technical
   head carries more weight when you eventually reach them.

## Tracking

Keep a simple sheet: name, company, role, date sent, accepted, replied, what they said.
Twenty rows tells you which opening line works. The replies are also the most valuable
input you will get on the project itself — better than any metric in the repo.
