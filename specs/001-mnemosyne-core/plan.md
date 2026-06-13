# Plan: Component A — `mnemosyne` core

**Date:** 2026-06-12 · **Spec:** `./spec.md` · **Tasks:** `./tasks.md`

Lean plan — design decisions over execution phases. The RFC is the contract; this
records *how* the core is built and the choices a reviewer must be able to judge.

## Build order (dependency-driven)

The RFC lists A1→A4; the build order is engine-first because models and the
repository surface need a `DeclarativeBase`/`MetaData` and an engine factory to
exist before they can be defined or fanned out.

1. **Foundation (A4-engine + A1-base)** — package skeleton: schema-bound
   `DeclarativeBase`, portable types, `DATABASE_URL` engine factory, scoped
   session + boundary enforcement, capability declaration, config. *The contract
   every namespace module conforms to — built by the orchestrator, not fanned out.*
2. **A1 models** — fan out **one subagent per namespace** (8 parallel), each
   introspecting live PG and emitting `models/<ns>.py`. Verified by schema-diff.
3. **Schema-diff harness** — `tools/schema_diff.py`; the FR-1 acceptance test.
4. **A2 surface** — repository/query API, scoped-session lifecycle, boundary tests.
5. **A4 capabilities** — capability map + pgvector/sqlite-vec parity on a synthetic
   fixture + fail-clear.
6. **A3 packaging** — import-guard CI, tag-cadence doc, #1300 compliance.

## Package layout

```
src/mnemosyne_core/
  __init__.py          # public re-exports (the sole import surface, A2.1)
  config.py            # env settings: DATABASE_URL, role, vector dim, sqlite path
  base.py              # DeclarativeBase + MetaData (naming convention, schema-bound)
  types.py             # portable column types: Vector, JSONB, ARRAY, UUID, TSVector
  engine.py            # backend factory (PG pool + pgvector + SET ROLE | SQLite + vec)
  session.py           # scoped session + namespace-boundary enforcement
  capabilities.py      # capability declaration + fail-clear
  repository.py        # typed query/repository surface (A2)
  namespaces.py        # the 8-namespace registry + Namespace enum
  models/
    __init__.py        # imports all namespace modules -> one MetaData
    _infra.py  entities.py  external.py  history.py
    triples.py  search.py  ai_memory.py  fleet_ops.py
  server.py            # existing MCP skeleton (kept; ping replaced later)
tools/
  schema_diff.py       # models <-> live PG drift check (FR-1)
```

## Design decisions

| Decision | Choice | Rationale |
| :-- | :-- | :-- |
| **Backend selection** | `DATABASE_URL` set → PG; unset → baked SQLite at `MNEMOSYNE_SQLITE_PATH` (default `./mnemosyne.db`) | RFC A4.1; SQLAlchemy-native `create_engine`. Supersedes legacy `PHDB_BACKEND` toggle. |
| **Schema binding** | One declarative module per namespace; every table `__table_args__={"schema": ns}` over a shared `MetaData` | RFC A1; native PG schemas. The two cross-schema duplicate names (`history`/`external` `documents`, `history`/`entities` `products`) are unambiguous when schema-qualified. |
| **Portable types** | `TypeDecorator`s that render PG type on PG, SQLite-compatible on SQLite: `Vector`→pgvector/sqlite-vec, `JSONB`→`JSON`, `ARRAY(int)`→`JSON`, `UUID`→`CHAR(36)`, `TSVector`→skip/`TEXT` | RFC A4.3 capability mapping; one model definition, two backends. |
| **SQLite schema mapping** | PG namespaces → `ATTACH DATABASE` aliases (schema names preserved) so `schema=` resolves on SQLite too | RFC A4.3 (PG-schema → prefix/`ATTACH`). Keeps models backend-agnostic. |
| **Role-aware engine** | On PG, a `connect` event issues `SET ROLE <MNEMOSYNE_DB_ROLE>` when set; no-op on SQLite | RFC B1 hook; A provides the *mechanism*, C defines the role/grant matrix. Default role until C lands. |
| **Namespace boundary** | A session is opened against a declared namespace set; a flush touching a table outside it raises `NamespaceBoundaryError` before SQL is emitted | RFC A1.3; enforced in Python at the session layer (DB grants are the second, authoritative guard via C). |
| **Public surface** | Stars import from `mnemosyne_core` top-level only (repository + models + session ctx); engine/sessionmaker are private (`_`-prefixed / not re-exported) | RFC A2.1; CI import-guard (A3.2) enforces no internal-path imports. |
| **Vector dim** | `MNEMOSYNE_VECTOR_DIM` env, default introspected (nomic-embed-text = 768) | Matches the live embedding config; re-embed required if changed. |
| **Models source of truth** | Live PG introspection is canonical; migrations/record classes give semantic intent | RFC: zero drift vs live PG is the acceptance. |
| **Schema-diff** | `tools/schema_diff.py` compares declared `MetaData` to `information_schema` over a `DATABASE_URL`; CI-runnable; orchestrator runs it via the phdb MCP as the in-session oracle | RFC A1.1 acceptance. |

## Risks / honest constraints

- **141 tables** is large; per-namespace fan-out may leave residual drift. The
  schema-diff harness is the truth-teller — drift is reported, not hidden, and
  flagged PARTIAL where real.
- **Live-PG schema-diff in CI** needs network reach to nas01 (Tailscale). In this
  session the orchestrator uses the phdb MCP as the oracle; the CI wiring is
  delivered but its live run happens where PG is reachable.
- **sqlite-vec / pgvector** are optional deps; capability declaration fails clear
  when absent rather than crashing.
