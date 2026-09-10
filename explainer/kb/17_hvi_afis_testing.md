# HVI vs AFIS testing

**HVI (High Volume Instrument)**: fast, bale-level. Reports micronaire, upper-half
mean length, uniformity index, bundle strength, elongation, colour (Rd, +b),
trash area. One reading per bale is normal. It does **not** measure short-fibre
content or neps directly, and it blends fineness with maturity in micronaire.

**AFIS (Advanced Fiber Information System)**: slower, sample-level. Reports
single-fibre length distribution (hence **SFC**), **nep count and size**,
**maturity ratio**, fineness, and trash particle counts. Used for process
troubleshooting and for combed/fine-count work.

Practical implication for this project: most mills have years of HVI data but
little AFIS, and rarely link either to the **spun-yarn QC result**. The data
layer's job is to digitise bale tests, join them to the laydown that consumed
them and to that lot's yarn QC, and flag where SFC/maturity must be *estimated*
from HVI because AFIS is missing.
