"""Entry point of the project: ``poetry run python src``.

Running a directory (or ``python -m src``) makes Python execute ``__main__.py`` inside it, which
drives the whole pipeline of docs/cluster_map_and_recursive_search.md
(index -> map -> search -> draw -> export -> render).

MVC (Projekt.docx): this module is the program's controller *entry* — it builds the demo
population (data) and drives :class:`controller.FamilyController` (Controller, which owns
the Model); finished values are handed to the Views (:mod:`draw` text exports,
:mod:`view` matplotlib figures).

The ``sys.path`` bootstrap below keeps flat imports (``from person import Person``,
``from cluster_map import ...``) resolvable in every supported launch mode:
``python src``, ``python src/__main__.py``, ``python -m src``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from person import Person


def build_demo_population() -> tuple[Person, ...]:
    """The worked family of docs/cluster_map_and_recursive_search.md (section 1.3).

    Two clusters: a pedigree-collapse family (invariant I3: ``ada`` is both mia's dad
    and dan's dad, so |Anc(kid)| < 2^{g+1} - 1) and one isolated person - edges never
    cross clusters.
    """
    ada = Person("ada")
    mia = Person("mia", mom=ada)
    dan = Person("dan", dad=ada)
    kid = Person("kid", mom=mia, dad=dan)
    solo = Person("solo")
    return ada, mia, dan, kid, solo


def spanning_forest_size(
    pairs: Iterable[tuple[Any, Any]], people: Iterable[Any]
) -> int:
    """Edges of a spanning forest of the undirected shadow G-bar, counted directly.

    An independent union-find pass (path halving) accepts exactly s = |V| - k pairs,
    which is equation (3) rearranged; keeping the count out of the cluster code makes
    the identity check meaningful rather than circular.
    """
    parent = {p: p for p in people}

    def find(x: Any) -> Any:
        while parent[x] is not x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    accepted = 0
    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra is not rb:
            parent[rb] = ra
            accepted += 1
    return accepted


def main() -> int:
    """Run the finalized cluster-map pipeline over the section 1.3 family.

    Exercises every stage of the design doc end to end and prints its outputs:

    1. index the population into a ``FamilyGraph`` (section 1.2),
    2. map the clusters by DFS, Union-Find and the pairs form (sections 2.3-2.4),
    3. search - membership, memoised ancestor closure, descendants, goal exit,
    4. draw each cluster with the layered passes (section 6), export Mermaid
       ``flowchart TB`` and Graphviz fragments, and render the matplotlib figures
       required by Projekt.docx (``out/cluster_<id>.png``).

    The three map implementations must agree, identity (3) must hold against two
    independent forest counts, and the CSR scan must match the pointer walk, so
    running this entry point doubles as a smoke test of the document's
    verification plan.
    """
    from controller import FamilyController
    from graph_model import parent_edges
    from search import ancestors

    people = build_demo_population()
    app = FamilyController(people)  # section 1.2 indexing happens here

    print("Heritage-tree cluster map (docs/cluster_map_and_recursive_search.md)")
    facts = app.verify_consistency()  # sections 2.3-2.4 + identity (3) + CSR (O6)
    cmap = app.cluster_map
    assert cmap is not None  # set by verify_consistency
    pairs = list(parent_edges(app.graph))
    s = spanning_forest_size(pairs, people)
    assert s == facts["s"], "independent forest counts disagree"
    print(f"population  n = {facts['n']}, parent edges m = {facts['m']}  (I1: m <= 2n)")
    print(f"clusters    k = {facts['k']}  (identity 3: k = n - s with s = {s})")
    for cluster in sorted(cmap.clusters, key=lambda c: (len(c.members), c.id)):
        names = ", ".join(sorted(p.name for p in cluster.members))
        print(f"  C{cluster.id}: {len(cluster)} persons - {names}")

    # --- searches (sections 2.2 / 2.5 / O7) ------------------------------------
    kid = app.person("kid")
    members = app.cluster_members("kid")  # production path (O5)
    print(
        "cluster of kid (explore_iterative over G-bar): "
        + ", ".join(sorted(p.name for p in members))
    )
    closure = app.ancestors_of("kid")  # memoised Anc (section 2.5, production form O5)
    assert closure == ancestors(kid), "iterative Anc disagrees with the reference recursion"
    print(
        f"ancestors of kid: {len(closure)} - "
        + ", ".join(sorted(p.name for p in closure))
        + "  (pedigree collapse reduces the binary-lattice bound)"
    )
    down = app.descendants_of("ada")
    print(
        f"descendants of ada: {len(down)} - " + ", ".join(sorted(p.name for p in down))
    )
    goal = app.find_person("kid", lambda p: p.name == "ada")
    assert goal is not None and goal.name == "ada", "early-exit search failed"
    print(f"early-exit search found: {goal.name} (O7)")

    # --- project requirement 7.10: har to personer mindst en fælles ane? --------
    shared = app.find_common_ancestor("mia", "dan")
    print("common ancestors of mia and dan: " + ", ".join(p.name for p in shared))
    print(f"is_related(mia, dan) = {app.is_related('mia', 'dan')}")
    print(f"is_related(kid, solo) = {app.is_related('kid', 'solo')}")

    # --- section 6: layered drawing + source-free exports ----------------------
    layouts = app.layout()  # O9/O12
    print("\nlayered layout (ranks and crossing counts):")
    for layout in layouts:
        ranks = sorted(set(layout.ranks.values()))
        print(f"  C{layout.cluster_id}: ranks {ranks}, crossings = {layout.crossings}")
        for person, rank in layout.ranks.items():
            assert layout.y[person] == rank * layout.delta, "coordinate pass (3) broken"
            assert layout.x[person] >= 0.0

    print("\nMermaid fragment (flowchart TB, parent -> child):")
    print(app.mermaid_of("kid"))  # the richest cluster as readable source
    print("\nGraphviz fragment (rankdir=TB):")
    print(app.dot_of("kid"))

    written = app.render(out_dir="out", highlight={kid})
    print("\nmatplotlib figures written:")
    for path in written:
        print(f"  {path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
