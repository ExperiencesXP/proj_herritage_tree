from __future__ import annotations

import random
import time
from types import SimpleNamespace

import pytest


def build_children(people):
    children: dict = {}
    for p in people:
        for q in (p.mom, p.dad):
            if q is not None:
                children.setdefault(q, []).append(p)
    return children


def undirected_neighbours(node, children):
    return [q for q in (node.mom, node.dad, *children.get(node, ())) if q is not None]


def bfs_reference(seeds, people):
    children = build_children(people)
    seen: set = set()
    stack = list(seeds)
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(undirected_neighbours(node, children))
    return seen


def component_count(people):
    children = build_children(people)
    seen: set = set()
    comps = 0
    for person in people:
        if person in seen:
            continue
        comps += 1
        stack = [person]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(undirected_neighbours(cur, children))
    return comps


def chain(person_cls, length: int, start=None):
    current = start
    for i in range(length):
        current = person_cls(f"chain{i}", mom=current)
    return current


def diamond_chain(person_cls, depth: int):
    tip = person_cls("a0")
    for i in range(depth):
        b_i = person_cls(f"b{i}", mom=tip)
        c_i = person_cls(f"c{i}", mom=tip)
        tip = person_cls(f"a{i + 1}", mom=b_i, dad=c_i)
    return tip


def random_population(person_cls, rng, target: int = 60):
    people = [person_cls(f"p{i}") for i in range(min(target, 8))]
    while len(people) < target:
        if rng.random() < 0.75 and len(people) >= 2:
            mom = rng.choice(people)
            dad = rng.choice(people)
            if mom is dad:
                dad = None
            child = person_cls(f"p{len(people)}", mom=mom, dad=dad)
        else:
            child = person_cls(f"p{len(people)}")
        people.append(child)
    return people


def test_cluster_matches_bfs_reference(person_cls, graph_model_module, cluster_map_module):
    for seed in (1729, 271828, 314159, 161803):
        rng = random.Random(seed)
        people = random_population(person_cls, rng, target=rng.randint(20, 90))
        graph = graph_model_module.build_family_graph(people)
        dfs_map = cluster_map_module.build_cluster_map_dfs(graph)
        uf_map = cluster_map_module.build_cluster_map_unionfind(graph)
        pairs_map = cluster_map_module.build_cluster_map_pairs(
            people, [(p, q) for p in people for q in (p.mom, p.dad) if q is not None]
        )

        for person in people:
            ref = bfs_reference([person], people)
            assert set(dfs_map.members_of(person)) == ref
            assert set(uf_map.members_of(person)) == ref
            assert set(pairs_map.members_of(person)) == ref


def test_cluster_count_identity_eq3(person_cls, graph_model_module, cluster_map_module):
    for seed in (42, 777, 2026):
        rng = random.Random(seed)
        people = random_population(person_cls, rng, target=rng.randint(25, 120))
        graph = graph_model_module.build_family_graph(people)
        n = len(people)
        edge_pairs = {
            (p, q) for p in people for q in (p.mom, p.dad) if q is not None and q is not p
        }
        uf_map = cluster_map_module.build_cluster_map_unionfind(graph)

        s = 0
        uf = cluster_map_module.UnionFind(n)
        idx = {p: i for i, p in enumerate(people)}
        for u, v in edge_pairs:
            if uf.union(idx[u], idx[v]):
                s += 1

        assert uf_map.k == n - s
        assert uf_map.k == len(uf_map.clusters)
        assert component_count(people) == n - s
        assert component_count(people) == uf_map.k


def test_ancestor_closure_size_classical_family(person_cls, search_module):
    g1 = person_cls("g1")
    g2 = person_cls("g2")
    parent1 = person_cls("parent1", mom=g1, dad=g2)
    seed = person_cls("seed", mom=parent1)

    closure = search_module.ancestors(seed)
    assert closure == {seed, parent1, g1, g2}
    assert len(closure) == 4


def test_memoised_closure_handles_pedigree_collapse(person_cls, search_module):
    tip = diamond_chain(person_cls, 12)
    closure = search_module.ancestors(tip)
    assert len(closure) == 13 + 2 * 12
    start = time.perf_counter()
    search_module.ancestors(tip)
    assert time.perf_counter() - start < 2.0


def test_iterative_survives_deep_chain(person_cls, search_module):
    tip = chain(person_cls, 2000)
    visited_search = search_module.explore_iterative(tip, neighbours=lambda p: (p.mom,))
    assert len(visited_search) == 2000


def test_recursive_reference_raises_recursionerror(person_cls, search_module):
    tip = chain(person_cls, 1500)
    with pytest.raises(RecursionError):
        search_module.explore(tip, set(), [], neighbours=lambda p: (p.mom,))


def test_ancestors_iterative_matches_reference(person_cls, search_module):
    tip = diamond_chain(person_cls, 8)
    assert search_module.ancestors_iterative(tip) == search_module.ancestors(tip)
    assert search_module.ancestors_iterative(None) == frozenset()


def test_ancestors_iterative_survives_deep_chain(person_cls, search_module):
    tip = chain(person_cls, 2000)
    closure = search_module.ancestors_iterative(tip)
    assert len(closure) == 2000


