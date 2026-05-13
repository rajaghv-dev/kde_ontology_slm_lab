# 04 — Graph schema and queries

The ontology says *what kinds of things exist*. The graph is the data structure that holds the actual instances and the edges between them. In this lab the graph is a `networkx.MultiDiGraph` built by [../src/graph/builder.py](../src/graph/builder.py) and queried by [../src/graph/queries.py](../src/graph/queries.py). This chapter explains the schema, walks the named queries, sketches the SPARQL / RDF / OWL path for v0.1, and is honest about the queries the lab cannot — and should not try to — express.

## Why a directed multi-graph

Three properties of a KDE ontology drive the choice:

1. **Edges are directed.** `CppClass --EMITS--> Signal` is not the same as `Signal --EMITS--> CppClass`. Most relations have a natural source and destination, so directionality matters.
2. **Multiple edges between the same pair are common.** A `SourceFile` can both `DEFINES` a `CppClass` and `RELATED_TO` it with a different annotation (e.g. via an `#include`). A class can `EMITS` more than one signal — that one is many edges to *different* targets, but `DEFINES + RELATED_TO` to the same target is what `MultiDiGraph` is for.
3. **Nodes carry attributes.** Every node has `type`, `name`, `qualified_name`, `source_path`, `source_line`, plus arbitrary `prop_*` keys. Edges carry `rel` (the relation type) plus any `prop_*` annotations.

A plain `DiGraph` would force us to encode the relation type in the edge attributes only, which makes querying clunky. `MultiDiGraph` lets us key edges on the relation, so `g.out_edges(node, keys=True)` yields `(node, dst, "EMITS")` tuples directly.

## Builder details

`build_graph` in [../src/graph/builder.py](../src/graph/builder.py) does two passes:

```python
for ent in bundle.entities.values():
    g.add_node(ent.id, type=ent.type, name=ent.name, ...)
for rel in bundle.relations:
    if rel.src not in g.nodes or rel.dst not in g.nodes:
        continue
    g.add_edge(rel.src, rel.dst, key=rel.rel, rel=rel.rel, ...)
```

Two things worth noting:

- **Silent drop of dangling relations.** If an edge points at an id that does not exist as a node, the builder drops it. We prefer a clean graph over a noisy one. The cost: when an extractor forgets to add a node, the corresponding edges vanish without warning. The mitigation is the smoke test in [../tests/test_graph_build.py](../tests/test_graph_build.py): it asserts the expected number of nodes and edges and would fail loudly if a key entity disappeared.
- **Stable ids.** Because ids come from [../src/common/ids.py](../src/common/ids.py)'s `make_id`, two extractors can produce the same id for the same logical entity without coordinating. The graph just merges them.

The graph is persisted in two formats:

- `artifacts/graphs/mini_repo.json` — a plain dict with `nodes` and `edges` arrays, easy to load in a Jupyter notebook or a Python REPL.
- `artifacts/graphs/mini_repo.graphml` — for Gephi, yEd, Cytoscape, and any other graph visualisation tool.

## The 10 named queries

The graph module also gives you a small library of focused queries — small enough that you can read every one in [../src/graph/queries.py](../src/graph/queries.py) in two minutes.

| Query                       | Returns                                                                | Used by                                  |
|-----------------------------|------------------------------------------------------------------------|------------------------------------------|
| `nodes_of_type(g, t)`       | All node ids of a given entity type                                    | Dataset templates                        |
| `out_edges_by_rel(g, n, r)` | All `(src, dst)` pairs out of `n` along relation `r`                   | All higher-level queries                 |
| `neighbors_by_rel(g, n, r)` | Just the destination ids for a relation                                | All higher-level queries                 |
| `signals_emitted_by(g, c)`  | Signal ids a `CppClass` emits                                          | Dataset, eval, traceability              |
| `config_keys_read_by(g, c)` | `ConfigKey` ids a class reads                                          | Dataset, eval, traceability              |
| `log_categories_of(g, c)`   | `LogCategory` ids a class logs to                                      | Dataset, debugging                       |
| `dbus_methods_of(g, i)`     | `DbusMethod` ids exposed by an interface                               | Dataset, tool-use prompts                |
| `qml_backend_for(g, q)`     | `CppClass` ids a QML component points at via `CONNECTS_TO`             | Dataset, code navigation                 |
| `find_by_name(g, n, types)` | Fuzzy-by-substring node lookup with optional type filter               | Traceability seed expansion              |
| (implicit) BFS expansion    | Multi-hop walk from a seed, used by [../src/traceability/symptom_to_code.py](../src/traceability/symptom_to_code.py) | RAG retriever |

A learning-grade convention: keep each query small, name it after the question it answers, and only generalise it when at least two different callers need the same pattern. Premature abstraction is how graph utilities turn into mini ORMs.

## A worked query

The eval suite asks *"Which signals does the KFileSearcher class emit?"*. The retriever boils down to:

```python
cls_ids = find_by_name(g, "KFileSearcher", types={"CppClass"})
for cid in cls_ids:
    for sid in signals_emitted_by(g, cid):
        d = g.nodes[sid]
        print(d["name"], d["source_path"], d["source_line"])
```

That prints something like:

```
resultsReady   examples/mini_kde_repo/src/kfilesearcher.h  32
searchFailed   examples/mini_kde_repo/src/kfilesearcher.h  32
currentPathChanged examples/mini_kde_repo/src/kfilesearcher.h 32
maxResultsChanged  examples/mini_kde_repo/src/kfilesearcher.h 32
```

