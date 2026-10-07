# Noter til synopsen "Fælles aner"

Arbejdsnoter til at skrive synopsen (skal være dansk, PDF, maks. 5 normalsider +
bilag). Det samlede dokument ligger klar som [`synopsis.tex`](synopsis.tex) →
`synopsis.pdf` (forblad + synopsis + bilag A–F, 14 sider; brødteksten fylder
under 5 normalsider).

## Opgavens krav (Projekt.docx) — status

| Krav | Status |
|---|---|
| Python-program, min. kravene i afsnit 7.10 | opfyldt: se tjeklisten nedenfor |
| Visualisering med `matplotlib.pyplot` | opfyldt: `src/view.py`, figurer i `out/` |
| MVC-arkitektur | opfyldt: Model (`model.person`, `model.graph_model`, `model.cluster_map`, `model.search` — pakken `src/model/`), View (`draw`, `view`), Controller (`controller`, `__main__`) |
| Synopsis i PDF, beskriver udvikling + færdigt program | opfyldt: `synopsis.pdf` (afsnit 1–5 + bilag) |
| Git anvendt til arbejdet | opfyldt: commits fra 28/9, se bilag D |
| Skærmdump: Git Graph + commits med datoer | **mangler** — manuelle trin nedenfor |
| Link til projektets kode (fx GitHub) | repoet er privat, se Åbne punkter |

## Afsnit 7.10: kravene fra bogen — afkrydset

Kilde: *Kapitel 7 Objektorienteret programmering* (Kathrine Bohus Madsen & Henrik
Sterner), "7.10 Projekt: Fælles aner", side 162–163. Bogen stiller spørgsmålet:
*"Har to personer mindst en fælles ane?"* Kravene vs. koden:

| Krav (bogens ordlyd) | Status i koden |
|---|---|
| Program der kan undersøge slægtskab: "Har to personer mindst en fælles ane?" | ✅ `is_related()` + `find_common_ancestor()` (`src/model/search.py`), via controlleren |
| "Vi antager at en person kan have en far og en mor" | ✅ `Person(mom, dad)` — begge valgfrie (`None`) |
| Implementer klassen `Person` fra klassediagrammet (`navn`, `mor`, `far`) | ✅ `name`, `mom`, `dad` + ekstra `pronouns` (engelske navne — se note) |
| Opret nogle personer og forbind dem | ✅ demo-population + `build_family_graph` |
| "Hvilken type relation er der tale om?" | ✅ svaret nedenfor — skal med i synopsen |
| `__str__()` "noget i stil med 'Navn Nikolaj, mors navn er Anne og fars navn er Peter'" | ✅ "nikolaj's mother is anne and father is peter." (engelsk ækvivalent) |
| "Test at dundermetoden virker efter hensigten" | ✅ `test_person_dunder_str_matches_book_style` + `test_str_names_the_unknown_parent_slot` |
| "Opret en stor familie med mindst tre generationer" | ✅ `stor_familie`-figuren (14 personer, 4 generationer) + tests op til 20.000 |
| "Tegn et stamtræ over den familie" | ✅ `view.render_cluster` (matplotlib) — `figurer/stor_familie.pdf` |
| `find_common_ancestor()` → liste over fælles aner (evt tom) | ✅ `search.find_common_ancestor()` |
| `is_related()` → `True` hvis de har en fælles ane | ✅ `search.is_related()` |

