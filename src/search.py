"""Recursive search over the family graph — `docs/cluster_map_and_recursive_search.md` §2 and §3.

Three searches live here, each computing exactly what the analysis proves it computes:

* :func:`explore` / :func:`explore_iterative` — the cluster of a seed as the **least fixed
  point** of the monotone operator Φ_v on (2^V, ⊆) (§2.1, Theorem 3.2).  The ``visited``
  guard is the fixed-point stabilisation: each node is expanded once, so
  T = Θ(n + m) = Θ(n) by equation (1) and S = Θ(n) (equation 2).
* :func:`ancestors` / :func:`ancestors_iterative` — the ancestral query
  (§2.5), **memoised**: without a cache the cost is Θ(2^{d/2}) for diamond chains or
  Θ(φ^d) for Fibonacci pedigrees (§4.3); with the cache it is Θ(n + m).  Same
  reference/production split as :func:`explore`: the recursion is the readable form,
  the explicit-stack form is depth-safe (O5).
* :func:`explore_safe` — the 3-colour (WHITE/GRAY/BLACK) cycle guard of §2.6, complete for
  the acyclicity invariant I2 (Theorem 3.4).

The recursive :func:`explore` is the readable reference; :func:`explore_iterative` is the
production path (O5) because a pure chain has depth Θ(n) while CPython's frame budget is
R = 1000 (§4.2).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from graph_model import FamilyGraph

__all__ = [
    "explore",
    "explore_iterative",
    "explore_safe",
    "ancestors",
    "ancestors_iterative",
    "descendants",
    "find_with_early_exit",
    "CycleError",
    "StopSearch",
    "NeighboursFn",
    "neighbours_of",
]

NeighboursFn = Callable[[Any], Iterable[Any]]


class CycleError(ValueError):
    """Raised by the 3-colour guard when the parental record contains a cycle."""


class StopSearch(Exception):
    """Internal early-exit signal for goal-directed search (optimisation O7)."""


def neighbours_of(graph: FamilyGraph) -> NeighboursFn:
    """Bind a traversal to a :class:`FamilyGraph`'s undirected adjacency (Ē)."""
    return graph.neighbours


def _parents(node: Any) -> tuple[Any, ...]:
    """Parent slots of a person-like object (child → parent direction, §1.1)."""
    return tuple(
        q
        for q in (getattr(node, "mom", None), getattr(node, "dad", None))
        if q is not None
    )


def _neighbours(node: Any, neighbours: NeighboursFn | None) -> tuple[Any, ...]:
    return tuple(neighbours(node)) if neighbours is not None else _parents(node)


def explore(
    node: Any,
    visited: set[Any],
    members: list[Any],
    neighbours: NeighboursFn | None = None,
) -> None:
    """Reference recursion of §2.2: append every node reachable from ``node``.

    The ``visited`` guard is the fixed-point stabilisation: it turns the recursion into
    the least fixed point Φ_v(∅) (Lemma 3.1, Theorem 3.2) and guarantees termination
    since |S_t| = t ≤ n.  Default direction is parent-only (``mom``/``dad``); pass
    ``neighbours`` to walk Ē full-sided for cluster membership.
    """
    if node is None or node in visited:
        return
    visited.add(node)
    members.append(node)
    for w in _neighbours(node, neighbours):
        explore(w, visited, members, neighbours)


def explore_iterative(
    node: Any,
    members: set[Any] | None = None,
    neighbours: NeighboursFn | None = None,
) -> set[Any]:
    """Production traversal: same output set as :func:`explore`, explicit stack (O5).

    A chain of n = 2000 persons overflows Python's default R = 1000 frames in the
    recursive form (§4.2); this form only bounds its stack by the frontier size.
    """
    seen = members if members is not None else set()
    if node is None:
        return seen
    stack = [node]
    while stack:
        current = stack.pop()
        if current is None or current in seen:
            continue
        seen.add(current)
        stack.extend(w for w in _neighbours(current, neighbours) if w not in seen)
    return seen


def explore_safe(
    node: Any,
    colour: dict[Any, int],
    neighbours: NeighboursFn | None = None,
    *,
    on_node: Callable[[Any], bool] | None = None,
) -> int:
    """3-colour depth-first search of §2.6; returns the number of vertices BLACKened.

    ``colour`` maps node → state with 1 = GRAY (on the stack) and 2 = BLACK; a missing key
    is WHITE.  A GRAY back edge signals a cycle and raises :class:`CycleError` (a
    ``ValueError``) *before* the traversal can diverge — invariant I2 is enforced, not
    assumed (Theorem 3.4).

    Only sound on the **directed** parental neighbourhood (the default): in the
    undirected shadow Ē every tree edge doubles back to a GRAY parent and would be
    misreported as a cycle.  Use :func:`explore_iterative` (visited guard) on Ē.

    ``on_node`` is an optional goal predicate: when it returns True the search raises
    :class:`StopSearch` for early exit (O7) — worst case unchanged, expected cost d·b̄
    instead of n when the goal is near.
    """
    if node is None:
        return 0
    state = colour.get(node)
    if state == 2:  # BLACK
        return 0
    if state == 1:  # GRAY → back edge ⇒ cycle
        raise CycleError("cycle in parental record")
    colour[node] = 1
    if on_node is not None and on_node(node):
        raise StopSearch
    count = 1
    for w in _neighbours(node, neighbours):
        count += explore_safe(w, colour, neighbours, on_node=on_node)
    colour[node] = 2
    return count


