from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from models.cluster_map import (
    ClusterMap,
    build_cluster_map,
    build_cluster_map_dfs,
    build_cluster_map_pairs,
    build_cluster_map_unionfind,
)
from draw import Layout, layout_cluster_map, to_dot, to_mermaid
from models.graph_model import (
    FamilyGraph,
    build_csr,
    build_family_graph,
    parent_edges,
    reach_csr,
)
from models.person import Person
from models.search import (
    ancestors_iterative,
    descendants,
    explore_iterative,
    find_common_ancestor as _common_ancestors,
    find_with_early_exit,
    is_related as _is_related,
    neighbours_of,
)
from view import render_cluster_map

__all__ = ["FamilyController"]


class FamilyController:

    def __init__(
        self, persons: Iterable[Person], *, include_ancestors: bool = True
    ) -> None:
        self.graph: FamilyGraph = build_family_graph(
            persons, include_ancestors=include_ancestors
        )
        self.cluster_map: ClusterMap | None = None
        self.layouts: tuple[Layout, ...] = ()

    def person(self, name: str) -> Person:
        for p in self.graph.persons:
            if p.name == name:
                return p
        raise ValueError(f"no person named {name!r} in the population")

    def build_map(self) -> ClusterMap:
        self.cluster_map = build_cluster_map(self.graph)
        return self.cluster_map

    def verify_consistency(self) -> dict[str, Any]:
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

        parent = {p: p for p in people}

        def find(x: Any) -> Any:
            while parent[x] is not x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        s = 0
        for a, b in pairs:
            ra, rb = find(a), find(b)
            if ra is not rb:
                parent[rb] = ra
                s += 1
        assert (
            dfs_map.k == self.graph.n - s
        ), f"identity (3) violated: {dfs_map.k} != n - {s}"

        biggest = max(dfs_map.clusters, key=len)
        members = frozenset(biggest.members)
        seed = sorted(members, key=lambda p: p.name)[0]
        walked = explore_iterative(seed, neighbours=neighbours_of(self.graph))
        csr = build_csr(self.graph, members=sorted(members, key=lambda p: p.name))
        assert walked == members, "cluster != closure of the seed in G-bar"
        assert (
            set(reach_csr(csr, 0)) == members
        ), "CSR traversal disagrees with the cluster"

        self.cluster_map = dfs_map
        return {"n": self.graph.n, "m": self.graph.m, "k": dfs_map.k, "s": s}

    def cluster_members(self, name: str) -> frozenset[Person]:
        if self.cluster_map is None:
            self.build_map()
        assert self.cluster_map is not None
        return self.cluster_map.members_of(self.person(name))

    def ancestors_of(self, name: str) -> frozenset[Person]:
        return ancestors_iterative(self.person(name))

    def descendants_of(self, name: str) -> frozenset[Person]:
        return descendants(self.graph, self.person(name))

    def find_person(self, name: str, goal: Callable[[Person], bool]) -> Person | None:
        return find_with_early_exit(
            self.person(name), goal, neighbours=neighbours_of(self.graph)
        )

    def find_common_ancestor(self, name1: str, name2: str) -> list[Person]:
        return _common_ancestors(self.person(name1), self.person(name2))

    def is_related(self, name1: str, name2: str) -> bool:
        return _is_related(self.person(name1), self.person(name2))

    def layout(self, *, parallel: bool = True) -> tuple[Layout, ...]:
        if self.cluster_map is None:
            self.build_map()
        assert self.cluster_map is not None
        self.layouts = layout_cluster_map(self.cluster_map, parallel=parallel)
        return self.layouts

    def mermaid_of(self, name: str) -> str:
        if self.cluster_map is None:
            self.build_map()
        assert self.cluster_map is not None
        return to_mermaid(self.cluster_map.cluster_of(self.person(name)))

    def dot_of(self, name: str) -> str:
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
