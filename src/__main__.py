"""Entry point for the finalized project: ``poetry run python src``.

Running a directory makes Python execute ``__main__.py`` inside it.  This shim just
hands off to :func:`main.main`, which drives the whole pipeline of
docs/cluster_map_and_recursive_search.md (index -> map -> search -> draw -> export).

The ``sys.path`` bootstrap below keeps flat imports (``import main``,
``from cluster_map import ...``) resolvable whether the project is run as
``python src``, ``python src/main.py`` or ``python -m src``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from main import main

if __name__ == "__main__":
    raise SystemExit(main())