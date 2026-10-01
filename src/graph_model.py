"""Explicit graph view over the family data — `docs/cluster_map_and_recursive_search.md` §1.

``V`` is the population of :class:`main.Person` objects, ``E = {(p, mom(p)), (p, dad(p))}``
is the child → parent edge set, and ``Ē`` is its undirected shadow (cluster membership is
orientation-insensitive, §1.1).  Invariant **I1** (``deg⁻(v) ≤ 2``) yields ``m = |E| ≤ 2n``
(§1.2, equation 1), so every ``O(n + m)`` traversal in this project is ``Θ(n)``.

This module provides the building blocks the analysis calls for:

* ``child_index``   — the one-time reverse parent → child index (§2.2, guardrail O1/§5),
* dense integer ids — arrays instead of hash lookups (optimisation O4),
* CSR adjacency     — contiguous neighbour lists for large clusters (optimisation O6).
"""

from __future__ import annotations

from array import array
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from main import Person

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
    """Immutable graph view: dense ids (O4) plus the one-time reverse index (O1)."""

    persons: tuple[Person, ...]
    id_of: dict[Person, int]
    child_index: dict[Person, tuple[Person, ...]]

    @property
    def n(self) -> int:
        """``|V|``."""
        return len(self.persons)

    @property
    def m(self) -> int:
        """``|E|`` — at most ``2n`` by invariant I1 (equation 1)."""
        return sum(1 for p in self.persons for q in (p.mom, p.dad) if q is not None)

    def children(self, p: Person) -> tuple[Person, ...]:
        """All persons with ``p`` in a parent slot (the reverse index, Õ(1) lookup)."""
        return self.child_index.get(p, ())

    def neighbours(self, p: Person) -> tuple[Person, ...]:
        """Undirected neighbourhood in ``Ē`` (parents ∪ children), self-loops dropped.

        Cluster traversals (§2.2) walk exactly this adjacency, which is why they are
        orientation-insensitive.
        """
        seen: set[Person] = {p}
        out: list[Person] = []
        for q in (p.mom, p.dad, *self.child_index.get(p, ())):
            if q is not None and q not in seen:
                seen.add(q)
                out.append(q)
        return tuple(out)


def close_population(persons: Iterable[Person]) -> tuple[Person, ...]:
    """Return ``persons`` plus every ancestor they reference (transitively), in BFS order.

    Edges never cross clusters (§1.3): a person and its missing parents must land in the
    same cluster, so the population is closed upward before anything is indexed.  O(n).
    """
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
    """Index a population into a :class:`FamilyGraph` in one ``O(n)`` pass.

    The reverse ``child_index`` (§2.2) is built **here, once** — rebuilding it inside a
    traversal would regrow the cost to ``O(n·m)`` (see the O1 guardrails in §5).

    Raises ``ValueError`` if the same :class:`Person` appears twice, or if a parent link
    points outside the population unless ``include_ancestors`` collects those ancestors
    automatically (:func:`close_population`).
    """
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
    """Iterate ``E`` as ``(child, parent)`` pairs (skipping empty slots)."""
    for p in graph.persons:
        for q in (p.mom, p.dad):
            if q is not None:
                yield p, q


def undirected_edges(graph: FamilyGraph) -> Iterator[Pair]:
    """Iterate ``Ē`` without duplicates (self-loops are dropped).

    Pairs keep the **child → parent** orientation of ``E`` (§1.1) even though connectivity
    is orientation-insensitive: the layout passes of §6 (rank assignment, arrow direction
    in exports) need to know which endpoint is the parent.
    """
    seen: set[tuple[int, int]] = set()
    for u, v in parent_edges(graph):
        if u is v:
            continue
        a, b = sorted((graph.id_of[u], graph.id_of[v]))
        if (a, b) in seen:
            continue
        seen.add((a, b))
        yield u, v  # (child, parent) as produced by parent_edges


@dataclass(frozen=True, slots=True)
class CsrAdjacency:
    """Compressed-sparse-row adjacency of ``Ē`` (optimisation O6).

    ``offset[i] .. offset[i+1]`` indexes into ``edges``, which stores the dense ids of
    ``persons``.  Traversals become sequential scans of whole arrays instead of
    pointer chasing — the layout code (§6) and big-cluster traversals use this.
    """

    persons: tuple[Person, ...]
    offset: array  # 'i', len n + 1
    edges: array  # 'i', concatenated neighbourhoods

    def neighbour_ids(self, i: int) -> array:
        return self.edges[self.offset[i] : self.offset[i + 1]]


def build_csr(graph: FamilyGraph, members: Iterable[Person] | None = None) -> CsrAdjacency:
    """Build the CSR adjacency of ``Ē`` over ``members`` (or the whole population)."""
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
    """Connected component of ``csr.persons[seed]`` scanned straight from the arrays.

    Used to cross-check the recursive search (§8.1) and to traverse huge clusters
    without touching anything but contiguous ints (O6).
    """
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