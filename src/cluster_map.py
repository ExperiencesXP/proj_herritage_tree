"""Cluster map construction — `docs/cluster_map_and_recursive_search.md` §2.3 and §2.4.

A *cluster* is a connected component of the undirected shadow Ē (§1.3): its members are
the least fixed point of the search operator of §2.1, and edges never cross clusters, so
the partition is V = ⨆ᵢ Cᵢ and E = ⨆ᵢ E(Cᵢ).

Two equivalent designs are provided, per §2.3:

* :func:`build_cluster_map_dfs` — run the reference DFS per as-yet-unvisited node; each
  run yields exactly one cluster (Theorem 3.2).  Cost Θ(n + m) = Θ(n).
* :func:`build_cluster_map_unionfind` — process every parent edge as ``union(u, v)``;
  chosen for the incremental/streaming import case because it adds edges in near-constant
  amortised time without rebuilding adjacency lists.  Cluster count is the boxed identity

      k = n − s                                        (3)

  with s the number of *successful* unions (Theorem 3.3: each success merges exactly two
  components), computed here in O(1) *after* the merges, no traversal needed.

:class:`UnionFind` itself is union-by-rank (rank height bound ⌊log₂ n⌋) with
path-halving ``find`` — overall O(m·α(m, n)), practically O(m) since α ≤ 5 for every
physically reachable n (§4.1, Appendix A).
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable
from dataclasses import dataclass
from typing import Any

from graph_model import FamilyGraph, undirected_edges
from search import explore_iterative


@dataclass(frozen=True, slots=True)
class Cluster:
    """One connected component ``C_i`` with its induced edge set ``E(C_i)`` (§1.3)."""

    id: int
    members: frozenset[Any]
    edges: tuple[tuple[Any, Any], ...]

    def __len__(self) -> int:
        return len(self.members)


@dataclass(frozen=True, slots=True)
class ClusterMap:
    """The map ``clusterId: V → {1..k}`` plus the per-cluster person subsets (§1.3)."""

    owner: dict[Any, int]
    clusters: tuple[Cluster, ...]

    @property
    def k(self) -> int:
        """Number of clusters — equals ``n − s`` by identity (3)."""
        return len(self.clusters)

    def cluster_of(self, person: Any) -> Cluster:
        return self.clusters[self.owner[person] - 1]

    def members_of(self, person: Any) -> frozenset[Any]:
        """``|members| = |C_i|`` for the cluster containing ``person`` (§1.4 sketch)."""
        return self.cluster_of(person).members


class UnionFind:
    """Disjoint-set union with union-by-rank and path-halving ``find`` (§2.4, O3)."""

    __slots__ = ("parent", "rank", "successful_unions")

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n
        self.successful_unions = 0

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]  # path halving (O3)
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:  # union by rank: serve the shallower root
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
    """Attach the induced subgraphs ``E(C_i)`` to the clusters found by either design."""
    edge_list = tuple(edges)
    inside: dict[int, list[tuple[Any, Any]]] = {cid: [] for cid in buckets}
    for u, v in edge_list:
        if owner[u] == owner[v]:  # edges never cross clusters (§1.3)
            inside[owner[u]].append((u, v))
    clusters = tuple(
        Cluster(id=cid, members=frozenset(members), edges=tuple(inside[cid]))
        for cid, members in sorted(buckets.items())
    )
    return ClusterMap(owner=dict(owner), clusters=clusters)


def _assign_ids(
    roots: dict[Any, Any], ordered: tuple[Any, ...]
) -> tuple[dict[Any, int], dict[int, list[Any]]]:
    """Map component roots to clusterIds ``1..k`` in first-seen order; O(n) single pass.

    Both call sites key buckets by these ``1..k`` ids so ``ClusterMap.cluster_of``
    (``clusters[cid - 1]``) is well-defined.
    """
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
    """Design (a) of §2.3: one traversal per cluster over Ē (parents ∪ children).

    Total cost is Θ(n + m) = Θ(n): every node is coloured once (O1) and every undirected
    edge is examined at most twice (equation 2), then one linear ``_assign_ids`` pass.
    """
    owner: dict[Any, int] = {}
    buckets: dict[int, list[Any]] = {}
    next_id = 1
    for seed in graph.persons:
        if seed in owner:  # already labelled by an earlier cluster
            continue
        members = explore_iterative(seed, neighbours=graph.neighbours)
        for p in members:
            owner[p] = next_id
        buckets[next_id] = []
        next_id += 1
    for p in graph.persons:  # single O(n) pass, dense-id order preserved
        buckets[owner[p]].append(p)
    return _assemble(owner, buckets, undirected_edges(graph))


def build_cluster_map_unionfind(
    graph: FamilyGraph, extra_pairs: Iterable[tuple[Any, Any]] = ()
) -> ClusterMap:
    """Design (b) of §2.3: Union-Find over every parent edge (plus optional extras).

    ``extra_pairs`` models the streaming case: pairs arriving later merge clusters in
    near-constant amortised time without rebuilding any adjacency list (the design choice
    documented under §2.3(b)).  Afterwards ``k = n − s`` holds with
    ``s = uf.successful_unions`` (identity (3)).
    """
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
        uf.union(a, b)  # union() counts only the successful merges (identity 3)
        edges.append((u, v))  # record the edge even if it merged nothing (in-cluster)
    owner, buckets = _assign_ids(
        {p: uf.find(idx[p]) for p in graph.persons}, graph.persons
    )
    return _assemble(owner, buckets, edges)


def build_cluster_map_pairs(
    nodes: Iterable[Hashable], pairs: Iterable[tuple[Hashable, Hashable]]
) -> ClusterMap:
    """Union-Find construction from bare identifiers and edge pairs (no Person needed).

    Implements the §2.4 pseudocode directly.  Each successful merge increments the
    counter behind identity (3), so ``map.k == len(nodes) - s`` holds after construction
    — the §8.1 property test exercises exactly this.
    """
    ordered = tuple(nodes)
    idx = {node: i for i, node in enumerate(ordered)}
    uf = UnionFind(len(ordered))
    edge_set: set[tuple[Hashable, Hashable]] = set()
    for u, v in pairs:
        try:
            a, b = idx[u], idx[v]
        except KeyError as err:
            raise ValueError(f"edge endpoint not in nodes: {err.args[0]!r}") from err
        uf.union(a, b)
        edge_set.add((u, v) if a < b else (v, u))
    owner, buckets = _assign_ids(
        {node: uf.find(idx[node]) for node in ordered}, ordered
    )
    return _assemble(owner, buckets, edge_set)


def build_cluster_map(graph: FamilyGraph) -> ClusterMap:
    """Recommended default construction: :func:`build_cluster_map_dfs`.

    Without a streaming edge source, clusters are fully known at graph build time, so the
    plain traversal runs in Θ(n + m) = Θ(n) and needs no union bookkeeping.
    """
    return build_cluster_map_dfs(graph)
