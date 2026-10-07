# Herritage Tree — Fælles aner

Skoleprojekt til afsnit 7.10 ("Projekt: Fælles aner"): en familie modelleres som en
graf, hvor hver person er en knude, og hver forældreference (`mom`/`dad`) er en kant
fra forælder til barn. Programmet opdeler befolkningen i klynger (personer der hænger
sammen via forældre- og børneforbindelser), søger i klyngerne, besvarer spørgsmålet
"Har to personer mindst en fælles ane?", og tegner ét stamtræ pr. klynge.

Synopsen med kravdokumentation ligger i `synopsis/synopsis.pdf`; figurene i synopsen
genereres af `synopsis/figurer/make_figures.py`.

## Installering og kørsel

Kræver Python 3.12+ og Poetry.

```bash
git clone https://github.com/ExperiencesXP/proj_herritage_tree.git && cd proj_herritage_tree
poetry install
poetry run python src
```

(`poetry env activate | iex` først, hvis venv'en skal være aktiv på PowerShell-prompten
— det er ikke nødvendigt, `poetry run` klarer det. Ækvivalente måder at starte på:
`poetry run python -m src` og `poetry run python src/__main__.py`.)

Programmet kører hele pipeline på demo-familien — indeks → klusterkort → søgning →
lagdelt layout → Mermaid/Graphviz-eksport → **matplotlib-figurer** i
`out/cluster_<id>.png` (projektets krav om visualisering) — og besvarer
slægtskabsspørgsmålet fra 7.10 via `is_related()` og `find_common_ancestor()`.
Udskriften viser bl.a. de fælles aner for to personer, og om en person fra én familie
er beslægtet med en fra en anden.

## Tests

```bash
poetry run pytest
```

25 tests fastholder verifikationsplanen: klusterkort sammenlignes med en uafhængig
bredde-først-reference, antallet af klynger er personer minus sammenlægninger, dybe
kæder klarer de iterative traverseringer, cyklusser afvises, skaleringen er
nær-lineær, og 7.10-spørgsmålene (`find_common_ancestor`, `is_related`) giver de
forventede svar.

## Arkitektur (MVC)

Modellen ligger i pakken `src/models/` og importeres som `models.person`,
`models.search`, … . Koden er bevidst uden kommentarer og docstrings; dokumentationen
står her og i synopsen (`synopsis/`). Koden er skrevet på engelsk — attributterne
`name`, `mom`, `dad` svarer til klassediagrammets `navn`, `mor`, `far`. Standardnavnet
på en person følger stedordene: `John Doe` ved han-ord, `Jane Doe` ved hun-ord,
`Alex Doe` ved de-ord og `An Other` ellers.

| Lag | Moduler | Rolle |
|---|---|---|
| Model | `src/models/` (`person`, `graph_model`, `cluster_map`, `search`) | data (`Person`, `FamilyGraph`) og algoritmer (klusterkort, rekursiv søgning, fælles aner) |
| View | `src/draw.py`, `src/view.py` | lagdelt Sugiyama-layout, Mermaid/Graphviz-uddrag, matplotlib-figurer |
| Controller | `src/controller.py`, `src/__main__.py` | `FamilyController`-facade og indgangspunktet der kører pipeline |
