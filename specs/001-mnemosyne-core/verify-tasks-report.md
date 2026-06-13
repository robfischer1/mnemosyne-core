# Verify-tasks report — Component A (`mnemosyne` core)

**Date:** 2026-06-12 · **Scope:** all · **Mode:** orchestrator-run (parent Opus,
not the implementing subagents — caller-judges-output)

> The 8 namespace models were authored by local subagents. This verification was
> run by the orchestrator against independent evidence (the live PG schema via the
> MCP oracle, the full lint/type/test gate, and the assembled metadata) — the
> subagents did **not** mark their own homework. One real defect their self-reports
> missed (history's `real` columns mapped to `Float`) was caught here and fixed.

## Scorecard

| Verdict | Count |
| :-- | :-- |
| ✅ VERIFIED | 25 |
| 🔍 PARTIAL | 2 |
| ❌ NOT_FOUND | 0 |

Gate at verification time: **ruff PASS · mypy PASS · pyright PASS · pytest 32 passed**
(incl. live PG: schema-diff zero drift, PG↔SQLite vector parity, no-leak soak).

## Verified

| Task | Evidence (layers 1/3/4/5) |
| :-- | :-- |
| T001 config | file ✓ · `Config.from_env` ✓ · imported by engine/repo ✓ · 3 tests green |
| T002 namespaces | file ✓ · `Namespace` (8), `ALL_NAMESPACES`, `SEARCH_PATH_ORDER` ✓ · used everywhere ✓ · test green |
| T003 base | file ✓ · `Base`, `metadata` ✓ · 141 tables register on it ✓ |
| T004 types | file ✓ · `Vector/JSONB/BigIntArray/IntArray/TSVector/UUIDType` ✓ · used by models ✓ · per-dialect render tests green |
| T005 engine | file ✓ · `make_engine` (PG pool+pgvector+SET ROLE / SQLite pragmas+sqlite-vec+translate) ✓ · engine-selection test green |
| T006 session | file ✓ · `scoped_session`, `NamespaceBoundaryError` ✓ · boundary enforced both directions (tests) |
| T007 capabilities | file ✓ · `Capability`, `require`, `available_capabilities`, `sqlite_vec_loadable` ✓ · fail-clear test green |
| T008 foundation tests | 16 cases green |
| T010–T017 models (8 ns) | 8 files ✓ · 141 classes ✓ · all import ✓ · **schema-diff zero drift** (below) |
| T018 models assembly | `import mnemosyne_core.models` → 141 tables / 1,471 cols, 0 collisions ✓ |
| T020 schema_diff | file ✓ · `declared_shape/live_shape/diff/main` ✓ · console entry ✓ · zero drift via oracle |
| T021 schema_diff tests | diff + canon vocabulary unit-tested (incl. real-vs-Float) ✓ |
| T030 repository | file ✓ · `Repository.open/session/get/add/list` ✓ · used in tests ✓ |
| T031 public surface | `Repository` in `__all__`; `make_engine`/`sessionmaker` not exposed ✓ |
| T032 repository tests | reference consumer add/get/list + boundary + hidden-engine green |
| T040 capability parity | portable Vector round-trip + **real sqlite-vec KNN** + capability mapping green |
| T041 import-guard | file + console entry ✓ · flags internal imports, allows public (tests) |
| T042 tag-cadence doc | `docs/core-tag-cadence.md` present ✓ |
| T043 README + deps | README rewritten; sqlalchemy/psycopg/pgvector/sqlite-vec pinned; 3 console scripts ✓ |

## FR-1 zero-drift evidence (the headline acceptance)

Declared models compared to the **live PG store** (introspected via the phdb MCP,
2026-06-12). All four cross-checks exact across 141 tables / 1,471 columns:

| Check | Result |
| :-- | :-- |
| Table set per namespace | ✅ exact (6/35/20/2/9/57/6/6) |
| Per-table column counts (141 tables) | ✅ exact — 0 missing, 0 extra, 0 mismatched |
| Canonical type histogram (8 namespaces) | ✅ exact (after fixing 5 `real` cols) |
| Nullability split (8 namespaces) | ✅ exact |

**Exhaustive live run (2026-06-12):** `mnemosyne-schema-diff` executed against the
live PG store (`postgresql://forge@100.93.64.106/phdb` via SQLAlchemy) reports
**`ZERO DRIFT -- models match the live store`** — the full per-column-name + type
+ nullability diff across all 141 tables / 1,471 columns, not just the aggregate.

## Closed against live PG (2026-06-12)

| Item | Verdict | Evidence |
| :-- | :-- | :-- |
| FR-1 schema-diff (live) | ✅ VERIFIED | `mnemosyne-schema-diff` → ZERO DRIFT against the live store |
| A4.3 PG↔SQLite vector parity | ✅ VERIFIED | `test_pg_sqlite_knn_parity_identical` — pgvector (temp table) and sqlite-vec return the **same** nearest neighbour on a synthetic fixture |
| A2.2 no-leak soak (#841) | ✅ VERIFIED | `test_sessions_released_no_leak_soak` — 200 cycles, checkouts == checkins |
| A2.3 #402 disposition (#842) | ✅ VERIFIED | `402-disposition.md` — each item re-homed or deferred with rationale |

## Still partial (honest)

| Task | Verdict | Gap |
| :-- | :-- | :-- |
| T005 SET ROLE leg | 🔍 PARTIAL | mechanism delivered + SQLite no-op path covered; the live PG `SET ROLE` under a least-privilege role is **Component C's** acceptance (roles/grants) — C is inflight in a parallel session. |
| A4.3 SQLite ATTACH fidelity | 🔍 PARTIAL | `schema_translate_map`→flatten ships + tested; ATTACH-per-namespace (for `documents`/`products` duplicate-name fidelity on a single SQLite file) is a documented follow-on in `engine.py`, beyond #848's stated acceptance. |

## Not in this push (sibling scope)

- Components B (Hades), C (Grants — inflight elsewhere), D (Helios), E (Clio).
