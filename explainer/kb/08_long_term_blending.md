# Long-term blending

Long-term blending is the practice of keeping the **average fibre profile of
successive laydowns stable over weeks and months**, even as the specific bales
change. The mixing is planned so that this week's blend differs only slightly
from the rolling average of recent blends.

Why it matters:

- Yarn **count (linear density) and strength track the blend profile**; if the
  profile drifts, yarn count wanders bale-to-bale and downstream processes
  (warping, knitting, dyeing) must be re-tuned.
- Dye lots must match; a micronaire or maturity shift changes shade.
- Customers reject yarn for *inconsistency* as readily as for being off-spec.

Typical control: hold the blend's weighted-average micronaire within about
+/- 0.2 and strength within about +/- 1.0-1.5 g/tex of the trailing average
(e.g. last 30 laydowns). The optimiser encodes these as hard constraints so a
cheaper blend is never chosen at the cost of consistency.
