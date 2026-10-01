# Cluster Map & Recursive Search over Family Graphs — Design & Analysis

**Scope.** Model the family tree implied by [`src/main.py`](../src/main.py) as a graph in which every
`Person` is a node and every parental connection (`mom`, `dad`) is an edge. Derive an algorithm that
(a) partitions the graph into *clusters* (connected components), (b) draws a map over each cluster,
and (c) finds all members of a cluster recursively. This document specifies the model, the algorithm,
its correctness proof, its asymptotic cost with formulas, and the design trade-offs behind every
optimization.

> Notation used throughout: $n = |V|$ (persons), $m = |E|$ (parental edges), $k$ = number of
> clusters, $d$ = recursion depth / height of the traversal, $b$ = branching factor.

---

## 1. Graph model

### 1.1 From `Person` to a graph

The existing `Person` class stores `mom: Person | None` and `dad: Person | None`. These fields are
nothing but *two incoming edges per node*:

$$
V = \{\,p \mid p \text{ is a } \texttt{Person}\,\},\qquad
E = \{\,(p, m),\,(p, d) \mid p.\texttt{mom} = m,\ p.\texttt{dad} = d\,\}.
$$

$E$ is oriented **child → parent**. The transposed orientation (parent → child) is equally valid and
is obtained by $E^{\top} = \{ (u,v) : (v,u)\in E \}$. All analysis below is orientation-insensitive
because cluster membership only uses the *underlying undirected graph*:

$$
\bar G = \bigl(V,\ \bar E\bigr),\qquad
\bar E = \bigl\{\,\{u,v\} : (u,v) \in E \cup E^{\top}\,\bigr\}.
$$

### 1.2 Structural invariants

**I1 (Bounded parental in-degree).** A person has at most one mother and one father, so
$\deg^{-}(v) \le 2$ for every $v$. Consequently

$$
m \;=\; \sum_{v\in V} \deg^{-}(v) \;\le\; 2n \;=\; O(n). \tag{1}
$$

This single fact is the reason *every* traversal below is linear in $n$: the sparsest realistic
family graph is not $O(n^2)$ but $O(n)$ in edges. Any algorithm that costs $O(n+m)$ therefore costs
$\Theta(n)$ here.

**I2 (Acyclicity, as a data-quality invariant).** In a biologically consistent record,

$$
\text{the parent relation is acyclic} \iff G \text{ is a DAG} \iff \nexists\, v : v \xrightarrow{+} v.
$$

The algorithm must not *assume* I2 silently — a corrupt record can contain a cycle (a person listed
as their own ancestor). Cycle detection is built in (Section 3.4) so the data problem surfaces as a
diagnostic instead of as infinite recursion.

**I3 (Pedigree collapse is allowed).** Two parents may share an ancestor. This makes $G$ a genuine
*lattice-shaped DAG*, not a tree. Any algorithm that assumes "number of ancestors at generation $g$
equals $2^g$" is wrong here; the correct bound is

$$
|A_g(v)| \;\le\; 2^{g}, \qquad
\bigl|A(v)\bigr| \;\le\; \sum_{g\ge 0} 2^{g} = 2^{G+1} - 1,
$$

with strict inequality whenever collapse occurs. Memoized recursion handles this automatically;
naive recursion does not (Section 4.3).

### 1.3 Clusters: the equivalence closure

Define reachability in $\bar G$: $u \sim v$ iff there is a path $u = w_0, w_1, \dots, w_k = v$ in
$\bar G$. This is reflexive, symmetric and transitive, hence an equivalence relation (Section 3.1
proves the recursion computes exactly its classes). The partition is

$$
\Pi = V/{\sim} \;=\; \{C_1, C_2, \dots, C_k\},\qquad
V = \bigsqcup_{i=1}^{k} C_i, \qquad
E = \bigsqcup_{i=1}^{k} E(C_i).
$$

(Edges never cross clusters — that is *why* a cluster is a cluster.) The **cluster map** is the
function

$$
\texttt{clusterId} : V \to \{1,\dots,k\},\qquad v \mapsto i \iff v \in C_i,
$$

and each cluster additionally carries a *map* (its induced subgraph) for drawing:

$$
H_i = G[C_i] = \bigl(C_i,\ \{(u,v)\in E : u,v \in C_i\}\bigr).
$$

