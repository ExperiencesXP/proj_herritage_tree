# Unifying `src/main.py` and `src/__main__.py`

Status: **applied** (this document was written after a bare `main.py -> __main__.py` rename
proved unsafe; sections 1-2 record why, section 3 is the refactor that was then executed).

## 1. Verdict

They are **only partly redundant**. `src/__main__.py` is a 24-line launcher whose entire job is

```python
from main import main
raise SystemExit(main())
```

Everything else in `src/main.py` (232 lines) is *not* entry-point code: it is the domain model
(`Pronouns`, `Person`) plus the demo population and the pipeline (`main()`).

So there is one redundant artefact — the shim — but we cannot just `git mv src/main.py
src/__main__.py`, because `main.py` is also used as a **library module**, and `__main__` is a
reserved module name that cannot be imported reliably. The rename becomes possible after the
split described in section 3.

## 2. Why a bare rename breaks

Current references to the `main` module:

| Location | Reference | Role |
|---|---|---|
| `src/graph_model.py:21` | `from main import Person` | the vertex type `V` |
| `src/tests/conftest.py:23` | `import main` → `main.Person` | `person_cls` fixture |
| `src/__main__.py:21` | `from main import main` | the entry point |
| `docs/cluster_map_and_recursive_search.md` §1.4, §7 | `src/main.py` | doc references |
| `README.md` | `poetry run python src` | invocation (unaffected) |

Blocking reasons:

1. **`main` is imported as a library, not only run as a script.** After a rename the name `main`
   no longer exists, so `graph_model` raises `ModuleNotFoundError` and test collection dies in
   `conftest.py`.
2. **`__main__` cannot be re-pointed.** `import __main__` does not load `src/__main__.py`; it
   returns whatever module the *runner* already registered as `__main__`. Measured under the
   project venv:

   ```
   --- run as pytest ---
   __main__ is: .venv\Lib\site-packages\pytest\__main__.py
   __main__ has VALUE: False
   from __main__ import VALUE FAILED: ImportError
   ```

   So `from __main__ import Person` in `graph_model.py` would work only when the program happens to
   be started from this directory, and would fail (or import someone else's `Person`) under
   `pytest`, an IDE run, or any embedding host.
3. **Two runners, two module identities.** `python src` registers the file as top-level
   `__main__`, `python -m src` registers it as `src.__main__`. Domain code living in
   `__main__.py` is therefore only reachable through the ambient `__main__`, and module-level
   state such as `Pronouns.PRESETS` could be initialised twice under two different identities.
4. **A documented invocation disappears**: `python src/main.py`, advertised in the
   `__main__.py` docstring and in this design doc's scope.

Conclusion: `main.py` is doing two jobs (library + entry point). The rename is possible once the
library job moves to a module with a normal, importable name.

## 3. Refactor that makes the rename possible

### Step 1 — new `src/person.py`: the domain model

Move `Pronouns`, `Pronouns.PRESETS` and `Person` verbatim out of `main.py` (the data types of
§1.1/§1.4 of `docs/cluster_map_and_recursive_search.md`). They have no project-internal imports,
so this move is mechanical.

```python
"""Family data model: `Person` / `Pronouns` (docs/cluster_map_and_recursive_search.md §1).

``V`` in the design doc is the population of :class:`Person` objects; ``Person.mom`` /
``Person.dad`` are the two parental edges (invariant I1: deg⁻(v) ≤ 2).  Presentation helpers
(``__str__``, ``pronoun``) play no role in the algorithms and are kept here so the graph modules
stay presentation-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

# ... Pronouns, Pronouns.PRESETS.update(...), Person — unchanged from src/main.py ...
```

### Step 2 — `src/__main__.py` absorbs the entry point, `src/main.py` is deleted

Keep `build_demo_population`, `spanning_forest_size` and `main()` together with the entry
(`main()` imports its pipeline lazily already, so no import order problem). The `sys.path`
bootstrap stays — it is what makes `python src`, `python src/__main__.py` and `python -m src`
all work with flat imports.

```python
"""Entry point of the project: ``poetry run python src``.

Running a directory (or ``python -m src``) makes Python execute ``__main__.py`` inside it, which
drives the whole pipeline of docs/cluster_map_and_recursive_search.md
(index -> map -> search -> draw -> export).

The ``sys.path`` bootstrap below keeps flat imports (``from person import Person``,
``from cluster_map import ...``) resolvable in every supported launch mode:
``python src``, ``python src/__main__.py``, ``python -m src``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from person import Person  # re-exported: build_demo_population's return type


def build_demo_population() -> tuple[Person, ...]:
    ...  # unchanged from src/main.py


def spanning_forest_size(pairs, people) -> int:
    ...  # unchanged from src/main.py


def main() -> int:
    ...  # unchanged from src/main.py (lazy imports of cluster_map/draw/graph_model/search)


if __name__ == "__main__":
    raise SystemExit(main())
```

Then `git rm src/main.py` (and the stale `src/__pycache__/main.*.pyc`). The function is still
called `main()`, so `raise SystemExit(main())` reads exactly as before.

### Step 3 — fix the two importers

```python
# src/graph_model.py
-from main import Person
+from person import Person
```

```python
# src/tests/conftest.py
 def person_cls():
     """The ``Person`` type, imported lazily so collection never fails on missing deps."""
-    import main
+    import person

-    return main.Person
+    return person.Person
```

`conftest.py`'s module docstring lists ``main`` among the sibling modules — change that to
``person``. No test body references `main` directly.

### Step 4 — update the doc references

`docs/cluster_map_and_recursive_search.md`:

* §Scope line 3: `src/main.py` → `src/person.py`;
* §1.4 heading "(design sketch, compatible with `src/main.py`)" → `src/person.py`;
* §7 table header "`src/main.py` element" → "`src/person.py` element".

`README.md` needs no change: it already runs `poetry run python src`.

## 4. Resulting layout and invocation matrix

```
src/
  __main__.py     entry point + pipeline (former main.main)
  person.py       Person, Pronouns            (former main.Person/Pronouns)
  graph_model.py  search.py  cluster_map.py  draw.py
  tests/
```

| Command | Before | After |
|---|---|---|
| `poetry run python src` (README) | works | works |
| `python -m src` | works | works |
| `python src/__main__.py` | works | works |
| `python src/main.py` | works | **removed** (nothing in the repo uses it) |
| `poetry run pytest` (11 tests) | works | works |

## 5. Verification checklist

```bash
poetry run pytest -q          # 11 passed
poetry run python src         # full pipeline output, exit 0
poetry run python -m src      # identical output
grep -rn "import main\|from main" src docs   # must be empty
```

## 6. Optional back-compat

Not needed here: `package-mode = false`, the project is not published, and no external caller
imports `main`. If one ever appears, keep a one-line `src/main.py` shim with a
`DeprecationWarning` that re-exports `person.Person` and `__main__.main` — but note it can only
re-export, never the reverse: `__main__` must not be imported from library code (section 2.2).
