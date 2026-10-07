# Herritage Tree

Family-tree project ("Fælles aner"): model a `Person` pedigree as a graph, partition it
into clusters (connected components of the undirected parent shadow), search the clusters
recursively, and draw one map per cluster.

Design and analysis: [docs/cluster_map_and_recursive_search.md](docs/cluster_map_and_recursive_search.md).

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

The suite pins the verification plan of the design doc (§8): cluster maps agree with an
independent BFS reference, identity (3) `k = n − s` holds, deep chains survive the
iterative traversals, cycles are flagged, the scaling is near-linear, and the 7.10
kinship queries (`find_common_ancestor`, `is_related`) return the expected answers.

## Architecture (MVC)

| Layer | Modules | Role |
|---|---|---|
| Model | `person.py`, `graph_model.py`, `cluster_map.py`, `search.py` | data (`Person`, `FamilyGraph`) and algorithms (cluster map, recursive search) |
| View | `draw.py`, `view.py` | layered Sugiyama layout, Mermaid/Graphviz fragments, matplotlib figures |
| Controller | `controller.py`, `__main__.py` | `FamilyController` facade + entry point that drives the pipeline |
