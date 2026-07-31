# PhysioMap as linked data (RDF / OWL)

`physiomap.ttl` is the FAIR, linked-data serialization of PhysioMap: a self-contained Turtle file
holding the OWL schema and the full graph (~27,500 triples). It is regenerated from the curated
YAML fragments by [`scripts/export_rdf.py`](../scripts/export_rdf.py).

Unlike the YAML fragments, the RDF gives a **persistent, resolvable identifier to every variable
_and_ every relation** — the defining property of a causal knowledge graph — so a single causal
edge is itself a citable, queryable resource.

## Identifiers and vocabulary

All PhysioMap resources are minted under **`https://w3id.org/physiomap/`**:

| Resource | IRI pattern |
|---|---|
| variable (node) | `…/node/<id>` |
| causal relation | `…/edge/causal/<source>--<pos\|neg\|unk>--<target>` |
| constitutive relation | `…/edge/constitutive/<n>` |
| modulation (gain) relation | `…/edge/modulation/<n>` |
| schema terms | `…/ontology#…` (prefix `pmo:`) |

Grounding and relation types reuse standard vocabularies:

- **Entities** — ChEBI, PR, GO, CL, Uberon (`obo:` = `http://purl.obolibrary.org/obo/`).
- **Qualities** — PATO; a variable is typed as its PATO determinable and linked to its entity by
  `RO:0000052` (*inheres in*).
- **Signed causation** — the Relation Ontology: `RO:0002304` (*causally upstream of, positive
  effect*), `RO:0002305` (*negative effect*), `RO:0002411` (*causally upstream of*, for `?`).
- **Constitution** — `pmo:constitutes` (+ `BFO:0000050`/`0000051` part-of/has-part).
- **Upper ontology** — SIO (primary): `pmo:Variable ⊑ sio:SIO_000614` (*attribute*), and each
  variable `sio:SIO_000011` (*is attribute of*) its entity; BFO/RO secondary.

Each causal edge is also **reified** as a `pmo:CausalRelation` individual carrying `pmo:sign`,
`pmo:causalEvidence` (the interventional-evidence class), `pmo:mechanism`, and `dcterms:source`
(provenance), so the direct RO triples support reasoning while the reified resource carries
metadata.

## Regenerate

```bash
uv run python scripts/export_rdf.py          # writes rdf/physiomap.ttl
python -c "import rdflib; g=rdflib.Graph(); g.parse('rdf/physiomap.ttl'); print(len(g),'triples')"
```

## Query with SPARQL

Load into any triple store. With [Apache Jena Fuseki](https://jena.apache.org/documentation/fuseki2/):

```bash
fuseki-server --file rdf/physiomap.ttl /physiomap        # serves SPARQL at /physiomap/sparql
```

or, in memory, with `arq`, or with Python `rdflib`. Example queries:

```sparql
PREFIX obo:  <http://purl.obolibrary.org/obo/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

# What does raising a variable lower (one interventional hop)?
SELECT ?sourceLabel ?targetLabel WHERE {
  ?s obo:RO_0002305 ?o .                 # causally upstream of, negative effect
  ?s rdfs:label ?sourceLabel .
  ?o rdfs:label ?targetLabel .
}

# Only causal edges grounded in human loss/gain-of-function evidence
PREFIX pmo: <https://w3id.org/physiomap/ontology#>
SELECT ?src ?tgt WHERE {
  ?e a pmo:CausalRelation ;
     pmo:causalEvidence "genetic_lof_gof" ;
     pmo:hasSource ?src ; pmo:hasTarget ?tgt .
}
```

## Resolving `w3id.org/physiomap/` (deployment)

The `https://w3id.org/physiomap/` namespace resolves through a redirect registered at
[w3id.org](https://github.com/perma-id/w3id.org) (a one-time pull request adding a `physiomap/`
directory with the [`w3id/.htaccess`](w3id/.htaccess) in this folder), pointing dereferenced IRIs
at the hosted RDF with content negotiation. Until that PR is merged the IRIs are stable and
globally unique but not yet dereferenceable.

## License

CC BY 4.0 (see the repository `LICENSING.md`).
