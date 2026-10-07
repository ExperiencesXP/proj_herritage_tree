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
    4. draw each cluster with the layered passes (section 6) and export Mermaid
       ``flowchart TB`` and Graphviz fragments.

    The three map implementations must agree and identity (3) must hold, so running
    this entry point doubles as a smoke test of the document's verification plan.
    """
    from cluster_map import (
        build_cluster_map_dfs,
        build_cluster_map_pairs,
        build_cluster_map_unionfind,
    )
    from draw import layout_cluster_map, to_dot, to_mermaid
    from graph_model import build_csr, build_family_graph, parent_edges, reach_csr
    from search import (
        ancestors,
        ancestors_iterative,
        descendants,
        explore_iterative,
        find_with_early_exit,
        neighbours_of,
    )

    people = build_demo_population()
    graph = build_family_graph(people, include_ancestors=True)  # section 1.2
    pairs = list(parent_edges(graph))
    neighbours = neighbours_of(graph)  # undirected shadow, orientation-insensitive

    print("Heritage-tree cluster map (docs/cluster_map_and_recursive_search.md)")
    print(f"population  n = {graph.n}, parent edges m = {graph.m}  (I1: m <= 2n)")

    # --- sections 2.3-2.4: three map implementations must coincide -------------
    cmap = build_cluster_map_dfs(graph)
    uf_map = build_cluster_map_unionfind(graph)
    pairs_map = build_cluster_map_pairs(graph.persons, pairs)
    assert cmap.k == uf_map.k == pairs_map.k, "map implementations disagree on k"
    for person in people:
        assert (
            cmap.members_of(person)
            == uf_map.members_of(person)
            == pairs_map.members_of(person)
        ), f"map implementations disagree on the cluster of {person.name}"

    # --- identity (3), equation of Theorem 3.3: k = n - s -----------------------
    s = spanning_forest_size(pairs, people)
    assert cmap.k == graph.n - s, f"identity (3) violated: {cmap.k} != {graph.n} - {s}"
    print(f"clusters    k = {cmap.k}  (identity 3: k = n - s with s = {s})")
    for cluster in sorted(cmap.clusters, key=lambda c: (len(c.members), c.id)):
        names = ", ".join(sorted(p.name for p in cluster.members))
        print(f"  C{cluster.id}: {len(cluster)} persons - {names}")

    # --- searches (sections 2.2 / 2.5 / O7) ------------------------------------
    kid = next(p for p in people if p.name == "kid")
    members = explore_iterative(kid, neighbours=neighbours)  # production path (O5)
    assert members == set(cmap.members_of(kid)), "cluster != closure of Phi_kid"
    print(
        "cluster of kid (explore_iterative over G-bar): "
        + ", ".join(sorted(p.name for p in members))
    )

    # CSR cross-check (O6): array scans reach the same vertices as the pointer walk
    csr = build_csr(graph, members=sorted(members, key=lambda p: p.name))
    assert set(reach_csr(csr, 0)) == members, "CSR traversal disagrees with the cluster"

    closure = ancestors_iterative(kid)  # memoised Anc (section 2.5, production form O5)
    assert closure == ancestors(kid), "iterative Anc disagrees with the reference recursion"
    print(
        f"ancestors of kid: {len(closure)} - "
        + ", ".join(sorted(p.name for p in closure))
        + "  (pedigree collapse reduces the binary-lattice bound)"
    )
    down = descendants(graph, next(p for p in people if p.name == "ada"))
    print(
        f"descendants of ada: {len(down)} - " + ", ".join(sorted(p.name for p in down))
    )

    goal = find_with_early_exit(kid, lambda p: p.name == "ada", neighbours=neighbours)
    assert goal is not None and goal.name == "ada", "early-exit search failed"
    print(f"early-exit search found: {goal.name} (O7)")

    # --- section 6: layered drawing + source-free exports ----------------------
    layouts = layout_cluster_map(cmap, parallel=True)  # O9/O12
    print("\nlayered layout (ranks and crossing counts):")
    for layout in layouts:
        ranks = sorted(set(layout.ranks.values()))
        print(f"  C{layout.cluster_id}: ranks {ranks}, crossings = {layout.crossings}")
        for person, rank in layout.ranks.items():
            assert layout.y[person] == rank * layout.delta, "coordinate pass (3) broken"
            assert layout.x[person] >= 0.0

    showcase = max(cmap.clusters, key=len)  # the richest cluster as readable source
    print("\nMermaid fragment (flowchart TB, parent -> child):")
    print(to_mermaid(showcase))
    print("\nGraphviz fragment (rankdir=TB):")
    print(to_dot(showcase))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
