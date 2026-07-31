# Building Ontologies with Basic Formal Ontology (BFO) — STUB

**[NO PDF — stub]** (MIT Press book, not open access.) Definitions below captured
from the BFO 2.0 Reference / ISO 21838-2 specification and the BFO literature
(verified via WebFetch/WebSearch). This stub captures the continuant/occurrent,
quality, disposition, process, and realization machinery that PhysioMap depends on.

## Citation
Arp R, Smith B, Spear AD. *Building Ontologies with Basic Formal Ontology.*
Cambridge, MA: MIT Press; 2015. ISBN 9780262527811.
Companion standard: BFO 2.0 / ISO/IEC 21838-2:2021.

## Key BFO distinctions (the realization chain PhysioMap reuses)
- **Continuant** vs **Occurrent**. A *continuant* persists through time, maintaining
  identity, and has no temporal parts (objects, qualities). An *occurrent* (process,
  process boundary, temporal/spatiotemporal region) unfolds in time and has temporal
  parts.
- **Independent continuant** — bears other entities but does not depend on them;
  e.g. *material entity*, *object* (a heart, a cell, a molecule). This is the
  ENTITY in PhysioMap's (entity, quality) node.
- **Specifically dependent continuant (SDC)** — *inheres in* (is borne by) an
  independent continuant and cannot exist without it. Two kinds:
  - **Quality** — an SDC that, if it inheres in a bearer, is fully exhibited /
    realized whenever its bearer exists (e.g. a mass, a shape, a color, blood
    pressure as a determinate value). This is the QUALITY in a PhysioMap node;
    PATO determinable qualities are the *determinables*, determinate values their
    *determinates*.
  - **Realizable entity** — an SDC whose instances are *realized in* processes of a
    correlated type. Subkinds: **role** (externally grounded, optional),
    **disposition** (internally grounded in the physical make-up of the bearer;
    realized in a process when triggered), **function** (a disposition that exists in
    virtue of the bearer's physical make-up and is the bearer's reason for being).
- **Process** — an occurrent that has temporal parts and depends on (has
  participants) one or more material entities; the *realization* of a disposition is
  a process.

## Key relations
- **inheres_in / bearer_of** (inverse): an SDC inheres in its independent-continuant
  bearer. (In phenotype EQ this is the relation tying Quality Q to Entity E.)
- **realized_in / realizes** (inverse, SDC–process): a realizable entity (disposition,
  function, role) is *realized_in* a process; the process *realizes* it. A
  disposition "d realized_in p" iff p is a process and d is a disposition whose bearer
  is causally responsible for p (realization happens in virtue of the bearer's
  physical make-up).
- **has_realization** = inverse of realized_in.
- **participates_in / has_participant**, **occurs_in**, **part_of**.

## The realization chain (load-bearing for PhysioMap causal edges)
BFO supports: a **quality/configuration of a bearer GROUNDS a disposition**; the
**disposition is realized_in a process**; the **process produces (changes) a quality**.
That is exactly the quality -> disposition -> process -> quality mechanism a PhysioMap
within-scale causal edge abbreviates.

## RELEVANCE to PhysioMap
- Node typing: ENTITY = BFO independent continuant (material entity); QUALITY = BFO
  quality (PATO determinable). The OWL reasoning phase validates that the EQ pair is
  a (material entity, quality) pair using BFO as the upper ontology.
- Causal-edge abbreviation: the mechanism a causal edge stores is a
  disposition realized_in a process (BFO realizable -> occurrent), with the process
  bringing about the downstream quality. Store the disposition + process as the
  mechanism ref; the edge is the abbreviation.
- Constitutive cross-scale edges: micro material entities are *part_of* the macro
  material entity; their configuration (micro qualities) *determines* the macro
  quality. Both are continuants, so the cross-scale relation is among continuants
  (part_of + determination), distinct from the occurrent-grounded within-scale
  causal edge.
