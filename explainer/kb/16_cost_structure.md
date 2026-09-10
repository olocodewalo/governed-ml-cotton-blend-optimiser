# Yarn cost structure and why blend optimisation matters

For a typical cotton spinning mill, **raw cotton is 55-65% of the cost of
yarn**. Conversion cost (power, labour, stores, depreciation) is most of the
rest and is largely fixed in the short run.

Consequences:

- A **1% cut in cotton cost at constant quality is roughly a 0.6% cut in total
  yarn cost** -- large at industry margins.
- Cotton prices move weekly (MCX/ICE, arrivals, MSP, currency). A laydown that
  was optimal a month ago may be leaving money on the table now.
- The saving must be **at constant quality**: buying cheaper fibre that pushes
  the yarn out of spec, or raises ends-down, destroys more value than it saves.

This is why the optimiser minimises blend Rs/kg **subject to** predicted quality
staying inside the count's band and the blend staying close to the long-term
average.
