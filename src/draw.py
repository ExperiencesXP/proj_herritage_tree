from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from bisect import bisect_left
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from models.cluster_map import Cluster, ClusterMap
from models.graph_model import FamilyGraph
from models.search import CycleError, explore_safe

__all__ = [
    "Layout",
    "validate_acyclic",
    "assign_ranks",
    "layout_cluster",
    "layout_cluster_map",
    "crossings",
    "to_mermaid",
    "to_dot",
]


@dataclass(frozen=True, slots=True)
class Layout:

    cluster_id: int
    ranks: dict[Any, int]
    x: dict[Any, float]
    y: dict[Any, float]
    layers: tuple[tuple[Any, ...], ...]
    crossings: int
    delta: float


def validate_acyclic(graph: FamilyGraph) -> None:
    colour: dict[Any, int] = {}
    for seed in graph.persons:
        if seed not in colour:
            explore_safe(seed, colour, neighbours=None)
    return


def assign_ranks(cluster: Cluster, delta: int = 1) -> dict[Any, int]:
    members = tuple(sorted(cluster.members, key=lambda p: p.name))
    inside = set(members)
    parents: dict[Any, set[Any]] = {v: set() for v in members}
    children: dict[Any, set[Any]] = {v: set() for v in members}
    for u, v in cluster.edges:
        if u in inside and v in inside:
            parents[u].add(v)
            children[v].add(u)

    ranks = {v: 0 for v in members}
    indegree = {v: len(parents[v]) for v in members}
    ready = deque(
        sorted((v for v in members if indegree[v] == 0), key=lambda p: p.name)
    )
    processed = 0
    while ready:
        parent = ready.popleft()
        processed += 1
        for child in children[parent]:
            ranks[child] = max(ranks[child], ranks[parent] + delta)
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if processed != len(members):
        raise CycleError("cycle in parental record — layered layout needs a DAG (I2)")
    return ranks


def _crossings_between(
    upper: Sequence[Any], lower: Sequence[Any], neighbours: dict[Any, tuple[Any, ...]]
) -> int:
    pos_lower = {node: i for i, node in enumerate(lower)}
    uppers: list[tuple[int, int]] = []
    pos_upper = {node: i for i, node in enumerate(upper)}
    for u in upper:
        for w in neighbours[u]:
            if w in pos_lower:
                uppers.append((pos_upper[u], pos_lower[w]))
    uppers.sort()
    inversions = 0
    seen: list[int] = []
    for _, low in uppers:
        i = bisect_left(seen, low)
        inversions += len(seen) - i
        seen.insert(i, low)
    return inversions


def crossings(
    layers: Sequence[Sequence[Any]], neighbours: dict[Any, tuple[Any, ...]]
) -> int:
    return sum(
        _crossings_between(upper, lower, neighbours)
        for upper, lower in zip(layers, layers[1:])
    )


def _barycenter_sweep(
    layers: list[list[Any]],
    neighbours: dict[Any, tuple[Any, ...]],
    forward: bool,
) -> list[list[Any]]:
    pos = {node: i for layer in layers for i, node in enumerate(layer)}
    order = range(len(layers)) if forward else range(len(layers) - 1, -1, -1)
    for li in order:
        nodes = layers[li]

        def bary(node: Any) -> tuple[float, int]:
            nbs = neighbours[node]
            if not nbs:
                return float(pos[node]), pos[node]
            b = sum(pos[w] for w in nbs if w in pos) / len(nbs)
            return b, pos[node]

        nodes.sort(key=bary)
        layers[li] = nodes
        for i, node in enumerate(nodes):
            pos[node] = i
    return layers


def layout_cluster(
    cluster: Cluster,
    *,
    delta: float = 40.0,
    sweeps: int = 4,
    order: Callable[[Any], str] | None = None,
) -> Layout:
    key = order or (lambda p: p.name)
    members = tuple(sorted(cluster.members, key=key))
    if not members:
        return Layout(cluster.id, {}, {}, {}, (), 0, delta)

    ranks = assign_ranks(cluster)

    inside = set(members)
    neighbour_sets: dict[Any, set[Any]] = {v: set() for v in members}
    for u, v in cluster.edges:
        if u in inside and v in inside:
            neighbour_sets[u].add(v)
            neighbour_sets[v].add(u)
    neighbours_list: dict[Any, tuple[Any, ...]] = {
        v: tuple(sorted(nbrs, key=key)) for v, nbrs in neighbour_sets.items()
    }

    max_rank = max(ranks.values())
    layers: list[list[Any]] = [
        [v for v in members if ranks[v] == r] for r in range(max_rank + 1)
    ]
    for pass_index in range(sweeps):
        _barycenter_sweep(layers, neighbours_list, forward=pass_index % 2 == 0)

    x_map: dict[Any, float] = {}
    y_map: dict[Any, float] = {}
    for layer in layers:
        for i, node in enumerate(layer):
            x_map[node] = float(i)
            y_map[node] = ranks[node] * delta
    out_layers = tuple(tuple(layer) for layer in layers)
    return Layout(
        cluster_id=cluster.id,
        ranks=ranks,
        x=x_map,
        y=y_map,
        layers=out_layers,
        crossings=crossings(list(out_layers), neighbours_list),
        delta=delta,
    )


def layout_cluster_map(
    cluster_map: ClusterMap,
    *,
    delta: float = 40.0,
    sweeps: int = 4,
    parallel: bool = False,
    order: Callable[[Any], str] | None = None,
) -> tuple[Layout, ...]:

    def draw(cluster: Cluster) -> Layout:
        return layout_cluster(cluster, delta=delta, sweeps=sweeps, order=order)

    clusters = cluster_map.clusters
    if not parallel or len(clusters) < 2:
        return tuple(draw(cluster) for cluster in clusters)
    with ThreadPoolExecutor(max_workers=len(clusters)) as pool:
        return tuple(pool.map(draw, clusters))


def to_mermaid(
    cluster: Cluster, *, label: Callable[[Any], str] = lambda p: p.name
) -> str:
    members = tuple(sorted(cluster.members, key=lambda p: p.name))
    ids = {p: f"n{i}" for i, p in enumerate(members)}
    esc = lambda s: s.replace('"', "'")
    lines = ["flowchart TB"]
    lines += [f'    {ids[p]}["{esc(label(p))}"]' for p in members]
    lines += [f"    {ids[parent]} --> {ids[child]}" for child, parent in cluster.edges]
    return "\n".join(lines)


def to_dot(cluster: Cluster, *, label: Callable[[Any], str] = lambda p: p.name) -> str:
    members = tuple(sorted(cluster.members, key=lambda p: p.name))
    ids = {p: f"n{i}" for i, p in enumerate(members)}
    esc = lambda s: s.replace('"', '\\"')
    lines = ["digraph {", "    rankdir=TB; node [shape=box];"]
    lines += [f'    {ids[p]} [label="{esc(label(p))}"];' for p in members]
    lines += [f"    {ids[parent]} -> {ids[child]};" for child, parent in cluster.edges]
    lines.append("}")
    return "\n".join(lines)
