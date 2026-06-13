# Model Authoring Guide — one namespace → `models/<ns>.py`

You are generating SQLAlchemy 2.0 declarative ORM models for **one** PostgreSQL
schema ("namespace") of an existing, **live** data store, for the greenfield
`mnemosyne_core` package. Your output is the **typed schema contract** for that
namespace — a *faithful, zero-drift* mirror of the live PostgreSQL schema. A
schema-diff check will compare your models to the live store; drift is a failure.

Repo root: `C:/Users/robfi/Forge/Outputs/mnemosyne_core`.

## Step 1 — Introspect the live store (READ-ONLY)

Use the MCP tool `mcp__personal-history-db__run_sql` (read-only `SELECT` only).
Substitute your schema name for `<NS>`:

**A. Columns (the spine):**
```sql
SELECT table_name, ordinal_position, column_name, data_type, udt_name,
       is_nullable, column_default
FROM information_schema.columns WHERE table_schema = '<NS>'
ORDER BY table_name, ordinal_position
```
The default row cap is 500. If truncated, page: add `AND table_name > '<last_seen>'`
and repeat until you have **every** table. Count `DISTINCT table_name` and confirm
it matches the expected table count before writing.

**B. Primary keys:**
```sql
SELECT tc.table_name, kcu.column_name, kcu.ordinal_position
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
WHERE tc.table_schema = '<NS>' AND tc.constraint_type = 'PRIMARY KEY'
ORDER BY tc.table_name, kcu.ordinal_position
```

**C. Vector dimensions + array element types** (only if your namespace has
`vector` or array columns — `udt_name` starts with `_` for arrays, or is `vector`):
```sql
SELECT c.relname AS table_name, a.attname AS column_name,
       format_type(a.atttypid, a.atttypmod) AS full_type
FROM pg_attribute a
JOIN pg_class c ON a.attrelid = c.oid
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = '<NS>' AND a.attnum > 0 AND NOT a.attisdropped
  AND (format_type(a.atttypid, a.atttypmod) LIKE 'vector%'
       OR format_type(a.atttypid, a.atttypmod) LIKE '%[]')
ORDER BY c.relname, a.attnum
```
`full_type` gives e.g. `vector(768)`, `bigint[]`, `integer[]`.

## Step 2 — Type map (use EXACTLY these)

| PG `data_type` (`udt_name`) | SQLAlchemy column type | `Mapped[...]` py-type |
| :-- | :-- | :-- |
| `text` / `character varying` / `character` | `Text` | `str` |
| `bigint` (`int8`) | `BigInteger` | `int` |
| `integer` (`int4`) | `Integer` | `int` |
| `smallint` (`int2`) | `SmallInteger` | `int` |
| `boolean` (`bool`) | `Boolean` | `bool` |
| `double precision` (`float8`) | `Float` | `float` |
| `real` (`float4`) | `Float` | `float` |
| `numeric` | `Numeric` | `Any` |
| `timestamp with time zone` (`timestamptz`) | `DateTime(timezone=True)` | `datetime` |
| `jsonb` | `JSONB` | `Any` |
| `uuid` | `UUIDType` | `Any` |
| `ARRAY` of `_int4` | `IntArray` | `Any` |
| `ARRAY` of `_int8` | `BigIntArray` | `Any` |
| `USER-DEFINED` `vector` | `Vector(<dim>)` (dim from query C; default `768`) | `Any` |
| `tsvector` | `TSVector` | `Any` |

Any PG type **not** in this map → do **not** guess; model it as `Text`/`Any`
only if trivial, otherwise note it in your summary as unmapped.

## Step 3 — Write `src/mnemosyne_core/models/<ns>.py`

Imports (include only what you use):
```python
from __future__ import annotations

from datetime import datetime          # if any timestamptz
from decimal import Decimal            # only if you choose Decimal for numeric
from typing import Any                 # if any jsonb/uuid/vector/array/numeric

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, Integer, Numeric, SmallInteger, Text, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from mnemosyne_core.base import Base
from mnemosyne_core.types import JSONB, BigIntArray, IntArray, TSVector, UUIDType, Vector
```

One declarative class per table, **every** table, **every** column in ordinal order:
```python
class AiSessions(Base):
    """ai_sessions in the ai_memory namespace."""

    __tablename__ = "ai_sessions"
    __table_args__ = {"schema": "ai_memory"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[Any | None] = mapped_column(JSONB)
```

Rules:
- **Nullable** (`is_nullable = 'YES'`) → `Mapped[T | None]`, no `nullable=False`.
- **NOT NULL, non-PK** → `Mapped[T]` + `nullable=False`.
- **Primary key** → `primary_key=True` (omit `nullable`). Composite PK → mark each
  PK column `primary_key=True` in order.
- `server_default`: if `column_default` is a simple literal / `now()` / `nextval(...)`,
  add `server_default=text("<default>")`. If unsure, **omit** it (defaults don't
  affect the column-shape diff) and note it.
- **Class name** = CamelCase of the table name (`session_turns` → `SessionTurns`).
  Keep `__tablename__` exact. On a name clash, suffix sensibly; never change the
  table name.
- Module docstring + a one-line docstring per class (ruff `D` is enforced).

## Step 4 — Validate before returning

```bash
cd "C:/Users/robfi/Forge/Outputs/mnemosyne_core"
uv run ruff check src/mnemosyne_core/models/<ns>.py     # must be clean
uv run python -c "import mnemosyne_core.models.<ns>"     # must import cleanly
```
Fix anything that fails. (`<ns>` keeps any leading underscore, e.g. `_infra`.)

## Step 5 — Return a concise summary (do NOT paste the file)

- `namespace`, `file`
- `tables_modeled`: N (must equal the live `DISTINCT table_name` count — state both)
- `columns_modeled`: N
- `pgvector/array/uuid/tsvector` columns handled (with dims)
- any unmapped types, ambiguities, or tables you could not fully model
- `ruff`: clean? `import`: ok?