### 1.4 Data types (design sketch, compatible with `src/main.py`)

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Cluster:
    id: int
    members: frozenset["Person"]        # |members| = |C_i|
    edges: tuple[tuple["Person", "Person"], ...]   # E(C_i)

@dataclass(frozen=True)
class ClusterMap:
    # clusterId: V -> {1..k};  Implemented as a dict for O(1) lookup.
    owner: dict["Person", int]
    clusters: tuple[Cluster, ...]

    def members_of(self, p: "Person") -> frozenset["Person"]:
        return self.clusters[self.owner[p] - 1].members
```

Note the deliberate backward compatibility: `Person.mom` / `Person.dad` are read directly into
edges; `Pronouns` and `__str__` play no role in the graph and are left untouched.

---

## 2. Recursive search

### 2.1 What "recursively find all" must compute

For a seed node $v$, the members of its cluster are the *least fixed point* of the monotone
operator

$$
\Phi_v : 2^{V} \to 2^{V},\qquad
\Phi_v(S) \;=\; \{v\} \cup \bigcup_{\{u,w\} \in \bar E,\ u \in S} \{w\}.
$$

By the **Knaster–Tarski theorem** applied to the complete lattice $(2^V, \subseteq)$, this monotone
map has a least fixed point

$$
\mathrm{reach}(v) \;=\; \mathrm{lfp}(\Phi_v) \;=\; \bigcup_{i\ge 0} \Phi_v^{\,i}(\varnothing),
$$

and this is precisely the *connected component* $C_i \ni v$. A depth-first recursion separated by a
`visited` guard computes exactly this fixed point, because each recursive call expands the frontier
by one layer of $\Phi$ and the guard prevents re-expansion (proof in Section 3.2).

### 2.2 Core algorithm — plain DFS with a visited guard

```python
def explore(v, visited: set, members: list) -> None:
    if v in visited:            # guard = fixed-point stabilisation
        return
    visited.add(v)
    members.append(v)
    for w in (v.mom, v.dad, *child_index.get(v, ())):   # neighbours in G̅
        if w is not None:
            explore(w, visited, members)
```

Complexity: each node is added to `visited` **once**, and each undirected edge is examined **at most
twice** (once from each endpoint). Hence

$$
T(n,m) = \Theta(n + m) \overset{(1)}{=} \Theta(n), \qquad S(n) = \Theta(n). \tag{2}
$$

The parent-only part ($\deg^- \le 2$) can be traversed without any lookup table; the *child*
direction needs a reverse index `child_index: dict[Person, list[Person]]` built in one $O(n)$
pre-pass, and this index is what makes the traversal full-sided instead of ancestors-only.

### 2.3 Cluster map construction — two equivalent designs

**(a) DFS-with-components.** For each as-yet-unvisited node, run `explore` and label all discovered
nodes with a fresh cluster id. Correctness follows from Section 3.2; cost is $O(n+m)$.

**(b) Union-Find (Disjoint Set Union).** Process each edge $\{u,v\}$ in $\bar E$ as `union(u, v)`;
afterwards, nodes with equal *find* representatives belong to the same cluster. Design choice: **(b)
is chosen for the incremental case** (edges arriving from file/stream, e.g. importing records one
person at a time), because it adds new edges in near-constant amortised time without rebuilding
adjacency lists. Formula for the number of clusters (proved in Section 3.3):

$$
\boxed{\,k = n - s\,} \tag{3}
$$

with $s$ the number of *successful* `union` operations (the ones that actually merged two distinct
sets). This gives an $O(1)$ cluster count after the merges, no traversal needed.

### 2.4 Full pseudocode (Union-Find + per-cluster extraction)

```python
def cluster_map(persons):
    idx = {p: i for i, p in enumerate(persons)}            # dense ids 0..n-1
    parent = list(range(len(persons)))
    rank   = [0] * len(persons)

    def find(x):                                           # path compression
        while parent[x] != x:
            parent[x] = parent[parent[x]]                  # halving
            x = parent[x]
        return x

    def union(a, b):                                       # union by rank
        ra, rb = find(a), find(b)
        if ra == rb: return False
        if rank[ra] < rank[rb]: ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]: rank[ra] += 1
        return True

    s = 0
    for p in persons:
        for q in (p.mom, p.dad):
            if q is not None and union(idx[p], idx[q]):
                s += 1

    k = len(persons) - s                                   # eq. (3)
    # group nodes by representative once, in O(n):
    buckets: dict[int, list[Person]] = {}
    for p in persons:
        buckets.setdefault(find(idx[p]), []).append(p)
    return build_cluster_map(buckets)
