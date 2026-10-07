from __future__ import annotations

from array import array
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from models.person import Person

__all__ = [
    "FamilyGraph",
    "CsrAdjacency",
    "build_family_graph",
    "close_population",
    "parent_edges",
    "undirected_edges",
    "build_csr",
    "reach_csr",
]

Pair = tuple[Person, Person]


@dataclass(frozen=True, slots=True)
class FamilyGraph:

    persons: tuple[Person, ...]
    id_of: dict[Person, int]
    child_index: dict[Person, tuple[Person, ...]]

    @property
    def n(self) -> int:
        return len(self.persons)

    @property
    def m(self) -> int:
        return sum(1 for p in self.persons for q in (p.mom, p.dad) if q is not None)

    def children(self, p: Person) -> tuple[Person, ...]:
        return self.child_index.get(p, ())

    def neighbours(self, p: Person) -> tuple[Person, ...]:
        seen: set[Person] = {p}
        out: list[Person] = []
        for q in (p.mom, p.dad, *self.child_index.get(p, ())):
            if q is not None and q not in seen:
                seen.add(q)
                out.append(q)
        return tuple(out)


def close_population(persons: Iterable[Person]) -> tuple[Person, ...]:
    order: list[Person] = []
    seen: set[Person] = set()
    for person in persons:
        if person not in seen:
            seen.add(person)
            order.append(person)
    cursor = 0
    while cursor < len(order):
        node = order[cursor]
        cursor += 1
        for q in (node.mom, node.dad):
            if q is not None and q not in seen:
                seen.add(q)
                order.append(q)
    return tuple(order)


def build_family_graph(
    persons: Iterable[Person], *, include_ancestors: bool = False
) -> FamilyGraph:
    ordered = close_population(persons) if include_ancestors else tuple(persons)
    id_of: dict[Person, int] = {}
    for index, p in enumerate(ordered):
        if p in id_of:
            raise ValueError(
                f"duplicate Person in population: {p.name!r} "
                f"(positions {id_of[p]} and {index})"
            )
        id_of[p] = index

    child_lists: dict[Person, list[Person]] = {p: [] for p in ordered}
    for p in ordered:
        for q in (p.mom, p.dad):
            if q is None:
                continue
            if q not in id_of:
                raise ValueError(
                    f"parent of {p.name!r} is not part of the population; "
                    "pass include_ancestors=True or list every Person"
                )
            child_lists[q].append(p)

    child_index = {p: tuple(child_lists[p]) for p in ordered}
    return FamilyGraph(persons=ordered, id_of=id_of, child_index=child_index)


def parent_edges(graph: FamilyGraph) -> Iterator[Pair]:
    for p in graph.persons:
        for q in (p.mom, p.dad):
            if q is not None:
                yield p, q


def undirected_edges(graph: FamilyGraph) -> Iterator[Pair]:
    seen: set[tuple[int, int]] = set()
    for u, v in parent_edges(graph):
        if u is v:
            continue
        a, b = sorted((graph.id_of[u], graph.id_of[v]))
        if (a, b) in seen:
            continue
        seen.add((a, b))
        yield u, v


@dataclass(frozen=True, slots=True)
class CsrAdjacency:

    persons: tuple[Person, ...]
    offset: array
    edges: array

    def neighbour_ids(self, i: int) -> array:
        return self.edges[self.offset[i] : self.offset[i + 1]]


def build_csr(
    graph: FamilyGraph, members: Iterable[Person] | None = None
) -> CsrAdjacency:
    ordered = tuple(members) if members is not None else graph.persons
    local = {p: i for i, p in enumerate(ordered)}
    offsets: list[int] = [0]
    flat: list[int] = []
    for p in ordered:
        for q in graph.neighbours(p):
            if q in local:
                flat.append(local[q])
        offsets.append(len(flat))
    return CsrAdjacency(
        persons=ordered,
        offset=array("i", offsets),
        edges=array("i", flat),
    )


def reach_csr(csr: CsrAdjacency, seed: int) -> tuple[Person, ...]:
    seen = bytearray(len(csr.persons))
    seen[seed] = 1
    stack = [seed]
    order: list[int] = []
    while stack:
        i = stack.pop()
        order.append(i)
        for pos in range(csr.offset[i], csr.offset[i + 1]):
            j = csr.edges[pos]
            if not seen[j]:
                seen[j] = 1
                stack.append(j)
    return tuple(csr.persons[i] for i in sorted(order))
