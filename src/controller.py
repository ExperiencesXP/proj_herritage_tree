"""**Controller** of the MVC architecture (`Projekt.docx`: "I skal anvende MVC-arkitektur").

The controller is the only layer that touches both sides of the program:

* it holds the session state — the indexed :class:`graph_model.FamilyGraph` (Model),
  the :class:`cluster_map.ClusterMap` (Model) and the :class:`draw.Layout` values;
* it exposes high-level commands (map, search, layout, export, render) that the entry
  point (`__main__.py`) calls;
* it hands **finished values** to the Views (`draw.py` text exports, `view.py`
  matplotlib figures) — the views never run algorithms themselves.

This is the "C" in MVC and also the OOP showcase of the program: encapsulation
(the graph/map/layouts are private session state behind methods), single
responsibility (each command does one thing), and delegation (rendering is
delegated to :mod:`view`, layout to :mod:`draw`, searching to :mod:`search`).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from cluster_map import (
    ClusterMap,
    build_cluster_map,
    build_cluster_map_dfs,
    build_cluster_map_pairs,
    build_cluster_map_unionfind,
)
from draw import Layout, layout_cluster_map, to_dot, to_mermaid
from graph_model import FamilyGraph, build_csr, build_family_graph, parent_edges, reach_csr
from person import Person
from search import (
    ancestors_iterative,
    descendants,
    explore_iterative,
    find_with_early_exit,
    neighbours_of,
)
from view import render_cluster_map

__all__ = ["FamilyController"]


class FamilyController:
    """Session facade over the family-graph model with view commands (MVC controller)."""

    def __init__(
        self, persons: Iterable[Person], *, include_ancestors: bool = True
    ) -> None:
        self.graph: FamilyGraph = build_family_graph(
            persons, include_ancestors=include_ancestors
        )
        self.cluster_map: ClusterMap | None = None
        self.layouts: tuple[Layout, ...] = ()

    # ------------------------------------------------------------------ model commands

    def person(self, name: str) -> Person:
        """Look a person up by natural key (``Person.name``, §1.4)."""
        for p in self.graph.persons:
            if p.name == name:
                return p
        raise ValueError(f"no person named {name!r} in the population")

    def build_map(self) -> ClusterMap:
        """Build the cluster map with the recommended default construction (§2.3)."""
        self.cluster_map = build_cluster_map(self.graph)
        return self.cluster_map

    def verify_consistency(self) -> dict[str, Any]:
        """Run the verification plan of §8.1 on the indexed population.

        All three map constructions (DFS, Union-Find, bare pairs) must agree, the
        boxed identity (3) ``k = n - s`` must hold against an independent union-find
        count, and the CSR array scan (O6) must reach the same cluster as the pointer
        walk.  Raises ``AssertionError`` on disagreement; returns the measured facts.
        """
        pairs = list(parent_edges(self.graph))
        people = self.graph.persons
        dfs_map = build_cluster_map_dfs(self.graph)
        uf_map = build_cluster_map_unionfind(self.graph)
        pairs_map = build_cluster_map_pairs(people, pairs)
        assert dfs_map.k == uf_map.k == pairs_map.k, "map implementations disagree on k"
        for person in people:
            assert (
                dfs_map.members_of(person)
                == uf_map.members_of(person)
                == pairs_map.members_of(person)
            ), f"map implementations disagree on the cluster of {person.name}"

        # identity (3) counted independently of the cluster code (not circular)
        parent = {p: p for p in people}

        def find(x: Any) -> Any:
            while parent[x] is not x:
                parent[x] = parent[parent[x]]  # path halving (O3)
                x = parent[x]
            return x

        s = 0
        for a, b in pairs:
            ra, rb = find(a), find(b)
            if ra is not rb:
                parent[rb] = ra
                s += 1
        assert dfs_map.k == self.graph.n - s, f"identity (3) violated: {dfs_map.k} != n - {s}"

        # CSR cross-check (O6) against the pointer walk over the largest cluster
        biggest = max(dfs_map.clusters, key=len)
        members = frozenset(biggest.members)
        seed = sorted(members, key=lambda p: p.name)[0]
        walked = explore_iterative(seed, neighbours=neighbours_of(self.graph))
        csr = build_csr(self.graph, members=sorted(members, key=lambda p: p.name))
        assert walked == members, "cluster != closure of the seed in G-bar"
        assert set(reach_csr(csr, 0)) == members, "CSR traversal disagrees with the cluster"

        self.cluster_map = dfs_map
        return {"n": self.graph.n, "m": self.graph.m, "k": dfs_map.k, "s": s}

    def cluster_members(self, name: str) -> frozenset[Person]:
        """All members of the cluster containing ``name`` (recursive search, §2.2)."""
        if self.cluster_map is None:
            self.build_map()
        assert self.cluster_map is not None
        return self.cluster_map.members_of(self.person(name))

    def ancestors_of(self, name: str) -> frozenset[Person]:
        """Memoised ancestral closure of ``name`` (§2.5, production form O5)."""
        return ancestors_iterative(self.person(name))

    def descendants_of(self, name: str) -> frozenset[Person]:
        """All descendants of ``name`` via the reverse index (§2.2)."""
        return descendants(self.graph, self.person(name))

    def find_person(self, name: str, goal: Callable[[Person], bool]) -> Person | None:
        """Goal-directed search from ``name`` with early exit (O7/O11)."""
        return find_with_early_exit(
            self.person(name), goal, neighbours=neighbours_of(self.graph)
        )

    def layout(self, *, parallel: bool = True) -> tuple[Layout, ...]:
        """Layered Sugiyama layout of every cluster (§6; O9/O12)."""
        if self.cluster_map is None:
            self.build_map()
        assert self.cluster_map is not None
        self.layouts = layout_cluster_map(self.cluster_map, parallel=parallel)
        return self.layouts

    # ------------------------------------------------------------------ view commands

    def mermaid_of(self, name: str) -> str:
        """Mermaid ``flowchart TB`` fragment of the cluster containing ``name`` (View)."""
        if self.cluster_map is None:
            self.build_map()
        assert self.cluster_map is not None
        return to_mermaid(self.cluster_map.cluster_of(self.person(name)))

    def dot_of(self, name: str) -> str:
        """Graphviz fragment of the cluster containing ``name`` (View)."""
        if self.cluster_map is None:
            self.build_map()
        assert self.cluster_map is not None
        return to_dot(self.cluster_map.cluster_of(self.person(name)))

    def render(
        self,
        out_dir: str | Path = "out",
        *,
        show: bool = False,
        highlight: Iterable[Any] = (),
        fmt: str = "png",
    ) -> tuple[Path, ...]:
        """Render every cluster map with matplotlib into ``out_dir`` (View, `Projekt.docx`)."""
        if self.cluster_map is None:
            self.build_map()
        if not self.layouts:
            self.layout()
        assert self.cluster_map is not None
        return render_cluster_map(
            self.cluster_map,
            self.layouts,
            out_dir=out_dir,
            fmt=fmt,
            show=show,
            highlight=highlight,
        )
