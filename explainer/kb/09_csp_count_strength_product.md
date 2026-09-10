# CSP -- Count Strength Product

CSP = (lea strength in lb) x (English count Ne). It is the traditional
single-number strength index for ring-spun cotton yarn; a lea is 120 yards.

- Higher CSP = stronger yarn for its fineness.
- Driven mainly by **fibre strength, staple length, and low short-fibre
  content**, then by twist and evenness.
- Weaving mills specify a **minimum CSP** per count; below it, warp breaks and
  loom stops rise sharply.

Approximate expectations for carded/combed cotton:

| Count | Typical CSP band |
|------:|:-----------------|
| 20s   | 2000-2200 |
| 30s   | 2100-2400 |
| 40s   | 2250-2600 |
| 60s   | 2400-2800 |

The optimiser treats the count's minimum CSP as a hard floor and, because the
prediction has uncertainty, can be set to require the **P10 (lower) estimate**
to clear the floor.
