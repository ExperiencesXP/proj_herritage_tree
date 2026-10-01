"""Per-cluster drawing over the family clusters — `docs/cluster_map_and_recursive_search.md` §6.

Want: a drawing of ``H_i = G[C_i]`` per cluster (§1.3). Recipe: layered Sugiyama layout on
the (I2-clean) DAG of each cluster, in three passes:

1. **Rank / generation layer.** Longest-path ranking in topological order:

       rank(v) = δ + max_{(p,v) ∈ E} rank(p),   rank = 0 for persons without parents

   (δ = one generation step). Parents rank strictly above their children in the layout, so
   a child sits exactly one "generation step" below both parents — the visual encoding of
   the deg⁻ ≤ 2 structure.

2. **Within-layer ordering (crossing minimisation).** Several alternating sweeps use the
   barycenter heuristic of §6:

       b(u) = (1/deg(u)) · Σ_{(w,u) ∈ Ē} pos(w)

   Sorting each layer by b(u) reduces edge crossings. Crossing minimisation is NP-hard in
   general — the heuristic is the accepted choice; it costs O(s·(n+m)) for s sweeps.

3. **Coordinates.** x = position from pass (2) (ordered within its layer), y = rank(v)·Δ
   with Δ a pixel-per-generation constant. Cluster bounding boxes never overlap because
   clusters are disjoint (§1.3) — the reason layout is embarrassingly parallel (O12),
   available via :func:`layout_cluster_map` ``parallel=True``.

Everything in this module runs on :class:`cluster_map.Cluster` values produced by the
builders of §2.3 — the search from §2 only has to supply ``C_i`` and ``E(C_i)``.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from bisect import bisect_left
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from cluster_map import Cluster, ClusterMap
from graph_model import FamilyGraph
from search import CycleError, explore_safe

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
    """The drawing of one cluster: 2D coordinates plus the layer structure (§6)."""

    cluster_id: int
    ranks: dict[Any, int]
    x: dict[Any, float]
    y: dict[Any, float]
    layers: tuple[tuple[Any, ...], ...]
    crossings: int
    delta: float


def validate_acyclic(graph: FamilyGraph) -> None:
    """Cycle guard of §2.6 as a standalone pre-pass; raises :class:`CycleError` (Theorem 3.4).

    Layered layout needs a topological order (well-defined only for a DAG); rather than
    *assuming* I2, the guard flags every directed cycle first. It walks the **directed**
    parental edges (``mom``/``dad``) on purpose: a self-parent ``p.mom = p`` is a length-1
    cycle that the loopless undirected adjacency of Ē would silently drop.
    """
    colour: dict[Any, int] = {}
    for seed in graph.persons:
        if seed not in colour:  # WHITE: undiscovered
            explore_safe(seed, colour, neighbours=None)  # directed mom/dad walk
    return


def assign_ranks(cluster: Cluster, delta: int = 1) -> dict[Any, int]:
    """Pass 1 of §6: longest-path ranks ``rank(v) = δ + max_{(p,v)∈E} rank(p)`` via Kahn.

    Topological order by in-degrees over E (parent → child); O(n + m) per cluster.
    Raises :class:`CycleError` if the induced subgraph is not a DAG (I2 enforced).
    """
    members = tuple(sorted(cluster.members, key=lambda p: p.name))
    inside = set(members)
    parents: dict[Any, set[Any]] = {v: set() for v in members}
    children: dict[Any, set[Any]] = {v: set() for v in members}
    for u, v in cluster.edges:  # (child, parent) per §1.1
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
            ranks[child] = max(
                ranks[child], ranks[parent] + delta
            )  # longest path (§6.1)
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if processed != len(members):
        raise CycleError("cycle in parental record — layered layout needs a DAG (I2)")
    return ranks


def _crossings_between(
    upper: Sequence[Any], lower: Sequence[Any], neighbours: dict[Any, tuple[Any, ...]]
) -> int:
    """Adjacent-layer inversion count between ``upper`` and ``lower`` (O(e log e))."""
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
    """Total adjacent-layer crossings of a layering (used for sweep diagnostics)."""
    return sum(
        _crossings_between(upper, lower, neighbours)
        for upper, lower in zip(layers, layers[1:])
    )


def _barycenter_sweep(
    layers: list[list[Any]],
    neighbours: dict[Any, tuple[Any, ...]],
    forward: bool,
) -> list[list[Any]]:
    """Pass 2 of §6: reorder every layer by ``b(u) = (1/deg(u))·Σ_{w∈Ē(u)} pos(w)``."""
    pos = {node: i for layer in layers for i, node in enumerate(layer)}
    order = range(len(layers)) if forward else range(len(layers) - 1, -1, -1)
    for li in order:
        nodes = layers[li]

        def bary(node: Any) -> tuple[float, int]:
            nbs = neighbours[node]
            if not nbs:
                return float(pos[node]), pos[node]  # isolated: keep position
            b = sum(pos[w] for w in nbs if w in pos) / len(nbs)
            return b, pos[node]

        nodes.sort(key=bary)  # stable: ties broken by current position
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
    """Full three-pass Sugiyama layout of ``H_i = G[C_i]`` (§6).

    ``delta`` is Δ, the pixel-per-generation constant of pass 3: y = rank(v)·Δ.
    ``sweeps`` alternating barycenter passes (top→bottom and bottom→top) drive the
    heuristic toward fewer crossings; each pass is O(n + m).
    """
    key = order or (lambda p: p.name)
    members = tuple(sorted(cluster.members, key=key))
    if not members:
        return Layout(cluster.id, {}, {}, {}, (), 0, delta)

    ranks = assign_ranks(cluster)

    inside = set(members)
    neighbour_sets: dict[Any, set[Any]] = {v: set() for v in members}
    # cluster.edges draw from (child, parent) per §1.1; the undirected adjacency of Ē
    # is exactly the pairs inside the cluster (edges never cross clusters, §1.3).
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
            x_map[node] = float(i)  # position from pass (2) (§6 pass 3)
            y_map[node] = ranks[node] * delta  # Δ per generation step
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
    """Layout every cluster — O9 (per-cluster layout *after* grouping).

    With ``parallel=True`` clusters are drawn concurrently (O12): they are disjoint
    vertex sets with no edges between them, so the map step is embarrassingly parallel
    and needs no locks.  Otherwise each cluster costs Θ(|C_i| + |E(C_i)|).
    """

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
    """Source-free export (§6): one ``flowchart TB`` chunk per cluster for Mermaid.

    ``TB`` (top → bottom) puts both parents above their children — the conventional
    pedigree orientation matching ``y = rank(v)·Δ`` of pass (3) — with arrows drawn
    parent → child.  Render the result to PNG/SVG for docs and READMEs; no Mermaid source
    needs to live in the codebase.
    """
    members = tuple(sorted(cluster.members, key=lambda p: p.name))
    ids = {p: f"n{i}" for i, p in enumerate(members)}
    esc = lambda s: s.replace('"', "'")
    lines = ["flowchart TB"]
    lines += [f'    {ids[p]}["{esc(label(p))}"]' for p in members]
    lines += [f"    {ids[parent]} --> {ids[child]}" for child, parent in cluster.edges]
    return "\n".join(lines)


def to_dot(cluster: Cluster, *, label: Callable[[Any], str] = lambda p: p.name) -> str:
    """Graphviz export of the same layout contract: rankdir=TB, parent → child arrows."""
    members = tuple(sorted(cluster.members, key=lambda p: p.name))
    ids = {p: f"n{i}" for i, p in enumerate(members)}
    esc = lambda s: s.replace('"', '\\"')
    lines = ["digraph {", "    rankdir=TB; node [shape=box];"]
    lines += [f'    {ids[p]} [label="{esc(label(p))}"];' for p in members]
    lines += [f"    {ids[parent]} -> {ids[child]};" for child, parent in cluster.edges]
    lines.append("}")
    return "\n".join(lines)
