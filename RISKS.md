# Risk Register — Mycelium

A living register. Every risk carries an owner, a concrete tripwire (an observable signal that says
"this is happening now"), and a status. Seeded from the BLUEPRINT "Failure Modes and Mitigations";
expand it as real failures land in `FAILURES.md`.

| Risk | Owner | Tripwire | Status |
|---|---|---|---|
| **Owner ping fatigue** — routed gap tickets overwhelm the humans who know, so they stop answering and the healing loop stalls. Mitigated by per-owner rate limits, weekly demand-ranked batches, and a visible credit loop ("you closed 6 gaps asked about 40 times"). | eng lead | Any owner's median gap-ticket response time exceeds 7 days for two consecutive weekly batches, **or** a single owner receives more than the configured per-owner weekly ping cap. | open |
| **Wrong ownership inference** — tickets route to someone who does not own the topic, eroding trust in the loop. Mitigated by using explicit metadata first, signal-based fallback second, and a one-click reassign on every ticket. | eng lead | Ticket reassignment rate exceeds 20% of routed tickets over a rolling 30-day window. | open |
