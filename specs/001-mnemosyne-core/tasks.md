# Tasks: Component A — `mnemosyne` core

**Spec:** `./spec.md` · **Plan:** `./plan.md` · **Date:** 2026-06-12
`[P]` = parallelizable · `[x]` = complete · maps to board Epic #816.
Verdicts in `./verify-tasks-report.md` (orchestrator-run cascade).

## Phase 1 — Foundation (A4-engine + A1-base)

- [x] **T001** `config.py` — env settings: `DATABASE_URL`, `MNEMOSYNE_DB_ROLE`, `MNEMOSYNE_VECTOR_DIM`, `MNEMOSYNE_SQLITE_PATH`.
- [x] **T002** `namespaces.py` — the 8-namespace `Namespace` enum + registry + search-path order.
- [x] **T003** `base.py` — `DeclarativeBase` + `MetaData` with naming convention.
- [x] **T004** `types.py` — portable types: `Vector`, `JSONB`, `BigIntArray`, `IntArray`, `TSVector`, `UUIDType`.
- [x] **T005** `engine.py` — `make_engine()`: `DATABASE_URL`→PG (pool, pgvector, `SET ROLE`), unset→SQLite (pragmas, sqlite-vec, schema_translate_map).
- [x] **T006** `session.py` — `scoped_session(namespaces)` + `NamespaceBoundaryError`; deterministic close.
- [x] **T007** `capabilities.py` — `Capability` enum + `require()` fail-clear + `sqlite_vec_loadable()`.
- [x] **T008** `tests/test_foundation.py` — foundation unit tests (16 cases, SQLite-backed).

## Phase 2 — A1 models (fan-out, board #837/#838/#839)

- [x] **T010 [P]** `models/_infra.py` — 6 tables / 52 cols.
- [x] **T011 [P]** `models/entities.py` — 20 tables / 191 cols.
- [x] **T012 [P]** `models/external.py` — 2 tables / 18 cols.
- [x] **T013 [P]** `models/triples.py` — 6 tables / 46 cols.
- [x] **T014 [P]** `models/search.py` — 6 tables / 46 cols (pgvector `Vector(768)`).
- [x] **T015 [P]** `models/fleet_ops.py` — 9 tables / 65 cols (bigint arrays).
- [x] **T016 [P]** `models/ai_memory.py` — 35 tables / 303 cols (vector, uuid, jsonb, arrays).
- [x] **T017 [P]** `models/history.py` — 57 tables / 750 cols (jsonb, real).
- [x] **T018** `models/__init__.py` — assembles all 8 into one MetaData: 141 tables / 1,471 cols, zero collisions.

## Phase 3 — Schema-diff harness (FR-1, board #837)

- [x] **T020** `schema_diff.py` — declared↔live drift check over `DATABASE_URL`; canonical type vocabulary. **Orchestrator-verified zero drift via the MCP oracle** (table set + per-table counts + type histograms + nullability all exact). Live-CI run executes where PG is reachable.
- [x] **T021** `tests/test_schema_diff.py` — diff logic + canon vocabulary unit-tested (incl. the real-vs-Float trap).

## Phase 4 — A2 surface (board #822 / #840)

- [x] **T030** `repository.py` — typed `Repository`: `open`/`session`/`get`/`add`/`list`, namespace-scoped, no engine/session leak.
- [x] **T031** `__init__.py` — public re-exports (`Repository`, `Namespace`, `Capability`, `scoped_session`, ...); engine/sessionmaker NOT exported.
- [x] **T032** `tests/test_repository.py` — reference consumer reads/writes via API only; boundary enforced; surface hides engine.

## Phase 5 — A4 capabilities + A3 packaging (board #823/#824, #844/#845)

- [x] **T040** `tests/test_capabilities_parity.py` — portable Vector round-trip + real sqlite-vec KNN + capability mapping (vector_search both backends; role_enforcement PG-only). PG/pgvector leg runs under `DATABASE_URL`.
- [x] **T041** `import_guard.py` + `tests/test_import_guard.py` — flags consumer imports of core internals; console entry `mnemosyne-import-guard`.
- [x] **T042** `docs/core-tag-cadence.md` — branch-during-Build → `@tag`-at-Harden policy.
- [x] **T043** README + `pyproject` deps (sqlalchemy, psycopg, pgvector, sqlite-vec) + console scripts.

## Phase 6 — Verify + promote + board

- [x] **T050** Orchestrator-run verify cascade → `./verify-tasks-report.md`.
- [x] **T051** Promote `spec.md` → `docs/`.
- [x] **T052** Board: Epic #816 + Features/Stories updated per verified state.

## Closed against live PG (2026-06-12)

- **FR-1 schema-diff** — `mnemosyne-schema-diff` run live → **ZERO DRIFT** (full per-column diff, 141 tables / 1,471 cols).
- **A2.2 #841 soak** — `test_sessions_released_no_leak_soak` (200 cycles, balanced checkout/checkin).
- **A4.3 #848 PG↔SQLite parity** — `test_pg_sqlite_knn_parity_identical` (pgvector temp table vs sqlite-vec, same nearest neighbour).
- **A2.3 #842 #402 disposition** — `402-disposition.md` (each item re-homed or deferred with rationale).

## Carried (honest deferrals)

- **SET ROLE live leg** — mechanism in `engine.py`; the live least-privilege-role test is **Component C's** acceptance (inflight in a parallel session).
- **A4.3 SQLite ATTACH-per-namespace fidelity** — flatten ships + tested; ATTACH mode for duplicate-name fidelity (`documents`/`products` on one SQLite file) is a documented `engine.py` follow-on, beyond #848's acceptance.
