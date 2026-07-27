# Mycelium key-gated synthesis eval

model: anthropic/claude-sonnet-5

q-refund-alice: sentences=2 ungrounded=0 answer='Your refund window is 30 days from the delivery date, not the order date. This same 30-day window ap'
q-expense-alice: sentences=2 ungrounded=0 answer='Submit your expense report through the finance portal within 14 days of the spend. Be sure to attach'
q-holiday-alice: sentences=4 ungrounded=0 answer='The company observes 12 public holidays in 2026, which are listed on the intranet calendar. Offices '

| metric | value | bound | pass |
|---|---|---|---|
| citation coverage | 1.00 | >= 1.0 | PASS |
| grounding validity | 1.00 | >= 1.0 | PASS |

contract: contracts/retrieval-stability.yaml (keyless invariant measured by scripts/eval.py; this section measures the synthesis stage)
