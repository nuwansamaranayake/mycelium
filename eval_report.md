# Mycelium golden retrieval eval report

reference_time: 2026-07-01T00:00:00+00:00 (staleness anchor; no wall-clock in this path)

q-refund-alice: top3=['doc-refund-policy'] expected=['doc-refund-policy']
q-expense-alice: top3=['doc-expense-policy'] expected=['doc-expense-policy']
q-vpn-alice: top3=['doc-vpn-setup'] expected=['doc-vpn-setup']
q-holiday-alice: top3=['doc-holiday-schedule'] expected=['doc-holiday-schedule']
q-onboarding-alice: top3=['doc-onboarding'] expected=['doc-onboarding']
q-incident-bob: top3=['doc-security-runbook'] expected=['doc-security-runbook']
q-payroll-harriet: top3=['doc-payroll-calendar'] expected=['doc-payroll-calendar']
q-api-eve: top3=['doc-api-auth'] expected=['doc-api-auth']
q-soc2-bob: top3=['doc-soc2-evidence'] expected=['doc-soc2-evidence']
q-brand-mona: top3=['doc-brand-guide'] expected=['doc-brand-guide']
q-acl-payroll-alice: top3=['doc-holiday-schedule', 'doc-refund-policy'] forbidden=['doc-payroll-calendar'] (planted ACL case)
q-acl-incident-alice: top3=['doc-onboarding'] forbidden=['doc-security-runbook'] (planted ACL case)
q-acl-soc2-mona: top3=['doc-holiday-schedule'] forbidden=['doc-soc2-evidence'] (planted ACL case)

| metric | value | bound | pass |
|---|---|---|---|
| retrieval_hit_at_3 | 1.0 | >= 0.85 | PASS |
| acl_leak_count | 0 | <= 0 | PASS |
| citation_validity | 1.0 | >= 1.0 | PASS |
| freshness_correctness | 1.0 | >= 1.0 | PASS |
| retrieval_stability_min | 1.0 | >= 0.6 | PASS |

key-gated synthesis section: run scripts/eval_llm.py (not part of this deterministic report)