**Svar til "Hvilken type relation er der tale om?":** forbindelsen mellem
`Person`-objekterne er en **assosiation** — mere præcist **aggregering** ("har
en"-relation): et `Person`-objekt har referencer til andre `Person`-objekter som
mor/far; objekterne eksisterer uafhængigt af hinanden (barnet "ejer" ikke sine
forældre), relationen er valgfri (`None`), og den er *refleksiv* — samme klasse i
begge ender. Det er ikke nedarvning. (Bogens klassediagram bruger `navn`, `mor`,
`far`; koden bruger engelske `name`, `mom`, `dad` og har ekstra attribut
`pronouns`. Nævn forskellen i dokumentationen, eller omdøb hvis læreren vil have
bogstavelig overensstemmelse.)

**Definition-valg værd at nævne:** spørgsmålet er "*mindst* en fælles ane". I koden
tæller Anc(v) også personen selv (design §2.5), så forælder/barn regnes som
beslægtede — ellers ville `is_related(ada, kid)` give `False`, hvilket er åbenlyst
forkert. To søskende deler forældrene; to fætre deler bedsteforældrene; fremmede
giver tom liste. Eksempel i stor-familie-figuren: `find_common_ancestor(anders,
line) = [else, ole]` (forældrenes søskendepar), `is_related(emma, pia) = True`.

**Beslutning:** koden forbliver **engelsk** (`name`, `mom`, `dad` — ingen
omdøbning til `navn`/`mor`/`far`). Synopsen dokumenterer mappingen til bogens
klassediagram i stedet (se bilag F).

## Forslag til indhold pr. afsnit

1. **Forblad** — titel, projektdeltagere, klasse, dato. Mangler: rigtige navne
   (pyproject har kun GitHub-navne: Experiences, Blockgameentity, Lufnin), klasse
   (bekræft 3.O for alle), afleveringsdato.
2. **Projektbeskrivelse** — "Fælles aner": en stamtavle som graf, hvor personer er
   knuder og forældreferencer er kanter. To kerneidéer: (a) opdel befolkningen i
   *klynger* (sammenhængende komponenter — familier der hænger sammen), (b) find alle
   medlemmer af en klynge rekursivt og tegn et kort pr. klynge. Matematikken:
   kompleksitet $\Theta(n)$ fordi $m \le 2n$ (invariant I1), identitet (3)
   $k = n - s$, og pedigree-collapse (I3) der bryder "2 forfædre pr. generation".
3. **Funktionsbeskrivelse** — hvad programmet gør, brugerens synsvinkel:
   indlæs population → byg klusterkort → søg (klustermedlemmer, forfædre,
   efterkommere, målrettet søgning med tidligt stop, **slægtskabsspørgsmålet
   "har de en fælles ane?"**) → tegn kort (lagdelt layout, færrest mulige
   krydsende kanter) → eksportér Mermaid/Graphviz-uddrag + PNG-figurer.
   Kørsel: `poetry run python src`. Brug demo-familien (figur `familie_demo.pdf`)
   som eksempel gennem afsnittet, og stor-familien (`stor_familie.pdf`) som det
   udfyldte 7.10-eksempel.
4. **Dokumentation af programmet** — overordnet: MVC-tabellen (bilag A) + pipeline
   (index → kort → søgning → layout → eksport). Detaljeret: bilag B1–B8 dækker
   datamodel (B1), grafrepræsentation (B2), rekursiv søgning som mindste faste punkt
   (B3), Union-Find + identitet (3) (B4), memoisering (B5), Sugiyama-layout (B6),
   matplotlib-view (B7), fælles aner/slægtskab (B8). OOP-principper at nævne:
   klasse/instans (`Person`, `UnionFind`, `FamilyGraph`), indkapsling (state bag
   `FamilyController`-metoder), immutabilitet (`@dataclass(frozen=True)`,
   `__slots__`), specialmetoder (`__str__`, `__len__`), klassevariabler
   (`Pronouns.PRESETS`), egenskaber (`@property`), nedarvning er bevidst *ikke*
   brugt — composition i stedet. Kompleksitetstabel: design-dokumentet §4.4
   (kan kopieres).
5. **Udviklingsproces** — design-dokumentet skrevet først
   (`docs/cluster_map_and_recursive_search.md`, 528 linjer med beviser og
   kompleksitetsanalyse), derefter implementering i trin (datamodel → graf →
   søgning → klusterkort → layout → view), tests undervejs (23 stk.), og et
   review der fandt og rettede 4 fejl (se nedenfor). Commit-tabellen ligger i
   bilag D. Husk at nævne arbejdsfordelingen i gruppen.

## Fakta og tal (kan citeres direkte)

- **Tests:** `poetry run pytest` → 25 passed, 0 fejl (7. okt. 2026).
- **Demo-eksempel:** $n = 5$ personer, $m = 4$ forældreferencer, $s = 3$
  vellykkede sammenlægninger, $k = 2$ klynger — identitet (3): $k = n - s = 2$.
- **Stor-familie (7.10):** 14 personer, 4 generationer, 1 klynge; fælles aner for
  `anders` og `line` = {`else`, `ole`} (pedigree-collapse på deres børn).
- **Målt skalering** (i7-11700KF, bedst af 5, klusterkort med DFS): 500 → 1,0 ms,
  1.000 → 2,1 ms, 2.000 → 4,4 ms, 5.000 → 12,2 ms, 10.000 → 25,3 ms,
  20.000 → 59,0 ms; fit $t(n) \approx 2{,}8\text{–}3{,}0\ \mu s \cdot n$
  (figur `scaling.pdf`).
- **Pedigree-collapse:** diamantkæde $D_k$: $|\mathrm{Anc}(v_k)| = 3k+1$ mod den
  binære grænse $2^{2k+1}-1$ (figur `pedigree_collapse.pdf`; ved $k=12$: 37 mod
  33.554.431).
- **Kompleksitet:** klusterkort $\Theta(n+m)=\Theta(n)$ tid og plads;
  memoiseret forfædre-udregning $\Theta(n+m)$; Union-Find $O(m\,\alpha(m,n))$
  (praktisk $O(m)$, $\alpha \le 5$); 3-farve cyklustjek $O(n+m)$.
- **Git:** commits på `dev`, 2026-09-28 → 2026-10-07 (bilag D har tabellen;
  `git log --oneline` giver den aktuelle liste).
- **Reviewet fandt 4 fejl** (alle rettet med regressionstests):
  1. `Person.__str__` nævnte den forkerte forældre-slot som ukendt
     ("mother is ada and no known mother").
  2. `build_cluster_map_pairs` vendte pilretningen i eksporter (barn → forælder
     tegnet som forælder → barn).
  3. `find_with_early_exit` brugte 3-farve-cyklusvagten på den udretningsløse
     skygge, hvor hver kant dobbelt-tilbage rapporteres som cyklus — målsøgning
     efter en fraværende person rejste `CycleError` i stedet for at returnere
     "ikke fundet".
  4. `ancestors`/`validate_acyclic` kunne ikke klare dybe kæder (RecursionError
     ved >1000) — løst med `ancestors_iterative` (O5).

## De to skærmdump — manuelle trin

1. **Git Graph:** Åbn `proj_herritage_tree` i VS Code. Installér udvidelsen
   *Git Graph* (mhutchie.git-graph) hvis den mangler (Extensions → søg
   "Git Graph" → Install). Tryk Ctrl+Shift+P → "Git Graph: View Git Graph".
   Tag skærmdump med `dev`-grenen og alle commits synlige.
2. **Commits med datoer:** browser (logget ind på GitHub) →
   <https://github.com/ExperiencesXP/proj_herritage_tree/commits/dev> →
   tag skærmdump. Alternativt: Git Graph med datoer (⋮ → Settings →
   "Show Date" eller højreklik kolonneoverskrift).

Gem begge PNG'er i `synopsis/figurer/` og erstat de to rammer nederst i
`synopsis.tex` (bilag D) med `\includegraphics`.

## Figurer

| Fil | Bruges til | Genereret af |
|---|---|---|
| `figurer/familie_demo.pdf` | funktionsbeskrivelse / visualisering | `make_figures.py` (`view.render_cluster`) |
| `figurer/stor_familie.pdf` | 7.10's "store familie" / stamtræ | `make_figures.py` (via `FamilyController`) |
| `figurer/pedigree_collapse.pdf` | dokumentation (matematik, I3) | `make_figures.py` (`search.ancestors_iterative`) |
| `figurer/scaling.pdf` | verifikation (kompleksitet, §8.5) | `make_figures.py` (målt køretid) |

Generér på ny: `poetry run python synopsis/figurer/make_figures.py`.
PNG-kopier ligger ved siden af (til preview/README).

## Åbne punkter / mangler

- **Forblad:** navne, klasse og dato skal ind.
- **Repoet er privat:** synopsen skal ifølge opgaven indeholde et *link* til
  koden — giv læreren adgang (GitHub → Settings → Collaborators) eller vedhæft
  koden som kodebilag i stedet.
- `synopsis.tex` er et udkast: forbladets navne/dato og de to skærmdump-rammer
  skal fyldes. Koden er renset for kommentarer og docstrings (okt. 2026), så
  forklaringerne ligger i prose rundt om kodeuddragene — præcis som bilag B1–B8
  er bygget.
- Overvej om Mermaid-uddragene skal vises som renderede diagrammer i bilaget
  (kan renderes på GitHub/i VS Code-udvidelsen Mermaid).