```

### 2.5 Mutually recursive "find all relatives" (ancestor closure)

The *ancestral* query — "give me every ancestor of $v$ and every descendant" — is naturally recursive
over parents. If pedigree collapse is present the raw form is exponential (Section 4.3), so it
**must** be memoised:

$$
\mathrm{Anc}(v) = \{v\} \cup \mathrm{Anc}(\mathrm{mom}(v)) \cup \mathrm{Anc}(\mathrm{dad}(v)),
\quad \mathrm{Anc}(\varnothing) = \varnothing.
$$

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def ancestors(p: Person | None) -> frozenset[Person]:
    if p is None:
        return frozenset()
    out = {p} | set(ancestors(p.mom)) | set(ancestors(p.dad))
    return frozenset(out)
```

Each node becomes a cache *hit* after its first computation, so the total work is

$$
T_{\text{anc}} = \sum_{v \in V}\bigl(1 + \deg^{-}(v)\bigr) = O(n+m) = O(n),
\qquad S = O(n) \text{ (cached sets)}.
$$

(The set-union cost is $O(1)$ per element for hash-set chunks; a bitset over dense ids reduces it to
one machine word per element if $n$ is large.)

### 2.6 Cycle guard (BFS/DFS 3-coloring) — required by I2

If any cycle can appear, track the classic three colours:
$\texttt{WHITE}$ = undiscovered, $\texttt{GRAY}$ = on the recursion stack, $\texttt{BLACK}$ = fully
explored. A back edge $u \to v$ with $v$ `GRAY` implies a cycle. Cost: one byte per node, i.e. $O(n)$
extra space and zero extra asymptotic time — the visited set already existed and is simply split
into two states.

```python
GRAY, BLACK = 1, 2
color = {}                       # absent => WHITE

def explore_safe(v):
    st = color.get(v)
    if st == BLACK: return
    if st == GRAY:  raise ValueError("cycle in parental record")
    color[v] = GRAY
    for w in neighbours(v): explore_safe(w)
    color[v] = BLACK
```

---

## 3. Correctness

### 3.1 Lemma (fundamental DFS invariant)

Let $S_t$ be the set marked `visited` after $t$ recursive entries. Then for all $t$:

1. $S_t \subseteq \mathrm{reach}(v_0)$ (nothing foreign is ever marked);
2. $\Phi_{v_0}(S_t) \subseteq S_{t+1}$ (the frontier never shrinks and never stops covering one
   layer of $\Phi$).

*Proof.* (1) is by induction on $t$: the seed $v_0 \in \mathrm{reach}(v_0)$; and if $u \in
\mathrm{reach}(v_0)$ and $w$ is a neighbour of $u$ in $\bar G$, then $w \in \mathrm{reach}(v_0)$ by
definition of $\sim$. (2) is immediate from the loop over all neighbours before the return. $\square$

### 3.2 Theorem (recursion computes the whole cluster and nothing else)

For the seed $v_0$, `explore` terminates and, at termination,
$\texttt{members} = \mathrm{reach}(v_0) = C_i$.

*Proof.* By Lemma 3.1(2) and finiteness of $V$, the ascending chain of visited sets stabilises: at
some $t^\ast$, $S_{t^\ast} = S_{t^\ast+1}$ is a fixed point of $\Phi_{v_0}$ containing $v_0$;
therefore $\mathrm{reach}(v_0) \subseteq S_{t^\ast}$ (it is the *least* such fixed point). By
Lemma 3.1(1), $S_{t^\ast} \subseteq \mathrm{reach}(v_0)$. Both inclusions give equality. The guard
`if v in visited: return` guarantees termination because each node is added at most once:
$|S_t| = t$, so $t \le n$. $\square$

### 3.3 Theorem (cluster count formula $k = n - s$)

Let $s$ be the number of successful `union` operations during construction. Then $k = n - s$.

*Proof.* Induction over the $i$-th successful union. Initially $k_0 = n$ (each person alone). A
successful union merges exactly two disjoint components, decreasing the component count by exactly
one; a failing union does not. Therefore $k_i = n - i$, and after $s$ successes $k = n - s$.
Equivalently, $s = n - k = $ the number of edges of a spanning forest of $\bar G$ (a spanning forest
on $n$ vertices with $k$ components has exactly $n-k$ tree edges — this is the rank identity of the
cycle space of $\bar G$). $\square$

