from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from models.cluster_map import Cluster, ClusterMap
from draw import Layout, layout_cluster_map

__all__ = ["render_cluster", "render_cluster_map"]

X_GAP = 1.4
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
    members = tuple(sorted(cluster.members, key=lambda p: p.name))
    hot = set(highlight)
    fresh = ax is None
    if fresh:
        max_rank = max(layout.ranks.values(), default=0)
        width = 2.0 + X_GAP * (
            1 + max((len(layer) for layer in layout.layers), default=1)
        )
        height = 2.0 + 1.2 * (1 + max_rank)
        _, ax = plt.subplots(figsize=(width, height))
    assert ax is not None

    for child, parent in cluster.edges:
        ax.annotate(
            "",
            xy=(layout.x[child] * X_GAP, layout.ranks[child]),
            xytext=(layout.x[parent] * X_GAP, layout.ranks[parent]),
            arrowprops={
                "arrowstyle": "->",
                "color": EDGE_COLOR,
                "lw": 1.2,
                "shrinkA": 10,
                "shrinkB": 10,
            },
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

    unit = "person" if len(cluster) == 1 else "persons"
    ax.set_title(title or f"Cluster {cluster.id} ({len(cluster)} {unit})", fontsize=10)
    ax.set_xlabel("position within generation layer (barycentre order, §6)")
    ax.set_ylabel("generation rank (rank 0 = no known parents)")
    xs = [layout.x[p] * X_GAP for p in members]
    ys = [layout.ranks[p] for p in members]
    pad = 0.7
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(max(ys) + pad, min(ys) - pad)
    ax.set_xticks([])
    ax.set_yticks(sorted(set(layout.ranks.values())))
    if fresh and hasattr(ax.figure, "tight_layout"):
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
