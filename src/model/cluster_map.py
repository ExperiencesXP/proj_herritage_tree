from __future__ import annotations

from collections.abc import Hashable, Iterable
from dataclasses import dataclass
from typing import Any

from model.graph_model import FamilyGraph, undirected_edges
from model.search import explore_iterative


@dataclass(frozen=True, slots=True)
class Cluster:

    id: int
    members: frozenset[Any]
    edges: tuple[tuple[Any, Any], ...]

    def __len__(self) -> int:
        return len(self.members)


@dataclass(frozen=True, slots=True)
class ClusterMap:

    owner: dict[Any, int]
    clusters: tuple[Cluster, ...]

    @property
    def k(self) -> int:
        return len(self.clusters)

    def cluster_of(self, person: Any) -> Cluster:
        return self.clusters[self.owner[person] - 1]

    def members_of(self, person: Any) -> frozenset[Any]:
        return self.cluster_of(person).members


class UnionFind:

    __slots__ = ("parent", "rank", "successful_unions")

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n
        self.successful_unions = 0

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        self.successful_unions += 1
        return True


def _assemble(
    owner: dict[Any, int],
    buckets: dict[int, list[Any]],
    edges: Iterable[tuple[Any, Any]],
) -> ClusterMap:
    edge_list = tuple(edges)
    inside: dict[int, list[tuple[Any, Any]]] = {cid: [] for cid in buckets}
    for u, v in edge_list:
        if owner[u] == owner[v]:
            inside[owner[u]].append((u, v))
    clusters = tuple(
        Cluster(id=cid, members=frozenset(members), edges=tuple(inside[cid]))
        for cid, members in sorted(buckets.items())
    )
    return ClusterMap(owner=dict(owner), clusters=clusters)


def _assign_ids(
    roots: dict[Any, Any], ordered: tuple[Any, ...]
) -> tuple[dict[Any, int], dict[int, list[Any]]]:
    owner: dict[Any, int] = {}
    buckets: dict[int, list[Any]] = {}
    next_id = 1
    root_id: dict[Any, int] = {}
    for p in ordered:
        root = roots[p]
        cid = root_id.get(root)
        if cid is None:
            cid = root_id[root] = next_id
            next_id += 1
            buckets[cid] = []
        owner[p] = cid
        buckets[cid].append(p)
    return owner, buckets


def build_cluster_map_dfs(graph: FamilyGraph) -> ClusterMap:
    owner: dict[Any, int] = {}
    buckets: dict[int, list[Any]] = {}
    next_id = 1
    for seed in graph.persons:
        if seed in owner:
            continue
        members = explore_iterative(seed, neighbours=graph.neighbours)
        for p in members:
            owner[p] = next_id
        buckets[next_id] = []
        next_id += 1
    for p in graph.persons:
        buckets[owner[p]].append(p)
    return _assemble(owner, buckets, undirected_edges(graph))


def build_cluster_map_unionfind(
    graph: FamilyGraph, extra_pairs: Iterable[tuple[Any, Any]] = ()
) -> ClusterMap:
    idx = graph.id_of
    uf = UnionFind(graph.n)
    edges = list(undirected_edges(graph))
    for u, v in edges:
        uf.union(idx[u], idx[v])
    for u, v in extra_pairs:
        try:
            a, b = idx[u], idx[v]
        except KeyError as err:
            raise ValueError(f"edge endpoint not in graph: {err.args[0]!r}") from err
        uf.union(a, b)
        edges.append((u, v))
    owner, buckets = _assign_ids(
        {p: uf.find(idx[p]) for p in graph.persons}, graph.persons
    )
    return _assemble(owner, buckets, edges)


def build_cluster_map_pairs(
    nodes: Iterable[Hashable], pairs: Iterable[tuple[Hashable, Hashable]]
) -> ClusterMap:
    ordered = tuple(nodes)
    idx = {node: i for i, node in enumerate(ordered)}
    uf = UnionFind(len(ordered))
    edge_first: dict[tuple[Hashable, Hashable], tuple[Hashable, Hashable]] = {}
    for u, v in pairs:
        try:
            a, b = idx[u], idx[v]
        except KeyError as err:
            raise ValueError(f"edge endpoint not in nodes: {err.args[0]!r}") from err
        uf.union(a, b)
        edge_first.setdefault((u, v) if a < b else (v, u), (u, v))
    owner, buckets = _assign_ids(
        {node: uf.find(idx[node]) for node in ordered}, ordered
    )
    return _assemble(owner, buckets, edge_first.values())


def build_cluster_map(graph: FamilyGraph) -> ClusterMap:
    return build_cluster_map_dfs(graph)
