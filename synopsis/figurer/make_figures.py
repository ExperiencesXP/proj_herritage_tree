from __future__ import annotations

import random
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

_HERE = Path(__file__).resolve()
_SRC = _HERE.parents[2] / "src"
sys.path.insert(0, str(_SRC))

from model.person import Person
import model.cluster_map as cluster_map_module
from controller import FamilyController
import draw as draw_module
import model.graph_model as graph_model_module
import model.search as search_module
from view import render_cluster

OUT = _HERE.parent


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def familie_demo() -> None:
    ada = Person("ada")
    mia = Person("mia", mom=ada)
    dan = Person("dan", dad=ada)
    kid = Person("kid", mom=mia, dad=dan)
    solo = Person("solo")
    graph = graph_model_module.build_family_graph([ada, mia, dan, kid, solo])
    cmap = cluster_map_module.build_cluster_map(graph)
    layouts = draw_module.layout_cluster_map(cmap)

    clusters = sorted(cmap.clusters, key=lambda c: (-len(c), c.id))
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.6))
    for ax, cluster in zip(axes, clusters):
        layout = next(l for l in layouts if l.cluster_id == cluster.id)
        render_cluster(cluster, layout, ax=ax, highlight={kid})
    fig.suptitle("Demo-familien fra design-dokumentet §1.3 (to klynger)", fontsize=11)
    fig.tight_layout()
    save(fig, "familie_demo")


def stor_familie() -> None:
    henrik, mette = Person("henrik"), Person("mette")
    ole, else_ = Person("ole"), Person("else")
    karen = Person("karen")
    lars = Person("lars", mom=mette, dad=henrik)
    iben = Person("iben", mom=mette, dad=henrik)
    sofie = Person("sofie", mom=else_, dad=ole)
    kasper = Person("kasper", mom=else_, dad=ole)
    pia = Person("pia", mom=karen)
    anders = Person("anders", mom=sofie, dad=lars)
    line = Person("line", mom=pia, dad=kasper)
    emma = Person("emma", mom=line, dad=anders)
    maja = Person("maja", mom=line, dad=anders)

    app = FamilyController([henrik, mette, ole, else_, karen, lars, iben,
                            sofie, kasper, pia, anders, line, emma, maja])
    app.build_map()
    (layout,) = app.layout(parallel=False)
    assert app.cluster_map is not None
    cluster = app.cluster_map.clusters[0]

    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    render_cluster(cluster, layout, ax=ax, highlight={emma})
    ax.set_title("Stor familie (7.10): fire generationer, én klynge — emma markeret")
    fig.tight_layout()
    save(fig, "stor_familie")

    shared = app.find_common_ancestor("anders", "line")
    print("  stor_familie: fælles aner for anders og line = "
          + ", ".join(p.name for p in shared))
    print(f"  is_related(anders, line) = {app.is_related('anders', 'line')},"
          f" is_related(emma, pia) = {app.is_related('emma', 'pia')}")


def diamond_chain(depth: int) -> Person:
    tip = Person("a0")
    for i in range(depth):
        b_i = Person(f"b{i}", mom=tip)
        c_i = Person(f"c{i}", mom=tip)
        tip = Person(f"a{i + 1}", mom=b_i, dad=c_i)
    return tip


def pedigree_collapse() -> None:
    ks = list(range(1, 13))
    actual = []
    for k in ks:
        tip = diamond_chain(k)
        actual.append(len(search_module.ancestors_iterative(tip)))
    heights = [2 * k for k in ks]
    bound = [2 ** (g + 1) - 1 for g in heights]

    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    ax.plot(ks, bound, "o--", label="binær grænse $2^{g+1}-1$ (uden kollaps)")
    ax.plot(ks, actual, "s-", label="målt $|\\mathrm{Anc}(v_k)| = 3k+1$ (D$_k$)")
    ax.set_yscale("log")
    ax.set_xlabel("diamanter $k$ i kæden D$_k$ (højde $g = 2k$)")
    ax.set_ylabel("antal forfædre (logaritmisk)")
    ax.set_title("Pedigree-collapse (I3): faktisk antal forfædre mod binær grænse")
    ax.legend()
    ax.grid(True, which="both", ls=":", alpha=0.5)
    fig.tight_layout()
    save(fig, "pedigree_collapse")


def random_population(rng: random.Random, target: int) -> list[Person]:
    people = [Person(f"p{i}") for i in range(min(target, 8))]
    while len(people) < target:
        if rng.random() < 0.75 and len(people) >= 2:
            mom = rng.choice(people)
            dad = rng.choice(people)
            if mom is dad:
                dad = None
            people.append(Person(f"p{len(people)}", mom=mom, dad=dad))
        else:
            people.append(Person(f"p{len(people)}"))
    return people


def scaling() -> None:
    sizes = [500, 1000, 2000, 5000, 10000, 20000]
    times = []
    for n in sizes:
        people = random_population(random.Random(n), n)
        graph = graph_model_module.build_family_graph(people)
        best = float("inf")
        for _ in range(5):
            start = time.perf_counter()
            cluster_map_module.build_cluster_map_dfs(graph)
            best = min(best, time.perf_counter() - start)
        times.append(best)

    ns = np.array(sizes, dtype=float)
    ts = np.array(times) * 1e6
    slope, intercept = np.polyfit(ns, ts, 1)

    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    ax.plot(ns, ts, "o", label="målt køretid (bedst af 5)")
    fit_label = "lineær fit: t(n) = %.2f·n %s %.0f [µs]" % (
        slope,
        "+" if intercept >= 0 else "−",
        abs(intercept),
    )
    ax.plot(ns, slope * ns + intercept, "-", label=fit_label)
    ax.set_xlabel("personer $n$ i populationen")
    ax.set_ylabel("køretid [µs]")
    ax.set_title("Cluster map (DFS): målt skalering mod lineær forudsigelse")
    ax.legend()
    ax.grid(True, ls=":", alpha=0.5)
    fig.tight_layout()
    save(fig, "scaling")
    for n, t in zip(sizes, times):
        print(f"  n={n:6d}  t={t * 1e6:9.1f} us")
    print(f"  fit: t(n) = {slope:.2f} n + {intercept:.0f} us")


if __name__ == "__main__":
    familie_demo()
    stor_familie()
    pedigree_collapse()
    scaling()
    print("figures written to", OUT)
