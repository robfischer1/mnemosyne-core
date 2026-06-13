# Core-tag cadence policy (A3.3)

How stars depend on the `mnemosyne` core over the build lifecycle. The core is an
**internal git-pinned dependency** (not PyPI-published) -- stars add it with
`uv add git+https://github.com/robfischer1/mnemosyne-core@<ref>`.

## The rule: branch during Build, `@tag` at Harden

| Phase | What the star pins | Why |
| :-- | :-- | :-- |
| **Build** | the core's **moving branch** (`@main`) | the contract is still settling; a star tracks core changes without a tag churn per edit |
| **Harden** | a **frozen `@tag`** (e.g. `@v0.3.0`) | the contract is frozen; the star's lockfile pins an immutable ref so its build is reproducible |
| **Live** | the same frozen `@tag` | production builds never float |

A star **must** move from `@main` to a `@tag` before it is declared Harden-ready.
CI in a star repo checks the lockfile pins a tag (not a branch) for any Harden/Live
build.

## Tagging the core

The core is tagged on every contract-affecting change once it has consumers:

- **Semantic version** `vMAJOR.MINOR.PATCH` on the schema contract:
  - **MAJOR** -- a breaking schema change (a column/table removed or retyped in a
    way that drops data access).
  - **MINOR** -- additive (new tables/columns/namespaces; new public API).
  - **PATCH** -- non-contract fixes (docs, internals, packaging).
- A tag is cut only when `mnemosyne-schema-diff` reports **zero drift** against the
  live store on the tagged commit (the FR-1 gate).
- The tag message records the introspection date and the live store's table/column
  counts at tag time (the drift baseline).

## Consuming the core (star side)

```bash
# Build phase -- track the moving branch
uv add "mnemosyne-core @ git+https://github.com/robfischer1/mnemosyne-core@main"

# Harden phase -- freeze to a tag
uv add "mnemosyne-core @ git+https://github.com/robfischer1/mnemosyne-core@v0.3.0"
```

A star imports only the public surface and runs the import-guard in CI so it never
couples to core internals:

```bash
uv run python -m mnemosyne_core.import_guard src
```
