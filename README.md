# Herritage Tree

Family-tree project ("Fælles aner"): model a `Person` pedigree as a graph, partition it
into clusters (connected components of the undirected parent shadow), search the clusters
recursively, and draw one map per cluster.

Design and analysis are described in the synopsis (`synopsis/synopsis.pdf`).

## Installing and running

```bash
git clone https://github.com/ExperiencesXP/proj_herritage_tree.git && cd proj_herritage_tree
poetry install
poetry run python src
```

(`poetry env activate | iex` first if you want the venv on your PowerShell prompt — not
required, `poetry run` handles it. Equivalent launch modes: `poetry run python -m src`
and `poetry run python src/__main__.py`.)

The entry point runs the whole pipeline over the demo family — index -> cluster map ->
search -> layered layout -> Mermaid/Graphviz export -> **matplotlib figures**, written to
`out/cluster_<id>.png` (the visualisation required by the project assignment), and answers
the assignment's kinship question from section 7.10 via `is_related()` and
`find_common_ancestor()`.

## Tests

```bash
poetry run pytest
```

The suite pins the project's verification plan: cluster maps agree with an
independent BFS reference, the cluster count equals persons minus merges, deep chains survive the
iterative traversals, cycles are flagged, the scaling is near-linear, and the 7.10
kinship queries (`find_common_ancestor`, `is_related`) return the expected answers.

## Architecture (MVC)

The model layer lives in the `src/models/` package and is imported as `models.person`,
`models.search`, … . The source is deliberately free of comments and docstrings; this
README and the synopsis (`synopsis/`) carry the documentation.

| Layer | Modules | Role |
|---|---|---|
| Model | `models/person.py`, `models/graph_model.py`, `models/cluster_map.py`, `models/search.py` (the `models` package) | data (`Person`, `FamilyGraph`) and algorithms (cluster map, recursive search) |
| View | `draw.py`, `view.py` | layered Sugiyama layout, Mermaid/Graphviz fragments, matplotlib figures |
| Controller | `controller.py`, `__main__.py` | `FamilyController` facade + entry point that drives the pipeline |
