#!/usr/bin/env python3
"""Generate deterministic release figures from ontology/SCM statistics."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def figures() -> dict[str, str]:
    stats = json.loads((ROOT / "docs/generated/statistics.json").read_text())
    modules = stats["source_modules"]
    benchmark = stats["benchmarks"]
    total_axioms = sum(record["axiom_count"] for record in modules)
    total_seconds = sum(record["extraction_seconds"] for record in modules)
    return {
        "three-layer-architecture.pdf": r'''digraph G {
          graph [rankdir=LR, bgcolor="transparent", pad=.2]; node [shape=box, style="rounded,filled", fontname="Helvetica", margin=.15];
          K [label="K  OWL TBox\ntraits + source modules\nordinary relational axioms", fillcolor="#dbeafe"];
          P [label="Pi  projection registry\nversioned binary/ternary patterns", fillcolor="#fef3c7"];
          M [label="M  typed JSON SCM\ntraits, influences, production,\nconstitution, identities, modulation", fillcolor="#dcfce7"];
          K -> M [label="  ELK entailment", fontname="Helvetica"]; P -> M [label="  pattern match", fontname="Helvetica"];
        }''',
        "asserted-inferred-projection.pdf": r'''digraph G {
          graph [rankdir=LR, bgcolor="transparent", pad=.2]; node [shape=box, style="rounded,filled", fontname="Helvetica"];
          A [label="asserted\ncollection(B) subclass\nhasMember some (causedBy some A)", fillcolor="#dbeafe"];
          C [label="classified closure\nB_sub subclass B\nA subclass A_super", fillcolor="#fef3c7"];
          E [label="entailed projections\nA -> B; A_super -> B\n(the witness member need not\nfall under B_sub)", fillcolor="#dcfce7"];
          A -> C [label=" ELK"]; C -> E [label=" indexed candidates"];
        }''',
        "trait-composition.pdf": f'''digraph G {{
          graph [rankdir=LR, bgcolor="transparent", pad=.2]; node [shape=box, style="rounded,filled", fontname="Helvetica"];
          T [label="All traits\\n{stats['traits']}", fillcolor="#e5e7eb"];
          C [label="Complete contextual traits\\n{stats['complete_traits']} ({100*stats['complete_traits']/stats['traits']:.1f}%)", fillcolor="#dcfce7"];
          I [label="Incomplete primitive traits\\n{stats['incomplete_traits']} ({100*stats['incomplete_traits']/stats['traits']:.1f}%)", fillcolor="#fee2e2"];
          T -> C; T -> I;
        }}''',
        "legacy-recovery.pdf": f'''digraph G {{
          graph [rankdir=LR, bgcolor="transparent", pad=.2]; node [shape=box, style="rounded,filled", fontname="Helvetica"];
          Y [label="legacy YAML\\n{stats['traits']} nodes\\n{stats['influences']} causal influences\\n{stats['production_relations']} production relations", fillcolor="#e5e7eb"];
          O [label="OWL + ELK\\n{stats['unique_elk_entailments']} unique witnesses", fillcolor="#dbeafe"];
          S [label="typed SCM\\n{stats['traits']} nodes\\n{stats['influences']} causal influences\\n{stats['production_relations']} production relations\\n{stats['quantitative_expressions']} quantitative expressions\\n100% recovered", fillcolor="#dcfce7"];
          Y -> O [label=" generate"]; O -> S [label=" project"]; S -> Y [label=" exact adapter", style=dashed];
        }}''',
        "graph-structure.pdf": f'''digraph G {{
          graph [rankdir=LR, bgcolor="transparent", pad=.2]; node [shape=box, style="rounded,filled", fontname="Helvetica"];
          G [label="causal graph\\n{stats['traits']} variables / {stats['influences']} influences", fillcolor="#dbeafe"];
          B [label="largest feedback SCC\\n{stats['graph']['largest_scc']} variables", fillcolor="#fee2e2"];
          R [label="remaining SCCs\\n{stats['graph']['scc_count'] - 1}", fillcolor="#dcfce7"];
          H [label="benchmarks\\n{sum(x['cases'] for x in benchmark.values())} cases / 0 wrong determinate", fillcolor="#fef3c7"];
          G -> B; G -> R; B -> H; R -> H;
        }}''',
        "locality-performance.pdf": f'''digraph G {{
          graph [rankdir=LR, bgcolor="transparent", pad=.2]; node [shape=box, style="rounded,filled", fontname="Helvetica"];
          S [label="6 checksum-pinned source ontologies", fillcolor="#e5e7eb"];
          L [label="OWLAPI BOT locality extraction\\n{total_axioms:,} module axioms / {total_seconds:.1f} s refresh", fillcolor="#dbeafe"];
          K [label="TBox-only primary KB\\nABox individuals excluded", fillcolor="#dcfce7"];
          S -> L -> K;
        }}''',
    }


def render(dot: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["dot", "-Tpdf", "-o", str(output)], input=dot, text=True, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/generated")
    parser.add_argument("--paper-dir", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    specs = figures()
    paper_dir = args.paper_dir or ROOT / "paper/generated"
    directories = [args.output_dir]
    if args.paper_dir is not None or paper_dir.parent.is_dir():
        directories.append(paper_dir)
    if args.check:
        stale = []
        with tempfile.TemporaryDirectory() as temporary:
            for name, dot in specs.items():
                render(dot, Path(temporary) / name)
                source_name = name.removesuffix(".pdf") + ".dot"
                for directory in directories:
                    source = directory / source_name
                    if not source.is_file() or source.read_text(encoding="utf-8") != dot + "\n":
                        stale.append(str(source))
                    if directory == paper_dir and not (directory / name).is_file():
                        stale.append(str(directory / name))
        if stale:
            raise SystemExit("stale generated figures: " + ", ".join(stale))
        print("generated migration figures: current")
        return 0
    for directory in directories:
        for name, dot in specs.items():
            (directory / (name.removesuffix(".pdf") + ".dot")).write_text(dot + "\n", encoding="utf-8")
            render(dot, directory / name)
    print(f"wrote {len(specs)} migration figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