def ancestors(p: Any) -> frozenset[Any]:
    """Memoised ancestral closure of §2.5: Anc(v) = {v} ∪ Anc(mom(v)) ∪ Anc(dad(v)).

    The per-seed cache is memoisation O2: each node is computed exactly once and reused,
    so a closure over a lattice-shaped pedigree costs Θ(n + m) instead of Θ(φ^d) for
    Fibonacci pedigrees or Θ(2^{d/2}) for diamond chains (§4.3).

    Reference recursion (O5): the frame depth is still Θ(d), so a pure chain past
    CPython's R = 1000 raises ``RecursionError`` — use :func:`ancestors_iterative`
    on the production path, exactly like :func:`explore` vs :func:`explore_iterative`.
    """
    cache: dict[Any, frozenset[Any]] = {}

    def closure(node: Any) -> frozenset[Any]:
        if node is None:
            return frozenset()
        hit = cache.get(node)
        if hit is not None:
            return hit
        out = {node} | set(closure(node.mom)) | set(closure(node.dad))
        cache[node] = frozenset(out)
        return cache[node]

    return closure(p)


def ancestors_iterative(p: Any) -> frozenset[Any]:
    """Production form of :func:`ancestors` (O5): same closure, explicit stack.

    The recurrence of §2.5 is evaluated bottom-up (post-order) with the same per-seed
    memo cache — each node is computed exactly once, Θ(n + m) by the potential argument
    of §4.3 — but without nesting Θ(d) Python frames: a 2000-person chain overflows the
    recursion limit in :func:`ancestors`, not here.  ``on_stack`` reuses the GRAY colour
    of §2.6: a node re-entered while still expanding is a back edge, so a parental cycle
    (violating I2) raises :class:`CycleError` instead of looping forever.
    """
    if p is None:
        return frozenset()
    cache: dict[Any, frozenset[Any]] = {}
    on_stack: set[Any] = set()
    stack: list[tuple[Any, bool]] = [(p, False)]
    while stack:
        node, expanded = stack.pop()
        if node is None:
            continue
        if expanded:  # both parents cached: fold the recurrence for this node
            out = {node}
            for q in (node.mom, node.dad):
                if q is not None:
                    out |= cache[q]
            cache[node] = frozenset(out)
            on_stack.discard(node)
            continue
        if node in cache:
            continue
        if node in on_stack:  # GRAY re-entry = cycle (§2.6)
            raise CycleError("cycle in parental record")
        on_stack.add(node)
        stack.append((node, True))
        for q in (node.mom, node.dad):
            if q is not None and q not in cache:
                stack.append((q, False))
    return cache[p]


def descendants(graph: FamilyGraph, p: Any) -> frozenset[Any]:
    """All descendants of ``p`` via ``child_index`` (§2.2) — the mirror of :func:`ancestors`."""
    if p is None:
        return frozenset()
    return frozenset(explore_iterative(p, neighbours=graph.children)) - {p}


def find_with_early_exit(
    node: Any,
    goal: Callable[[Any], bool],
    neighbours: NeighboursFn | None = None,
) -> Any | None:
    """Goal-directed search returning the first match, with early exit (O7).

    The visited-guarded iterative form (O5) is used on purpose instead of the 3-colour
    guard of :func:`explore_safe`: the goal search may run over the undirected shadow Ē
    (cluster membership), where the 3-colour "back edge" test would report a cycle for
    every ordinary parent-child pair.  The visited guard is the correct fixed-point
    stabilisation on Ē (Lemma 3.1); I2 diagnostics belong to :func:`draw.validate_acyclic`
    on the directed parental graph.  Worst case unchanged (Θ(n + m)); when the goal sits
    near the seed the unexplored branches are pruned, expected cost ≈ d·b̄ (O7).
    """
    if node is None:
        return None
    seen: set[Any] = set()
    stack = [node]
    while stack:
        current = stack.pop()
        if current is None or current in seen:
            continue
        if goal(current):
            return current
        seen.add(current)
        stack.extend(w for w in _neighbours(current, neighbours) if w not in seen)
    return None
