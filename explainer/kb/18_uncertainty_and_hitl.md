# Prediction uncertainty and the human-in-the-loop

The quality model outputs a mean plus a **P10-P90 band** for each property. The
band matters as much as the point estimate:

- A blend whose **mean** CSP clears the spec but whose **P10** does not is a
  gamble -- roughly a 1-in-10 chance the real yarn misses. The optimiser can be
  set to require the P10 to clear the floor for critical properties.
- A **wide band** means the model is extrapolating -- usually the candidate
  blend's aggregate profile is unlike anything in the training laydowns
  (unusual origin mix, extreme SFC). These recommendations should always go to a
  human.

Confidence policy: the system **auto-suggests only when the band is tight enough
and inside spec with margin**; otherwise it presents the recommendation as "for
review" and asks the mixing master to accept, adjust, or reject. Every decision,
and the reason, is logged.
