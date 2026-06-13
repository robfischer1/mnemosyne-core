# #402 core-shared item disposition (A2.3 / board #842)

Epic #402 ("phdb Core") was the titan's grab-bag. The RFC keeps #402 and
distributes its children to real homes. Here is the disposition of the six
core-shared items the RFC routed at Component A — each **re-homed under A with an
acceptance**, or **explicitly deferred with rationale**.

| #402 item | Disposition | Where / why |
| :-- | :-- | :-- |
| **#240** write/visibility tools | **Re-homed (write) + deferred (visibility)** | The *write* surface is `Repository.add` / typed sessions (A2). *Visibility* (who-sees-what) is a **grant** concern → Component **C**, not A. A's namespace-boundary is the first guard; C's roles are authoritative. _Acceptance (write): a star persists via `Repository` with no raw SQL — met (`test_repository`)._ |
| **#540** CLI | **Deferred** | A typed *library* contract has no CLI surface; a CLI is a per-star or ops concern. No core acceptance depends on it. Re-open as a star/ops task if a need appears. |
| **#536** predicate-query tools | **Deferred → triples/graph star** | The `triples` namespace models ship in A (the contract); the *query tools* over predicates are a sibling-star concern (the triples/graph Initiative under Theme #1063), not the shared core. Modeling ≠ querying. |
| **#550** multi-tenant serving | **Re-homed (satisfied in A)** | The namespace-scoped `Repository` + the role-aware engine **are** multi-tenant serving: each star is a tenant scoped to its declared namespaces (Python guard) and its PG role (C). _Acceptance: a star reads/writes only its declared namespaces — met (`test_repository` boundary)._ |
| **#547** federated query | **Deferred** | Cross-namespace / cross-store federation is a higher layer (a star, or Hades). A provides the typed single-store access it would build on; federation is out of the core's single-concern. |
| **#542** `PHDB_DB_PATH` | **Re-homed (superseded in A4)** | Replaced by `MNEMOSYNE_SQLITE_PATH` (+ `DATABASE_URL` as the backend selector). _Acceptance: backend/path is env-selected with a baked default — met (`test_foundation`, `Config.from_env`)._ |

**Summary:** re-homed-in-A — #240(write), #550, #542; deferred-with-rationale —
#240(visibility, → C), #540, #536(→ triples star), #547. No #402 item is silently
dropped.