### 3.4 Theorem (cycle detection is complete)

3-colour DFS raises on every directed cycle of $G$ and never raises on a DAG.

*Proof (sketch).* In a DAG, fix a topological order; a DFS then only sees tree/cross/forward edges
by TRO — no grey back edges; hence no false positive. Conversely, if $G$ contains a directed cycle
$v_0 \to \dots \to v_j = v_0$, DFS from $v_0$ keeps all of the cycle's vertices grey until the closing
edge is examined (grey = descendant on the recursion stack) and raises. $\square$

---

## 4. Cost analysis

### 4.1 Cluster map: linear time, linear space

From (1) and (2),

$$
T_{\text{cluster}} = \Theta(n + m) = \Theta(n),\qquad S_{\text{cluster}} = \Theta(n).
$$

With Union-Find and both union-by-rank **and** path compression the bound is
$O(m\,\alpha(m,n))$ where $\alpha$ is the inverse Ackermann function (Tarjan 1975,
Tarjan–van Leeuwen 1984):

$$
\alpha(m,n) = \min\bigl\{\, i \ge 1 : A(i, \lceil 4m/n \rceil) > \lceil \log_2 n \rceil \,\bigr\},
$$

with Ackermann's function $A(1,j)=2j,\ A(i,0)=0,\ A(i,j)=A(i-1,A(i,j-1))$. Since $\alpha(2^{2^{2^{16}}})
\le 5$, the bound is *practically* $O(m)$ — the inverse Ackermann factor is an artefact of the
function's slow growth, not a measurable cost. Both designs are valid; see the table in
Section 5.

### 4.2 Recursion depth budget

Worst-case depth is $d = \Theta(n)$ (a single chain: every person has the previous one as mother).
CPython's default recursion limit is $R = 1000$ frames; each frame costs roughly 32–48 bytes plus
payload, so the stack cost grows linearly with $d$. Two safe formulas:

$$
\text{depth-safe: } d < R \quad\Longleftrightarrow\quad R \ge d_{\text{observed}} + \kappa,
\qquad \kappa \approx 100.
$$

**Design choice:** ship an iterative variant as the production path (explicit `list` stack / `deque`
for BFS; identical bound (2)) and keep the recursive variant for readable reference and testing.
The recursion-limit knob (`sys.setrecursionlimit`) is explicitly avoided — it trades
`RecursionError` for a `Segfault` risk on tiny stack budgets.

### 4.3 Why memoisation matters: the exponential blow-up

If the query enumerates *all paths* (rather than all *nodes*) — e.g. "all descent paths" or naive
counting recursion — the un-memoised cost obeys the path-counting recurrence

$$
P(v) = 1 + \sum_{(v,u) \in E} P(u).
$$

**Diamond chain family** $D_k$: layers $a_i \to \{b_i, c_i\} \to a_{i+1}$ give $P(k) = 2^{k}$, i.e.

$$
T = \Theta\bigl(2^{\,\lfloor d/2 \rfloor}\bigr).
$$

**Fibonacci pedigree** (each person links to their parent *and* to their grandparent, so the
*grandparent link* combines two branches) gives $P(k) = P(k-1) + P(k-2) + 1$, whose closed form is

$$
P(k) = \Theta(\varphi^{k}),\qquad \varphi = \frac{1+\sqrt{5}}{2} \approx 1.618.
$$

Either way: exponential in $d$, unusable for $n \gtrsim 40$. Memoisation turns the same recursion
into a DAG dynamic program: unroll subproblems in reverse topological order (topological order
computable in $O(n+m)$ since $G$ is a DAG by I2). With cache:

$$
T_{\text{memo}} = \Theta(n + m),\qquad S_{\text{memo}} = \Theta(n).
$$

*Proof sketch (potential method).* Give each uncached node potential $1$: a call either (a) hits the
cache and costs $O(1)$, or (b) is a fresh node and performs $1 + \deg^{-}(v)$ units of work while
consuming its own potential. Summing potential over $V$ bounds the number of case-(b) calls by $n$,
and $\sum_v \deg^{-}(v) = m$ bounds the loop work; total $O(n+m)$. $\square$

