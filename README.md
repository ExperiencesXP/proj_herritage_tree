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
