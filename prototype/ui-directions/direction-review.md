# UI direction review

Assumptions:
- Desktop-first web prototype for adjusters/reviewers and SIU.
- No approved brand name, logo, palette, typography, or existing design system was found.
- All three directions use the same representative claim and current project metrics.
- Vehicle imagery remains an explicit placeholder until the team provides approved assets.

Directions:
1. A — Operations Workbench: default reviewer queue; maximum scan speed.
2. B — Evidence Ledger: auditability, provenance, presentation and compliance.
3. C — Triage Map: relationship investigation and SIU workflow.

## Comparison

| Direction | Best for | Main strength | Trade-off |
| --- | --- | --- | --- |
| A — Operations Workbench | Adjusters and claim reviewers | Fast review of images, documents, extracted fields and warnings on one screen | Dense when a case contains many relationships |
| B — Evidence Ledger | Audit, governance and progress-report demonstrations | Clear provenance and an evidence trail for every recommendation | Slower for high-volume queue work |
| C — Triage Map | SIU and fraud investigation | Makes shared entities and point-in-time graph signals visible | Too specialized to be the only claim workspace |

Recommended product composition: use A as the main claim workspace, reuse B's evidence/provenance treatment in a case-history drawer, and expose C as a separate Relationship Watch tab. This remains a recommendation until a direction is approved.

## Shared model boundary for the prototype

All directions should read the same versioned `ClaimAnalysis` response. During UI work the response can come from a checked-in fixture; the live adapter can later call the inference API without changing page components.

Minimum response sections:

- `claim`: identifiers, intake values and timestamps.
- `damage`: checkpoint version, masks, class scores and cautions.
- `documents`: document type, OCR text references, extracted fields and confidence.
- `consistency`: rule identifiers, severity and supporting values.
- `relationships`: point-in-time nodes, edges and provenance.
- `risk`: research score, route recommendation and model/version metadata.
- `review`: human decision, correction reason and audit timestamps.

The first implementation milestone should package a fixture adapter, a live API adapter, health/version endpoints and a model registry manifest containing hashes, schemas and validation metrics. Model outputs remain decision support and require a human decision in the prototype.

No direction has been approved yet. Do not build the full clickable prototype until the user selects or combines directions.
