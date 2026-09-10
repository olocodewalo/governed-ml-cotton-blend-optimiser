# RACI -- Cotton Blend Optimisation

R = Responsible, A = Accountable, C = Consulted, I = Informed.
One **A** per row.

| Activity | Mixing Master | Yarn QC Lead | Data Engineer | ML Engineer | MLOps | Product / PM | Plant Manager | Procurement |
|---|---|---|---|---|---|---|---|---|
| Define spec bands per count | C | A | I | I | - | R | C | I |
| Data contracts (lab, QC, price) | I | C | R | C | C | A | I | C |
| Bale/QC data pipeline + feature store | I | C | **A/R** | C | C | I | I | I |
| Quality model training & uncertainty | I | C | C | **A/R** | C | I | I | I |
| Model registry & version sign-off | I | C | I | R | C | **A** | I | I |
| Optimiser formulation & constraints | C | C | I | **A/R** | I | C | I | C |
| Confidence policy & thresholds | C | C | I | R | I | **A** | C | I |
| LLM explainer + knowledge base | C | C | I | **A/R** | I | C | I | I |
| HITL review (weekly, per laydown) | **A/R** | C | I | I | I | I | I | I |
| Approve / Adjust / Reject a blend | **A/R** | C | I | I | I | I | I | I |
| Golden set & regression suite | I | C | C | **A/R** | C | I | I | I |
| Retrain trigger & execution | I | I | C | R | **A** | I | I | I |
| Cost model & value measurement | I | C | C | C | I | **A/R** | C | C |
| Go / No-Go before influencing a real laydown | C | C | I | C | I | R | **A** | I |
| Change Advisory Board for model changes | C | C | C | R | R | **A** | C | I |
| Incident response (bad blend in production) | R | R | C | C | C | I | **A** | I |
| Audit log retention & review | I | C | R | I | **A** | C | I | I |

**Notes**

- The **mixing master owns every operational blend decision**. The system
  recommends; it never overrides.
- **Product/PM is accountable for governance artefacts** (registry sign-off,
  confidence policy, CAB) so model changes cannot ship silently.
- **Plant Manager holds the Go/No-Go** -- the point where the tool is allowed to
  influence real production.
