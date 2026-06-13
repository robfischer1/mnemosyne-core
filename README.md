# Mnemosyne Core

The shared **typed schema-contract** every Mnemosyne star imports -- one
SQLAlchemy definition of the corpus store's 8 namespaces, a repository/query
surface as the sole public API, and a **pluggable PostgreSQL | SQLite backend**
selected at runtime. (Component A of the Store-Access Foundation, Initiative
#815.)

- **One contract, no drift.** Typed models mirror the live PostgreSQL store across
  all 8 namespaces (`_infra`, `entities`, `external`, `history`, `triples`,
  `search`, `ai_memory`, `fleet_ops`) -- 141 tables / 1,471 columns. A schema-diff
  check fails CI if the models and the store disagree.
- **One image, two backends.** `DATABASE_URL` set → PostgreSQL (the corpus, pooled,
  pgvector-aware, role-enforced); unset → a baked local SQLite file (sqlite-vec,
  WAL pragmas) so a star runs standalone. No rebuild to switch.
- **Boundaries the DB enforces.** A star declares the namespaces it owns; a write
  outside them is rejected before it reaches the DB (and, on PostgreSQL, by grant).

## Use it (as a star)

```python
from sqlalchemy import select

from mnemosyne_core import Namespace, Repository
from mnemosyne_core.models.ai_memory import Sessions

# Opens the env-selected backend; scoped to the declared namespaces.
repo = Repository.open([Namespace.AI_MEMORY])

with repo.session() as s:
    rows = s.scalars(select(Sessions).limit(10)).all()
```

A star imports the **public surface** only -- `Repository`, `Namespace`,
`scoped_session`, `Capability`, the `mnemosyne_core.models` namespace modules, and
`mnemosyne_core.types`. Never the internals (`engine`, `session`, `base`). The
import-guard enforces this in CI.

## Configure (env)

| Var | Default | Purpose |
| :-- | :-- | :-- |
| `DATABASE_URL` | _(unset)_ | set → PostgreSQL backend; unset → baked SQLite |
| `MNEMOSYNE_SQLITE_PATH` | `mnemosyne.db` | SQLite file path when `DATABASE_URL` is unset |
| `MNEMOSYNE_DB_ROLE` | _(unset)_ | PostgreSQL least-privilege role (`SET ROLE`); no-op on SQLite |
| `MNEMOSYNE_VECTOR_DIM` | `768` | embedding dimensionality (nomic-embed-text) |
| `PORT` / `HOST` | `8201` / `0.0.0.0` | MCP server bind (when run as a service) |

## Capabilities

A star declares what it needs and fails clear when the backend can't provide it:

```python
from mnemosyne_core import Capability, require
require([Capability.VECTOR_SEARCH])   # pgvector on PG, sqlite-vec on SQLite
```

`vector_search`, `fulltext_search`, `json_query` map across both backends;
`role_enforcement` is PostgreSQL-only.

## Develop

```bash
uv sync --extra dev
uv run ruff check src tests
uv run mypy src tests
uv run pyright
uv run pytest

# FR-1 acceptance: models vs the live store (needs a reachable DATABASE_URL)
DATABASE_URL=postgresql://... uv run python -m mnemosyne_core.schema_diff

# A3.2 import-guard (run in a star's CI)
uv run python -m mnemosyne_core.import_guard src
```

## Consume as a pinned dependency

```bash
uv add "mnemosyne-core @ git+https://github.com/robfischer1/mnemosyne-core@v0.1.0"
```

See [`docs/core-tag-cadence.md`](docs/core-tag-cadence.md) for the branch-during-Build
→ `@tag`-at-Harden policy.

## Container

```bash
docker build -t mnemosyne-core .
docker run --rm -e DATABASE_URL=postgresql://... mnemosyne-core
```
