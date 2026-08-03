# API Contracts — Mycelium

Doctrine Rule 6. **Derivation rule: this table derives from the served `/openapi.json`,
never from router source** (decorators are pre-prefix declarations). Enforcement is
literal — parameter spellings included — in both directions, and planned rows must not be
served yet. `tests/test_contracts.py` runs it in CI.

| Frontend call | Method | Path | Status | Notes |
|---|---|---|---|---|
| Landing page (browser) | GET | `/` | implemented (not in schema) | Next.js static export served by FastAPI; carries the EVAL.md limits block verbatim. |
| Demo page (browser) | GET | `/demo` | implemented (not in schema) | The ACL refusal screen. |
| API reference | GET | `/docs` | implemented (not in schema) | FastAPI-served. |
| OpenAPI schema | GET | `/openapi.json` | implemented (not in schema) | This file is checked against it. |
| Health probe | GET | `/health` | implemented | `{status, env}`. |
| Load demo fixture | GET | `/api/v1/demo` | implemented | Development-only; 503 outside development. |
| Register a principal | POST | `/api/v1/principals` | implemented | Admin-gated; issues the per-principal bearer. |
| Upload a document (JSON) | POST | `/api/v1/documents` | implemented | Admin-gated; text + ACL list. |
| Upload a document file (PDF/docx) | POST | `/api/v1/documents/upload` | implemented | Admin or demo session; demo uploads are tenant-forced (prefixed title, tenant-only ACL, never wildcard). |
| Ingest a folder | POST | `/api/v1/ingest/folder` | implemented | Admin-gated, keyless connector. |
| Open a demo session | POST | `/api/v1/demo/session` | implemented | Public by design: issues scoped credentials; seeds two principals with their own tokens + four documents. |
| Run a query | POST | `/api/v1/query` | implemented | Per-principal bearer; response carries `acl.{visible,excluded}_documents` computed before scoring, and per-result freshness labels. |
| Synthesize the cited answer | POST | `/api/v1/answers` | implemented | Admin, or the token of the principal who ran the query. Sentences carry `grounded` + `passage_ids`; ungrounded counted. |
| Read an answer | GET | `/api/v1/answers/{aid}` | implemented | Principal-gated read-back. |
