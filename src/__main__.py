from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from models.person import Person


def build_demo_population() -> tuple[Person, ...]:
    ada = Person("ada")
    mia = Person("mia", mom=ada)
    dan = Person("dan", dad=ada)
    kid = Person("kid", mom=mia, dad=dan)
    solo = Person("solo")
    return ada, mia, dan, kid, solo


def spanning_forest_size(
    pairs: Iterable[tuple[Any, Any]], people: Iterable[Any]
) -> int:
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
    from controller import FamilyController
    from models.graph_model import parent_edges
    from models.search import ancestors

    people = build_demo_population()
    app = FamilyController(people)

    print("Heritage-tree cluster map (docs/cluster_map_and_recursive_search.md)")
    facts = app.verify_consistency()
    cmap = app.cluster_map
    assert cmap is not None
    pairs = list(parent_edges(app.graph))
    s = spanning_forest_size(pairs, people)
    assert s == facts["s"], "independent forest counts disagree"
    print(f"population  n = {facts['n']}, parent edges m = {facts['m']}  (I1: m <= 2n)")
    print(f"clusters    k = {facts['k']}  (identity 3: k = n - s with s = {s})")
    for cluster in sorted(cmap.clusters, key=lambda c: (len(c.members), c.id)):
        names = ", ".join(sorted(p.name for p in cluster.members))
        print(f"  C{cluster.id}: {len(cluster)} persons - {names}")

    kid = app.person("kid")
    members = app.cluster_members("kid")
    print(
        "cluster of kid (explore_iterative over G-bar): "
        + ", ".join(sorted(p.name for p in members))
    )
    closure = app.ancestors_of("kid")
    assert closure == ancestors(
        kid
    ), "iterative Anc disagrees with the reference recursion"
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

    shared = app.find_common_ancestor("mia", "dan")
    print("common ancestors of mia and dan: " + ", ".join(p.name for p in shared))
    print(f"is_related(mia, dan) = {app.is_related('mia', 'dan')}")
    print(f"is_related(kid, solo) = {app.is_related('kid', 'solo')}")

    layouts = app.layout()
    print("\nlayered layout (ranks and crossing counts):")
    for layout in layouts:
        ranks = sorted(set(layout.ranks.values()))
        print(f"  C{layout.cluster_id}: ranks {ranks}, crossings = {layout.crossings}")
        for person, rank in layout.ranks.items():
            assert layout.y[person] == rank * layout.delta, "coordinate pass (3) broken"
            assert layout.x[person] >= 0.0

    print("\nMermaid fragment (flowchart TB, parent -> child):")
    print(app.mermaid_of("kid"))
    print("\nGraphviz fragment (rankdir=TB):")
    print(app.dot_of("kid"))

    written = app.render(out_dir="out", highlight={kid})
    print("\nmatplotlib figures written:")
    for path in written:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