In four lines you have not only the names but the file and line numbers — exactly the evidence the dataset record carries.

## SPARQL-shaped queries today

We do not run SPARQL yet, but the lab is *SPARQL-shaped*: every relation in the graph maps cleanly to a triple `(subject, predicate, object)`. The named queries cover the most common patterns:

```
?cls a :CppClass ; :EMITS ?sig .         -> signals_emitted_by
?cls a :CppClass ; :READS_CONFIG ?key .  -> config_keys_read_by
?cls a :CppClass ; :LOGS_TO ?cat .       -> log_categories_of
?iface a :DbusInterface ; :EXPOSES_DBUS ?m . FILTER ?m a :DbusMethod
                                          -> dbus_methods_of
?qml a :QmlComponent ; :CONNECTS_TO ?bk . FILTER ?bk a :CppClass
                                          -> qml_backend_for
```

The TODO file lists "Neo4j and RDF/OWL exporters" as v0.1 stretch items. The bridge is straightforward:

- Each entity id becomes an IRI like `kde:CppClass:abc12345`.
- Each relation becomes a predicate IRI in a small KDE namespace.
- Node properties become datatype properties.
- The export is two passes over the `MultiDiGraph` — one for triples encoding `type`, one for relation triples.

The corresponding OWL ontology is what `schema.py` describes: a class for each entity type, an object property for each relation type, plus a couple of axioms (e.g. `EMITS` has domain `CppClass` and range `Signal`).

## What the graph cannot do

The graph is great at *named-thing* queries. It is bad at three other classes of questions:

1. **Free text similarity.** "Find documents that talk about indexing performance" is a vector-store question, not a graph question. The lab ships a hybrid retriever (planned for v0.1) precisely so the right tool handles each half.
2. **Aggregate counts that span deep paths.** "How many config keys are read by classes that emit a `searchFailed`-style signal in any KIO worker?" is technically a graph traversal, but the lab's named queries deliberately stop short of that. If you need it, write a tiny query for that specific question and add it.
3. **Causality and counterfactuals.** "Would Dolphin still be slow if Baloo were disabled?" requires reasoning over states the graph does not model. That is the job of the SLM plus eval discipline, not the graph.

Knowing the boundary keeps the graph from turning into a giant blob of edges you cannot navigate.

## Edge cases worth knowing

- **Self-edges.** The `from_desktop` extractor adds a `REGISTERS_SERVICE` self-relation on a `DesktopFile` when `DBusActivatable=true`. That is mildly cheeky — really, it should point at a `DbusService` entity — but it preserves the fact in the graph until v0.1 splits service registration into its own slice.
- **Multi-edges with the same key.** `MultiDiGraph` accepts repeated `add_edge` calls with the same key; they overwrite the attributes. We rely on that for idempotency: re-running the pipeline does not double-count edges.
- **Mixed-direction asymmetries.** `CONTAINS` and `BUILDS` always go from container to contained; `DEFINES` always goes from a file to a class. If you add a new relation, write its direction down in `schema.py`'s docstring so future readers do not flip it.

## Reading the graph in a notebook

The notebooks under `notebooks/` (planned for v0.1) load `artifacts/graphs/mini_repo.json`. The pattern is:

```python
import json
import networkx as nx
data = json.loads(open("artifacts/graphs/mini_repo.json").read())
g = nx.MultiDiGraph()
for n in data["nodes"]:
    g.add_node(n.pop("id"), **n)
for e in data["edges"]:
    g.add_edge(e.pop("src"), e.pop("dst"), key=e.get("rel"), **e)
```

From there, every named query in [../src/graph/queries.py](../src/graph/queries.py) works directly because the schema matches the in-process builder output.

## Exercises

1. Open `artifacts/graphs/mini_repo.json` and count edges by `rel`. Sketch a histogram. Which relations are the densest in the v0 ontology? Which are missing entirely?
2. Add a one-line query `methods_calling_dbus(g, class_id)` to a personal scratch file. Implement it as `out_edges_by_rel(g, class_id, "CALLS_DBUS")`. Which entity type does it return?
3. Write a Python snippet that loads the graph and produces a one-line summary per `CppClass`: name, number of signals, number of slots, number of config keys, log category. Print it for `KFileSearcher` and `KFileSearchBackend`.
4. Re-read the `RELATED_TO` edges produced by `from_cpp`'s `include` branch. Choose one and argue whether it should be promoted to a typed relation in v0.1. What new entity type would you add?
5. Export the graph to GraphML, open it in Gephi or yEd, and screenshot the connected component around `KFileSearcher`. Note what is missing visually that should not be (a hint that an extractor branch is silent).

## Further reading

- The `networkx` documentation for `MultiDiGraph` and the I/O modules (`readwrite.graphml`, `readwrite.json_graph`).
- *Graph Databases* (2nd edition) by Robinson, Webber, Eifrem (O'Reilly) — the property-graph perspective.
- The SPARQL 1.1 Query Language specification at W3C for the triple-pattern style.
- Neo4j's Cypher manual for a hands-on graph-query language, useful when v0.1 adds the optional Neo4j exporter.
- *Knowledge Graphs* by Aidan Hogan et al. (Morgan & Claypool, also free online) for a broader survey of graph + ontology patterns.
- The Gephi documentation if you want to look at `mini_repo.graphml` visually.
- *Foundations of Statistical Natural Language Processing* by Manning & Schütze, chapter 14, for why vector retrieval is the wrong hammer for typed-relation questions.
