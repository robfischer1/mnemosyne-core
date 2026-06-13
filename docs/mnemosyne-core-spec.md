# Spec: Component A — `mnemosyne` core

| | |
| :-- | :-- |
| **Component** | A — `mnemosyne` core (Epic #816, succeeds #402) |
| **Initiative** | Mnemosyne — Store-Access Foundation (#815, Theme #1063) |
| **Repo** | `mnemosyne-core` (board tracking under `personal-history-db`) |
| **Feature branch** | `001-mnemosyne-core` |
| **Created** | 2026-06-12 |
| **Status** | Draft — review-spec gate |
| **Source RFC** | `Inbox/mnemosyne-store-access-foundation-rfc.md` — Component A |

## Scope (one sentence)

The shared typed **SQLAlchemy schema-contract package every star imports** — one
definition of the store's 8 namespaces, a repository/session surface as the sole
public API, packaged as a #1300-standard git-pinned dependency, with a **pluggable
PG | SQLite backend** selected at runtime (SQLite default for standalone degradation).

This Component is the **fan-in**: B (Hades), C (Grants), D (Helios), E (Clio) all
depend on it. It ships first. It builds **no** network door, **no** grant
definitions, **no** domain logic — those are B/C and the stars.

## User Stories

- **US1 — Typed models, no string SQL.** As a star author, I import `mnemosyne`
  and get typed models for the namespace I own, so I never build SQL by
  concatenation and there is one definition with no drift.
- **US2 — A managed query surface.** As a star author, I read/write through a
  typed repository/session API with no direct engine handle, so connection
  lifecycle is deterministic and leak-free.
- **US3 — One image, runtime backend.** As an operator, I select the backend by
  `DATABASE_URL` at runtime (PG when set, baked SQLite when unset), so a single
  image serves the corpus in production and runs standalone with no rebuild.
- **US4 — Boundaries hold.** As the platform, a write to a namespace the caller's
  contract does not declare is rejected before it reaches the DB.
- **US5 — Pinned consumption.** As a consuming star, I pin the core by `@tag` via
  `uv add git+…`, and CI fails if I import core internals by path.
- **US6 — Capabilities fail clear.** As a capability-sensitive star (e.g. vector
  search), I declare required capabilities; the core starts on a backend that can
  satisfy them and refuses startup — naming the missing capability — on one that
  cannot.

## Functional Requirements

Each FR cites its RFC slice and the board Story it maps to.

| FR | Requirement | RFC / Board |
| :-- | :-- | :-- |
| **FR-1** | Typed SQLAlchemy models cover all 8 namespaces (`_infra`, `entities`, `external`, `history`, `triples`, `search`, `ai_memory`, `fleet_ops`); a schema-diff check reports **zero drift** vs the live PG schema. | A1.1 / #837 |
| **FR-2** | The typed surface replaces raw SQL string-building; the hand-rolled dialect helpers (`FieldSpec`/`Schema` DDL) are **grep-clean** in any consuming star. | A1.2 / #838 |
| **FR-3** | A write to a namespace the caller's contract does not declare is **rejected before it reaches the DB** (boundary enforced at the model/session layer). | A1.3 / #839 |
| **FR-4** | A typed query/repository API is the **sole public import surface**; no direct engine/session handle is exposed to stars. | A2.1 / #840 |
| **FR-5** | Sessions/connections have a scoped, deterministic lifecycle; a soak test shows **no leaked connections**. | A2.2 |
| **FR-6** | #402 core-shared items (#240 write/visibility, #540 CLI, #536 predicate-query, #550 multi-tenant serving, #547 federated query, #542 `PHDB_DB_PATH`) are each **re-homed under A** with acceptance, or explicitly deferred with rationale. | A2.3 |
| **FR-7** | The core ships as a #1300-standard repo (src-layout, pyproject, uv.lock, publish-set) and passes the standard-compliance check with **zero structural edits**. | A3.1 |
| **FR-8** | Stars consume the core via `uv add git+…@tag`; CI **fails if a star imports core internals by path**. | A3.2 / #844 |
| **FR-9** | A **core-tag cadence policy** is documented (moving branch during Build, `@tag` pin at Harden). | A3.3 / #845 |
| **FR-10** | Backend is selected by runtime `DATABASE_URL`; absent → a **baked-default local SQLite** file (volume-mountable); switching needs **no rebuild**. | A4.1 |
| **FR-11** | Per-star **capability declaration + fail-clear** (e.g. vector search starts on PG/pgvector and SQLite/sqlite-vec; refuses startup naming the missing capability on SQLite without it). | A4.2 |
| **FR-12** | **SQLite-mode capability mapping** (pgvector→sqlite-vec, PG-schema→prefix/`ATTACH`, `SET ROLE`→no-op); mappable capabilities return identical results across PG and SQLite on a **synthetic fixture** (never the real corpus). | A4.3 |

## Data Contract

**Source of truth:** the live PG schema on nas01 (`postgresql://…/phdb`) is
canonical. Models are **introspection-faithful**; the 81 phdb migrations and the
`phdb.records.*` / `phdb.schemas.*` classes supply *semantic intent* (column
meaning, PII tier) but the live schema decides shape. The real corpus is **never**
copied — only its structure is read.

**Shape (introspected 2026-06-12):**

| Namespace | Tables | Columns | Role |
| :-- | --: | --: | :-- |
| `_infra` | 6 | 52 | migration/bookkeeping, source files |
| `entities` | 20 | 191 | identity-bearing rows (people, places, web pages…) |
| `external` | 2 | 18 | external-reference shims |
| `history` | 57 | 750 | the `history` domain (Clio's future home) |
| `triples` | 6 | 46 | RDF-style predicate graph |
| `search` | 6 | 46 | chunks + vectors (pgvector) |
| `ai_memory` | 35 | 303 | the witness layer (Helios's future home) |
| `fleet_ops` | 9 | 65 | dispatch/capacity ledger |
| **Total** | **141** | **1,471** | |

**Model layout:**
- One SQLAlchemy declarative module **per namespace** (`mnemosyne/models/<ns>.py`),
  each `Table` bound to its PG schema via `__table_args__ = {"schema": "<ns>"}`,
  over a shared `DeclarativeBase` / `MetaData`.
- **Namespace boundary:** a star declares the namespace contracts it imports; a
  session is scoped to that declared set; a write targeting an undeclared
  namespace raises **before flush** (FR-3).
- **Backend abstraction:** a single engine factory keyed on `DATABASE_URL`. PG uses
  native schemas + roles; SQLite maps namespaces to attached databases / table
  prefixes and `SET ROLE` to a no-op (FR-12).
- **Provenance tail:** the `raw_hash` / `source_file_id` / `created_at` tail
  carried by phdb typed tables is preserved in the models.

## Success Criteria

| SC | Falsifiable check |
| :-- | :-- |
| **SC-1** | `schema-diff` (models ↔ live PG) reports **zero drift** across all 8 namespaces. |
| **SC-2** | A reference consumer reads/writes using **only** the published API — no raw SQL, no engine handle; old dialect helpers grep-clean. |
| **SC-3** | `DATABASE_URL` set → connects PG; unset → connects baked SQLite; switching is config-only (no rebuild). |
| **SC-4** | An undeclared-namespace write is **rejected before the DB**. |
| **SC-5** | A capability-gated star starts on PG **and** SQLite-with-extension, and **refuses clear** on SQLite-without (message names the capability). |
| **SC-6** | Connection soak shows **zero leaks**; the repo passes #1300 compliance; a star pins the core by `@tag` and CI blocks path-imports. |

## Assumptions (← RFC Decision Log)

- **Greenfield code, keep the data.** The store is proven and stays PG on nas01; we
  rebuild only the access code. No in-place strangler of phdb.
- **Polyrepo; core is an internal git-pinned dep** (not PyPI-published) — no
  out-of-repo Python consumer; front-ends use Hades, not the core.
- **SQLite = local-only, never a corpus copy.** SQLite has no roles; a SQLite
  corpus copy would punch the grant model. Capability mapping is verified on a
  synthetic fixture only.
- **#402 kept.** Epic A succeeds its core role; #402's children distribute to A/C/E
  and sibling stars (not all folded into A — that re-monoliths).
- **Grants are C's.** A provides a **role-aware** engine/session (connects under a
  least-privilege PG role from env/secret); the tier→role→grant **matrix** is
  Component C. A is buildable before C lands, gated to a default role.

## Out of scope (Component A)

Hades network door (B) · grant/role definitions (C) · Helios (D) · Clio (E) · the
store/data itself · the #1300 substrate (Hazel) · the FSA pipeline (#815/B4).

## Board mapping

Epic **#816** → Features **#821** (A1), **#822** (A2), **#823** (A3), **#824** (A4)
→ Stories #837/#838/#839 (A1), #840 + session-lifecycle + #402-migration (A2),
#844/#845 (A3), backend-select/capability/mapping (A4). Tasks are deepened at
`tasks` time and kept in sync as Stories complete.
