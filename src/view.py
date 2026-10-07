"""Matplotlib visualisation of the family clusters — the **View** of the MVC architecture.

`Projekt.docx` requires the product to visualise with ``matplotlib.pyplot``; this module
renders the layered layouts of `draw.py` (§6) as figures: one box per person at its
layout position (within-layer index × horizontal gap, generation rank vertically) and one
arrow per parental edge, parent → child — the same orientation as :func:`draw.to_mermaid`
and :func:`draw.to_dot`.

Layering rule (MVC): the view receives finished values (:class:`cluster_map.Cluster` +
:class:`draw.Layout`) and renders them.  It never runs a search or builds a map, and no
model module imports it — data flows model → controller → view, never back.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from cluster_map import Cluster, ClusterMap
from draw import Layout, layout_cluster_map

__all__ = ["render_cluster", "render_cluster_map"]

X_GAP = 1.4  # horizontal display gap between within-layer positions
NODE_STYLE = {
    "boxstyle": "round,pad=0.3",
    "facecolor": "#dae8ff",
    "edgecolor": "#4a6785",
    "linewidth": 1.2,
}
HIGHLIGHT_STYLE = {
    "boxstyle": "round,pad=0.3",
    "facecolor": "#ffe6b3",
    "edgecolor": "#c77f0a",
    "linewidth": 1.8,
}
EDGE_COLOR = "#6b7d94"


def render_cluster(
    cluster: Cluster,
    layout: Layout,
    *,
    ax: Axes | None = None,
    highlight: Iterable[Any] = (),
    label: Callable[[Any], str] = lambda p: p.name,
    title: str | None = None,
) -> Axes:
    """Draw one cluster map ``H_i = G[C_i]`` (§1.3) onto ``ax`` (a fresh figure if None).

    ``highlight`` marks the persons a query is about (e.g. a search hit) in a second
    colour; everything else keeps the default node style.  The y axis is inverted so
    rank 0 (persons without parents) sits at the top — the conventional pedigree
    orientation, matching ``flowchart TB`` in the Mermaid export.
    """
    members = tuple(sorted(cluster.members, key=lambda p: p.name))
    hot = set(highlight)
    fresh = ax is None
    if fresh:
        max_rank = max(layout.ranks.values(), default=0)
        width = 2.0 + X_GAP * (1 + max((len(layer) for layer in layout.layers), default=1))
        height = 2.0 + 1.2 * (1 + max_rank)
        _, ax = plt.subplots(figsize=(width, height))
    assert ax is not None

    # arrows first so the node boxes cover their ends
    for child, parent in cluster.edges:  # (child, parent) per §1.1
        ax.annotate(
            "",
            xy=(layout.x[child] * X_GAP, layout.ranks[child]),
            xytext=(layout.x[parent] * X_GAP, layout.ranks[parent]),
            arrowprops={"arrowstyle": "->", "color": EDGE_COLOR, "lw": 1.2,
                        "shrinkA": 10, "shrinkB": 10},
        )
    for person in members:
        ax.text(
            layout.x[person] * X_GAP,
            layout.ranks[person],
            label(person),
            ha="center",
            va="center",
            fontsize=9,
            bbox=HIGHLIGHT_STYLE if person in hot else NODE_STYLE,
        )

    ax.set_title(title or f"Cluster {cluster.id} ({len(cluster)} persons)", fontsize=10)
    ax.set_xlabel("position within generation layer (barycentre order, §6)")
    ax.set_ylabel("generation rank (rank 0 = no known parents)")
    # text artists do not feed autoscale, so the extents are set explicitly:
    # rank 0 (no known parents) at the top = the conventional TB pedigree orientation
    xs = [layout.x[p] * X_GAP for p in members]
    ys = [layout.ranks[p] for p in members]
    pad = 0.7
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(max(ys) + pad, min(ys) - pad)
    ax.set_xticks([])
    ax.set_yticks(sorted(set(layout.ranks.values())))
    if fresh:
        ax.figure.tight_layout()
    return ax


def render_cluster_map(
    cluster_map: ClusterMap,
    layouts: tuple[Layout, ...] | None = None,
    *,
    out_dir: str | Path = "out",
    fmt: str = "png",
    dpi: int = 150,
    show: bool = False,
    highlight: Iterable[Any] = (),
    prefix: str = "cluster",
) -> tuple[Path, ...]:
    """Render every cluster to ``out_dir/<prefix>_<id>.<fmt>`` and return the file paths.

    With ``show=True`` the figures are additionally raised in interactive windows
    (``plt.show()``); otherwise they are only written, which keeps the pipeline
    deterministic and usable on a headless run.  Clusters are drawn from the same
    layouts the export stage uses (O9), so the figures and the Mermaid/Graphviz
    fragments always agree.
    """
    if layouts is None:
        layouts = layout_cluster_map(cluster_map)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    hot = set(highlight)
    written: list[Path] = []
    for cluster, layout in zip(cluster_map.clusters, layouts):
        render_cluster(cluster, layout, highlight=hot)
        path = out / f"{prefix}_{cluster.id}.{fmt}"
        plt.savefig(path, dpi=dpi, bbox_inches="tight")
        written.append(path)
    if show:
        plt.show()
    else:
        plt.close("all")
    return tuple(written)
