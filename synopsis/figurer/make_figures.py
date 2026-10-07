"""Generate the synopsis figures from the program's own modules.

Run inside the project venv:

    poetry run python synopsis/figurer/make_figures.py

Outputs (PDF, for \\includegraphics in the LaTeX synopsis):

* ``familie_demo.pdf``     — the demo family of docs/cluster_map_and_recursive_search.md
  §1.3, drawn by ``view.render_cluster`` (the product's own matplotlib View).
* ``pedigree_collapse.pdf`` — invariant I3: actual |Anc(v)| for the diamond chain family
  D_k against the naive binary bound 2^{g+1} - 1 (measured via ``search.ancestors_iterative``).
* ``scaling.pdf``          — measured wall time of the cluster-map construction for
  n in {500, ..., 20000} with a linear fit (verification plan §8.5).
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # figures go to disk only
import matplotlib.pyplot as plt
import numpy as np

_HERE = Path(__file__).resolve()
_SRC = _HERE.parents[2] / "src"
sys.path.insert(0, str(_SRC))

from person import Person  # noqa: E402
import cluster_map as cluster_map_module  # noqa: E402
import draw as draw_module  # noqa: E402
import graph_model as graph_model_module  # noqa: E402
import search as search_module  # noqa: E402
from view import render_cluster  # noqa: E402

OUT = _HERE.parent


def save(fig: plt.Figure, name: str) -> None:
    """Write the figure as PDF (for LaTeX) and PNG (for previews) next to this script."""
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def familie_demo() -> None:
    """The §1.3 demo family: one pedigree-collapse cluster and one isolated person."""
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


def diamond_chain(depth: int) -> Person:
    """Diamond chain D_k of §4.3: a_i -> {b_i, c_i} -> a_{i+1} (pedigree collapse I3)."""
    tip = Person("a0")
    for i in range(depth):
        b_i = Person(f"b{i}", mom=tip)
        c_i = Person(f"c{i}", mom=tip)
        tip = Person(f"a{i + 1}", mom=b_i, dad=c_i)
    return tip


def pedigree_collapse() -> None:
    """|Anc| for D_k (k = 1..12) vs the naive binary bound at the same generation height."""
    ks = list(range(1, 13))
    actual = []
    for k in ks:
        tip = diamond_chain(k)
        actual.append(len(search_module.ancestors_iterative(tip)))
    heights = [2 * k for k in ks]  # D_k is 2k generations tall
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
    """Random persons with deg-in <= 2 (invariant I1), parents always earlier in the list."""
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
    """Wall time of the cluster-map construction vs n, with a linear fit (§8.5)."""
    sizes = [500, 1000, 2000, 5000, 10000, 20000]
    times = []
    for n in sizes:
        people = random_population(random.Random(n), n)
        graph = __import__("graph_model").build_family_graph(people)
        best = float("inf")
        for _ in range(5):
            start = time.perf_counter()
            cluster_map_module.build_cluster_map_dfs(graph)
            best = min(best, time.perf_counter() - start)
        times.append(best)

    ns = np.array(sizes, dtype=float)
    ts = np.array(times) * 1e6  # microseconds
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
    pedigree_collapse()
    scaling()
    print("figures written to", OUT)
