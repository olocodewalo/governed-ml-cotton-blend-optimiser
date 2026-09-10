# Ends-down (spinning breaks)

Ends-down is the rate of yarn breaks during ring spinning, quoted per 1000
spindle-hours. Every break is lost production plus a piecing operation, so it is
a direct productivity and cost metric.

Causes tied to the blend:

- **Low fibre strength** relative to what the count needs -- the yarn cannot
  take spinning tension.
- **High short-fibre content** -- weak thin spots break under tension.
- **High micronaire variance** -- uneven yarn has weak places.
- Interaction: weak fibre *and* high SFC together is much worse than either
  alone.

Fine counts (60s+) run higher ends-down for the same fibre because the yarn has
fewer fibres in its cross-section. The optimiser keeps predicted ends-down under
a count-specific ceiling.
