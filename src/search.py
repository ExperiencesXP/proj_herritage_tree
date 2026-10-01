"""Recursive search over the family graph — `docs/cluster_map_and_recursive_search.md` §2 and §3.

Three searches live here, each computing exactly what the analysis proves it computes:

* :func:`explore` / :func:`explore_iterative` — the cluster of a seed as the **least fixed
  point** of the monotone operator Φ_v on (2^V, ⊆) (§2.1, Theorem 3.2).  The ``visited``
  guard is the fixed-point stabilisation: each node is expanded once, so
  T = Θ(n + m) = Θ(n) by equation (1) and S = Θ(n) (equation 2).
* :func:`ancestors` / :func:`descendants` — mutual recursion over the ancestral query
  (§2.5), **memoised**: without a cache the cost is Θ(2^{d/2}) for diamond chains or
  Θ(φ^d) for Fibonacci pedigrees (§4.3); with the cache it is Θ(n + m).
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
        q for q in (getattr(node, "mom", None), getattr(node, "dad", None)) if q is not None
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
    """Goal-directed 3-colour search returning the first match (O7/O11 reference form)."""
    colour: dict[Any, int] = {}
    found: list[Any] = []

    def goal_and_stop(candidate: Any) -> bool:
        if goal(candidate):
            found.append(candidate)
            return True
        return False

    try:
        explore_safe(node, colour, neighbours, on_node=goal_and_stop)
    except StopSearch:
        return found[0] if found else None
    return None