def test_ancestors_iterative_flags_cycles(person_cls, search_module):
    a, b = person_cls("a"), person_cls("b")
    a.mom = b
    b.mom = a
    with pytest.raises(ValueError):
        search_module.ancestors_iterative(a)


def test_common_ancestors_and_is_related(person_cls, search_module):
    ada = person_cls("ada")
    mia = person_cls("mia", mom=ada)
    dan = person_cls("dan", dad=ada)
    kid = person_cls("kid", mom=mia, dad=dan)
    solo = person_cls("solo")

    assert [p.name for p in search_module.find_common_ancestor(mia, dan)] == ["ada"]
    assert search_module.is_related(mia, dan) is True
    assert search_module.find_common_ancestor(kid, solo) == []
    assert search_module.is_related(kid, solo) is False
    assert search_module.is_related(ada, kid) is True
    assert [p.name for p in search_module.find_common_ancestor(ada, kid)] == ["ada"]
    assert search_module.find_common_ancestor(None, kid) == []
    assert search_module.is_related(None, kid) is False


def test_goal_search_over_undirected_shadow_has_no_false_cycles(person_cls, search_module):
    ada = person_cls("ada")
    mia = person_cls("mia", mom=ada)
    dan = person_cls("dan", dad=ada)
    kid = person_cls("kid", mom=mia, dad=dan)

    def neighbours(p):
        return [q for q in (p.mom, p.dad) if q is not None] + [
            c for c in (mia, dan, kid) if c.mom is p or c.dad is p
        ]

    assert (
        search_module.find_with_early_exit(
            kid, lambda p: p.name == "solo", neighbours=neighbours
        )
        is None
    )
    found = search_module.find_with_early_exit(
        kid, lambda p: p.name == "ada", neighbours=neighbours
    )
    assert found is not None and found.name == "ada"


def test_self_parent_cycle_raises(person_cls, draw_module):
    person = person_cls("self_parent")
    person.mom = person
    graph = SimpleNamespace(persons=(person,))
    with pytest.raises(ValueError):
        draw_module.validate_acyclic(graph)


def test_longer_cycle_raises(person_cls, draw_module):
    a, b = person_cls("a"), person_cls("b")
    a.mom = b
    b.mom = a
    graph = SimpleNamespace(persons=(a, b))
    with pytest.raises(ValueError):
        draw_module.validate_acyclic(graph)


def test_layout_rank_and_y_coordinate(person_cls, cluster_map_module, graph_model_module, draw_module):
    chain_tip = chain(person_cls, 6)
    graph = graph_model_module.build_family_graph([chain_tip], include_ancestors=True)
    cmap = cluster_map_module.build_cluster_map(graph)
    cluster = cmap.clusters[0]
    layout = draw_module.layout_cluster(cluster)

    assert layout.ranks[chain_tip] == 5
    assert max(layout.ranks.values()) == 5
    delta = layout.delta
    for person in cluster.members:
        assert layout.y[person] == pytest.approx(layout.ranks[person] * delta)
        assert layout.x[person] >= 0.0


def test_mermaid_export_shape(person_cls, cluster_map_module, graph_model_module, draw_module):
    kids = chain(person_cls, 4)
    graph = graph_model_module.build_family_graph([kids], include_ancestors=True)
    cmap = cluster_map_module.build_cluster_map(graph)
    cluster = cmap.clusters[0]
    text = draw_module.to_mermaid(cluster)

    assert text.startswith("flowchart TB")
    assert "-->" in text
    lines = [line for line in text.splitlines() if "[" in line]
    assert len(lines) == 4


def test_pairs_map_exports_keep_parent_to_child_arrows(person_cls, cluster_map_module, draw_module):
    a, b, c = person_cls("a"), person_cls("b"), person_cls("c")
    pmap = cluster_map_module.build_cluster_map_pairs([a, b, c], [(b, a), (c, b)])
    text = draw_module.to_mermaid(pmap.clusters[0])
    assert '    n0["a"]' in text
    assert "    n0 --> n1" in text
    assert "    n1 --> n2" in text


def test_str_names_the_unknown_parent_slot(person_cls):
    ada = person_cls("ada")
    assert str(ada) == "ada has no known parents."
    assert str(person_cls("mia", mom=ada)) == "mia's mother is ada and no known father."
    assert str(person_cls("dan", dad=ada)) == "dan's father is ada and no known mother."
    assert (
        str(person_cls("kid", mom=person_cls("mia"), dad=person_cls("dan")))
        == "kid's mother is mia and father is dan."
    )


def test_scaling_linear_in_n(person_cls, graph_model_module, cluster_map_module):
    sizes = (500, 1000, 2000)
    samples = {}
    for n in sizes:
        rng = random.Random(n)
        people = random_population(person_cls, rng, target=n)
        graph = graph_model_module.build_family_graph(people)

        best = float("inf")
        for _ in range(3):
            start = time.perf_counter()
            cluster_map_module.build_cluster_map_dfs(graph)
            best = min(best, time.perf_counter() - start)
        samples[n] = best

    ratio_small = samples[1000] / max(samples[500], 1e-6)
    ratio_large = samples[2000] / max(samples[1000], 1e-6)
    assert abs(ratio_small - 2.0) < 0.7 or abs(ratio_large - 2.0) < 0.7
