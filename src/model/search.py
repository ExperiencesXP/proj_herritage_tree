from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from model.graph_model import FamilyGraph

__all__ = [
    "explore",
    "explore_iterative",
    "explore_safe",
    "ancestors",
    "ancestors_iterative",
    "find_common_ancestor",
    "is_related",
    "descendants",
    "find_with_early_exit",
    "CycleError",
    "StopSearch",
    "NeighboursFn",
    "neighbours_of",
]

NeighboursFn = Callable[[Any], Iterable[Any]]


class CycleError(ValueError):
    pass


class StopSearch(Exception):
    pass


def neighbours_of(graph: FamilyGraph) -> NeighboursFn:
    return graph.neighbours


def _parents(node: Any) -> tuple[Any, ...]:
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
    if node is None:
        return 0
    state = colour.get(node)
    if state == 2:
        return 0
    if state == 1:
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
    if p is None:
        return frozenset()
    cache: dict[Any, frozenset[Any]] = {}
    on_stack: set[Any] = set()
    stack: list[tuple[Any, bool]] = [(p, False)]
    while stack:
        node, expanded = stack.pop()
        if node is None:
            continue
        if expanded:
            out = {node}
            for q in (node.mom, node.dad):
                if q is not None:
                    out |= cache[q]
            cache[node] = frozenset(out)
            on_stack.discard(node)
            continue
        if node in cache:
            continue
        if node in on_stack:
            raise CycleError("cycle in parental record")
        on_stack.add(node)
        stack.append((node, True))
        for q in (node.mom, node.dad):
            if q is not None and q not in cache:
                stack.append((q, False))
    return cache[p]


def descendants(graph: FamilyGraph, p: Any) -> frozenset[Any]:
    if p is None:
        return frozenset()
    return frozenset(explore_iterative(p, neighbours=graph.children)) - {p}


def find_common_ancestor(a: Any, b: Any) -> list[Any]:
    if a is None or b is None:
        return []
    shared = ancestors_iterative(a) & ancestors_iterative(b)
    return sorted(shared, key=lambda p: getattr(p, "name", str(p)))


def is_related(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return False
    return not ancestors_iterative(a).isdisjoint(ancestors_iterative(b))


def find_with_early_exit(
    node: Any,
    goal: Callable[[Any], bool],
    neighbours: NeighboursFn | None = None,
) -> Any | None:
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