Counting *simple paths* is #P-hard in general DAGs — no closed-form polynomial exists — so the DP
above must count through unique nodes, never through paths.

### 4.4 Summary of the cost model

| Operation | Time | Space | Caveat |
|---|---|---|---|
| Cluster map (DFS + visited set) | $\Theta(n+m)=\Theta(n)$ | $\Theta(n)$ | needs `child_index` for descendants |
| Cluster map (Union-Find, path-halving + union-by-rank) | $O(m\,\alpha(m,n))\approx O(m)$ | $O(n)$ | best for streaming edge ingest |
| Cluster count $k = n - s$ | $O(1)$ after unions | $O(1)$ | identity (3), free after merges |
| `find all` with memoisation | $\Theta(n+m)$ | $\Theta(n)$ | correct with collapse (I3) |
| `find all` without memoisation | $\Theta(\varphi^{d})$ — $\Theta(2^{d/2})$ | $\exp$ | forbidden for $n \gtrsim 40$ |
| Cycle detection (3-colour) | $O(n+m)$ | $O(n)$ colors | guarantees I2 |
| Iterative deepening (early-exit search) | $O(b^{d})$ with factor $\tfrac{b}{b-1}$ | $O(b\,d)$ | use when goal may be shallow |

Everything above collapses into $\Theta(n)$ for real family data thanks to (1).

---

## 5. Optimizations and design choices

| # | Choice | Rationale / bound |
|---|---|---|
| O1 | Visited set (hash) on every traversal | Guarantees each node processed once; this alone is what removes the exponential blow-up. |
| O2 | Memoise recursive queries (`lru_cache`) | Converts path explosion to $O(n+m)$ (Theorem 4.3). Requires hashable nodes — use `frozen=True` dataclasses or a dense `id` table. |
| O3 | Union-Find with union-by-rank **+** path-halving | Amortised $O(\alpha(m,n))$ per merge; with I1 this is $O(1)$ in practice. |
| O4 | Dense index `id: dict[Person, int]` + arrays | Hash lookups are $O(1)$ but cache misses dominate Python; dense integer arrays (`array`/`__slots__`) cut memory by $5\times$ and make Union-Find trivially cacheable. |
| O5 | Iterative stack instead of recursion for deep chains | Recursion depth budget is $\Theta(n)$ (Section 4.2); Python's $R = 1000$ will crash before data does. |
| O6 | CSR adjacency (`offset[]`, `edges[]`) for big clusters | One contiguous block per cluster; layout and traversal become sequential scans, not pointer chasing. |
| O7 | Early-exit flag in *search* DFS (goal match) | Prunes the remaining branches: worst case unchanged, expected cost $\approx d \cdot \bar{b}$ instead of $n$ when the goal is early. |
| O8 | 3-colour guard instead of silent `visited` in `find all` | Data-integrity diagnostics; complete for I2 (Theorem 3.4). |
| O9 | Compute per-cluster layout *after* grouping | Layout $O(k)$ sweeps instead of rerunning connectivity per cluster (Section 6). |
| O10 | Bitset/word encoding of cached ancestor sets | Union of two ancestor sets becomes one `|V|/64`-word OR: $O(n/64)$ vs $O(|A|)$ hashing. |
| O11 | Iterative deepening when goal is a person/name | Space $O(d)$ instead of $O(n)$; only useful for early-exit search (table 4.4). |
| O12 | Thread-per-cluster map building (embarrassingly parallel) | Clusters are disjoint (no edges between them) — no locks, no synchronisation needed; $O(n/k)$ per worker (Amdahl: parallelism ~ perfect here). |

**Mandatory guardrails**

- The `child_index` table is *constructed once*, before any traversal; rebuilding it inside the
  recursion would regrow the cost to $O(n \cdot m)$.
- Caching must survive the *object identity* semantics of `Person`; since `Person` is mutable as
  written, key the cache on `id(p)` + a `weakref` guard, or freeze the record after import.
- Frozen dataclass instances (`@dataclass(frozen=True)`) are hashable by definition; mutable
  dataclasses are not hashable (`__hash__ = None`), so never use them as `lru_cache` keys.

---

## 6. Drawing the map over each cluster

Want: a drawing of $H_i = G[C_i]$ per cluster. Standard recipe: **layered (Sugiyama) layout on a
DAG** — 3 passes:

1. **Rank / generation layer.** Longest-path ranking in topological order:

   $$
   \mathrm{rank}(v) = \delta + \max_{(p,v) \in E} \mathrm{rank}(p),\qquad \delta = \text{rank offset},
   $$

   with $\mathrm{rank} = 0$ for persons without parents. Computed in $O(n+m)$ by processing nodes in
   topological order (well-defined by I2; if violated, the cycle detector flags it first).
   This placement is *semantically correct*: children sit one generation below both parents, which
   reproduces the $\deg^{-} \le 2$ structure visually.

2. **Within-layer ordering (crossing minimisation).** Suggest several sweep passes (top→bottom and
   bottom→top) using the *barycenter* heuristic: for node $u$ on layer $\ell$,

   $$
   b(u) = \frac{1}{\deg(u)} \sum_{(w,u) \in E \text{ or } (u,w)\in E} \mathrm{pos}(w).
   $$

   Sorting nodes in each layer by $b(u)$ reduces edge crossings. This is NP-hard in general, so the
   heuristic is the accepted choice; it costs $O(s\,(n+m))$ for $s$ sweeps.

3. **Coordinates.** $x$ = position from pass (2) (ordered within its layer), $y = \mathrm{rank}(v) \cdot
   \Delta$, with $\Delta$ = pixel-per-generation constant; cluster $i$'s bounding boxes never overlap
   because clusters are disjoint (Section 1.3).

For a source-free export, Mermaid or Graphviz already does (2)-(3); the recursive search only has to
supply $C_i$ and $E(C_i)$.

---

## 7. Relationship to existing code

| `src/main.py` element | Role in the design |
|---|---|
| `Person.mom`, `Person.dad` | The two parental edges per node (Section 1.1) |
| `Person.name` | Natural key for external maps / Mermaid labels |
| `Person.pronouns`, `Pronouns` | Presentation only; irrelevant to the algorithm |
| `Person.__str__`, `Person.pronoun` | Presentation only |
| *(new, proposed)* `ChildIndex`, `ClusterMap`, `explore`, `cluster_map` | The additions specified above |

---

## 8. Verification plan

1. **Correctness (property-based).** Generate random `Person` DAGs with controlled $n$ and
   $\deg^- \le 2$; assert `cluster_map` matches a reference BFS-with-components in $\Theta(n+m)$;
   assert $k = n - s$ (identity (3)) on every random instance.
2. **Memoisation.** Build the diamond chain $D_k$; measure the un-memoised (expected exponential)
   number of calls against $2^{k}$; assert the memoised call count is $\Theta(n+m)$ — each node is
   computed exactly once.
3. **Depth safety.** Build a chain of $n > 1000$ persons; assert the iterative version completes and
   (as a negative test) that the naive recursive one raises `RecursionError`.
4. **Cycles.** Add a self-parent edge `p.mom = p`; assert the 3-colour guard raises `ValueError`.
5. **Scaling.** Fit measured wall-time to $t(n) = c \cdot n$ on $n \in \{10^{3}, 10^{4}, 10^{5}\}$;
   expected residual $< 5\%$ — the linear prediction of (1).

---

## Appendix A — Ackermann inverse $\alpha$ in one display

$$
A(1,j) = 2j,\qquad A(i,0) = 0,\qquad A(i,j) = A(i-1, A(i, j-1)),
\qquad
\alpha(m,n) = \min\{i : A(i, \lceil 4m/n\rceil) > \lceil \log_2 n\rceil\}.
$$

$\alpha$ grows slower than any primitive recursive function; for all physically reachable input sizes
$\alpha \le 5$. Hence $O(m\,\alpha(m,n))$ is linear for all intents, which is why Union-Find is the
accepted choice for streaming cluster construction (O3).

## Appendix B — The two running theorems in compact form

- **Knaster–Tarski / DFS coherence.** $\mathrm{lfp}$ of monotone $\Phi_v$ is exactly the recursion's
  output (Theorem 3.2).
- **Cluster count rank identity.** $k = n - s$ where $s$ = successful unions = $n - k$ forest edges
  (Theorem 3.3).
- **Memoised DP.** $T(n,m) = \Theta(n+m)$; proof via the potential/uncached-node argument (4.3).
- **Amortised Union-Find bound.** $O(m\,\alpha(m,n))$ (Tarjan 1975; Tarjan–van Leeuwen 1984).