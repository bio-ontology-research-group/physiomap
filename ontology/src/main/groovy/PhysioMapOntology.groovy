/*
 * OWL 2 EL release validator. Non-EL input is rejected before ELK is created;
 * bounded HermiT module checks belong to separately registered validation jobs.
 */

import org.semanticweb.owlapi.apibinding.OWLManager
import org.semanticweb.owlapi.model.OWLOntologyManager
import org.semanticweb.owlapi.model.OWLOntology
import org.semanticweb.owlapi.model.IRI
import org.semanticweb.owlapi.model.OWLClass
import org.semanticweb.owlapi.model.AxiomType
import org.semanticweb.owlapi.model.OWLSubClassOfAxiom
import org.semanticweb.owlapi.model.OWLObjectSomeValuesFrom
import org.semanticweb.owlapi.model.OWLObjectIntersectionOf
import org.semanticweb.owlapi.profiles.OWL2ELProfile
import org.semanticweb.owlapi.profiles.OWL2DLProfile
import org.semanticweb.elk.owlapi.ElkReasonerFactory
import org.semanticweb.owlapi.reasoner.OWLReasoner
import org.semanticweb.owlapi.reasoner.InferenceType
import org.semanticweb.HermiT.ReasonerFactory
import uk.ac.manchester.cs.owlapi.modularity.ModuleType
import uk.ac.manchester.cs.owlapi.modularity.SyntacticLocalityModuleExtractor
import org.semanticweb.owlapi.formats.FunctionalSyntaxDocumentFormat

class PhysioMapOntology {

    OWLOntologyManager manager
    OWLOntology ontology
    OWLReasoner reasoner
    Map<String, String> nodeIds = [:]
    /** Trait-collection class IRI -> node id of the trait it collects (`pm:collectionFor`). */
    Map<String, String> collectionNodeIds = [:]
    Set<OWLClass> variables = new HashSet<OWLClass>()

    /** Load an ontology (or import-merged set) from an IRI or local path. */
    void load(String location) {
        manager = OWLManager.createOWLOntologyManager()
        File file = new File(location)
        ontology = file.exists()
            ? manager.loadOntologyFromOntologyDocument(file)
            : manager.loadOntology(IRI.create(location))
    }

    /** Classify the loaded ontology with the ELK reasoner. */
    void classify() {
        requireLoaded()
        def report = new OWL2ELProfile().checkOntology(ontology)
        if (!report.inProfile) {
            throw new IllegalArgumentException("OWL 2 EL profile violations:\n" +
                report.violations.collect { it.toString() }.join("\n"))
        }
        reasoner = new ElkReasonerFactory().createReasoner(ontology)
        if (!reasoner.consistent) {
            throw new IllegalStateException("PhysioMap EL ontology is inconsistent")
        }
        reasoner.precomputeInferences(InferenceType.CLASS_HIERARCHY)
        def unsatisfiable = reasoner.unsatisfiableClasses.entitiesMinusBottom
        if (!unsatisfiable.empty) {
            throw new IllegalStateException("Unsatisfiable classes: " +
                unsatisfiable.collect { it.getIRI().toString() }.sort().join(", "))
        }
    }

    /** Validate an EQ node typing: entity IRI + PATO quality IRI. */
    boolean validateEqTyping(String entityIri, String qualityIri) {
        requireLoaded()
        OWLClass entity = manager.OWLDataFactory.getOWLClass(IRI.create(entityIri))
        OWLClass quality = manager.OWLDataFactory.getOWLClass(IRI.create(qualityIri))
        return ontology.containsClassInSignature(entity.getIRI(), true) &&
               ontology.containsClassInSignature(quality.getIRI(), true) &&
               !entity.isOWLNothing() && !quality.isOWLNothing()
    }

    /**
     * Enumerate registered projection witnesses using ELK entailment. Candidate generation is
     * indexed from asserted restrictions and their inferred class closures; it never performs an
     * all-pairs query over traits. Output is stable TSV consumed by the Python release gate.
     */
    void project(File output) {
        if (reasoner == null) classify()
        // SCM variables are selected semantically (asserted/inferred `pm:MapVariable` membership)
        // and named by their `pm:nodeId` annotation. Neither the IRI namespace nor the IRI's local
        // name carries meaning: grouping classes share the KB but are not map variables.
        def factory = manager.OWLDataFactory
        def mapVariable = factory.getOWLClass(IRI.create("https://w3id.org/physiomap/MapVariable"))
        variables = new HashSet<OWLClass>(reasoner.getSubClasses(mapVariable, false)
            .flattened.findAll { !it.isOWLNothing() })
        nodeIds = [:]
        collectionNodeIds = [:]
        ontology.getAxioms(AxiomType.ANNOTATION_ASSERTION).each { axiom ->
            if (!(axiom.subject instanceof IRI) || !axiom.value.asLiteral().present) return
            String property = axiom.property.getIRI().toString()
            if (property == "https://w3id.org/physiomap/nodeId") {
                nodeIds[axiom.subject.toString()] = axiom.value.asLiteral().get().getLiteral()
            } else if (property == "https://w3id.org/physiomap/collectionFor") {
                collectionNodeIds[axiom.subject.toString()] = axiom.value.asLiteral().get().getLiteral()
            }
        }
        variables.each { cls ->
            if (!nodeIds.containsKey(cls.getIRI().toString())) {
                throw new IllegalStateException("map variable without a pm:nodeId annotation: " +
                    cls.getIRI().toString())
            }
        }
        def traitSignature = variables.size()
        def rows = new TreeSet<String>()
        // Constitution is a genuine universal and stays a subclass axiom on the trait; the
        // mechanism relations are type-level capacity claims asserted of the trait's collection.
        def binary = [
            "https://w3id.org/physiomap/constitutedBy": "constitution-v1",
        ]
        def collectionBinary = [
            "https://w3id.org/physiomap/causedBy": "causal-collection-v2",
            "https://w3id.org/physiomap/producedBy": "production-collection-v2",
        ]
        String hasMember = "https://w3id.org/physiomap/hasMember"
        def numerator = [:].withDefault { new TreeSet<String>() }
        def denominator = [:].withDefault { new TreeSet<String>() }
        int indexedRestrictions = 0
        int traitSubclasses = 0
        int existentialSupers = 0

        ontology.getAxioms(AxiomType.SUBCLASS_OF).each { OWLSubClassOfAxiom axiom ->
            if (axiom.subClass.anonymous) return
            OWLClass sub = axiom.subClass.asOWLClass()
            def sup = axiom.superClass
            if (collectionNodeIds.containsKey(sub.getIRI().toString())) {
                // `C_t SubClassOf hasMember some (causedBy some T_s)`: some member of the target
                // trait's collection is actually caused by a source instance.
                if (!(sup instanceof OWLObjectSomeValuesFrom) || sup.property.anonymous) return
                if (sup.property.asOWLObjectProperty().getIRI().toString() != hasMember) return
                if (!(sup.filler instanceof OWLObjectSomeValuesFrom)) return
                def inner = sup.filler
                if (inner.property.anonymous) return
                indexedRestrictions++
                String innerProperty = inner.property.asOWLObjectProperty().getIRI().toString()
                if (collectionBinary.containsKey(innerProperty) && !inner.filler.anonymous) {
                    addCollectionEntailments(rows, collectionBinary[innerProperty], sub,
                                             inner.filler.asOWLClass(),
                                             inner.property.asOWLObjectProperty())
                } else if (innerProperty == "https://w3id.org/physiomap/modulates" &&
                           inner.filler instanceof OWLObjectIntersectionOf) {
                    addModulationEntailment(rows, axiom, sub, inner.filler)
                }
                return
            }
            if (!variables.contains(sub)) return
            traitSubclasses++
            if (sup instanceof OWLObjectSomeValuesFrom) existentialSupers++
            if (sup instanceof OWLObjectSomeValuesFrom && !sup.property.anonymous) {
                indexedRestrictions++
                String property = sup.property.asOWLObjectProperty().getIRI().toString()
                if (binary.containsKey(property) && !sup.filler.anonymous) {
                    addBinaryEntailments(rows, binary[property], sub, sup.filler.asOWLClass(),
                                         sup.property.asOWLObjectProperty())
                } else if (property == "https://w3id.org/physiomap/hasNumerator" && !sup.filler.anonymous) {
                    numerator[nodeId(sub)] << nodeId(sup.filler.asOWLClass())
                } else if (property == "https://w3id.org/physiomap/hasDenominator" && !sup.filler.anonymous) {
                    denominator[nodeId(sub)] << nodeId(sup.filler.asOWLClass())
                }
            }
        }
        (numerator.keySet().intersect(denominator.keySet())).sort().each { result ->
            numerator[result].each { n -> denominator[result].each { d ->
                rows << "ratio-v1\t${result}\t${n}\t${d}"
            }}
        }
        output.parentFile?.mkdirs()
        output.setText("pattern_id\targ1\targ2\targ3\n" + rows.join("\n") + "\n", "UTF-8")
        File traitOutput = new File(output.parentFile, "trait-classification.tsv")
        def traitRows = variables.toList().sort {
            a, b -> nodeId(a) <=> nodeId(b)
        }.collect { cls ->
            def parents = new TreeSet<String>()
            reasoner.getSuperClasses(cls, false).flattened.findAll { !it.isOWLThing() }.each {
                parents << it.getIRI().toString()
            }
            reasoner.getEquivalentClasses(cls).entities.findAll { it != cls && !it.isOWLThing() }.each {
                parents << it.getIRI().toString()
            }
            return "${nodeId(cls)}\ttrue\t${parents.join('|')}"
        }
        traitOutput.setText("node_id\tsatisfiable\tinferred_parents\n" + traitRows.join("\n") + "\n", "UTF-8")
        println "Signature has ${traitSignature} traits. Found ${traitSubclasses} trait subclass axioms / ${existentialSupers} existential supers; " +
                "indexed ${indexedRestrictions} restrictions; projected ${rows.size()} entailments"
    }

    private void addBinaryEntailments(Set<String> rows, String pattern, OWLClass target,
                                      OWLClass source, def property) {
        def targets = new TreeSet<OWLClass>(Comparator.comparing { it.getIRI().toString() })
        targets << target
        targets.addAll(reasoner.getSubClasses(target, false).flattened.findAll {
            !it.isOWLNothing() && variables.contains(it)
        })
        def sources = new TreeSet<OWLClass>(Comparator.comparing { it.getIRI().toString() })
        sources << source
        sources.addAll(reasoner.getSuperClasses(source, false).flattened.findAll {
            !it.isOWLThing() && variables.contains(it)
        })
        targets.each { t -> sources.each { s ->
            def witness = manager.OWLDataFactory.getOWLSubClassOfAxiom(t,
                manager.OWLDataFactory.getOWLObjectSomeValuesFrom(property, s))
            if (reasoner.isEntailed(witness)) rows << "${pattern}\t${nodeId(s)}\t${nodeId(t)}\t"
        }}
    }

    /**
     * Witnesses for a mechanism relation asserted of the *target* trait's collection.
     *
     * Generalizing the source is sound and stays entailed: if some member of the collection is
     * caused by a `T_s` instance, it is caused by an instance of every superclass of `T_s`.
     * Specializing the target is deliberately *not* inherited -- the witness member need not fall
     * under a more specific trait -- which is exactly what the plain subclass form got wrong.
     */
    private void addCollectionEntailments(Set<String> rows, String pattern, OWLClass collection,
                                          OWLClass source, def property) {
        String target = collectionNodeIds[collection.getIRI().toString()]
        if (target == null) return
        def sources = new TreeSet<OWLClass>(Comparator.comparing { it.getIRI().toString() })
        sources << source
        sources.addAll(reasoner.getSuperClasses(source, false).flattened.findAll {
            !it.isOWLThing() && variables.contains(it)
        })
        def factory = manager.OWLDataFactory
        def hasMember = factory.getOWLObjectProperty(
            IRI.create("https://w3id.org/physiomap/hasMember"))
        sources.each { s ->
            def witness = factory.getOWLSubClassOfAxiom(collection,
                factory.getOWLObjectSomeValuesFrom(hasMember,
                    factory.getOWLObjectSomeValuesFrom(property, s)))
            if (reasoner.isEntailed(witness)) rows << "${pattern}\t${nodeId(s)}\t${target}\t"
        }
    }

    private void addModulationEntailment(Set<String> rows, OWLSubClassOfAxiom axiom,
                                         OWLClass collection, OWLObjectIntersectionOf filler) {
        String modulator = collectionNodeIds[collection.getIRI().toString()]
        if (modulator == null) return
        OWLClass target = null
        OWLClass source = null
        filler.operands.each { operand ->
            if (!operand.anonymous) target = operand.asOWLClass()
            if (operand instanceof OWLObjectSomeValuesFrom && !operand.property.anonymous &&
                operand.property.asOWLObjectProperty().getIRI().toString() == "https://w3id.org/physiomap/causedBy" &&
                !operand.filler.anonymous) source = operand.filler.asOWLClass()
        }
        if (target != null && source != null && reasoner.isEntailed(axiom)) {
            rows << "multiplicative-modulation-v2\t${modulator}\t${nodeId(source)}\t${nodeId(target)}"
        }
    }

    /** Node id of a map variable, read from its `pm:nodeId` annotation (never from its IRI). */
    private String nodeId(OWLClass cls) {
        String value = nodeIds[cls.getIRI().toString()]
        if (value == null) {
            throw new IllegalStateException("no pm:nodeId annotation for " + cls.getIRI().toString())
        }
        return value
    }

    private void requireLoaded() {
        if (ontology == null) throw new IllegalStateException("load an ontology first")
    }

    /**
     * Check that the representation-level artifact is in the OWL 2 DL profile. No reasoner runs:
     * the DL artifact states what PhysioMap represents (inverses, universals), while every
     * released entailment is computed by ELK over the EL artifact.
     */
    void checkDlProfile() {
        requireLoaded()
        def report = new OWL2DLProfile().checkOntology(ontology)
        if (!report.inProfile) {
            throw new IllegalArgumentException("OWL 2 DL profile violations:\n" +
                report.violations.collect { it.toString() }.join("\n"))
        }
        println "OWL 2 DL profile: OK (${ontology.axiomCount} axioms)"
    }

    /** Validate one explicitly bounded OWL 2 DL locality module with HermiT. */
    void checkHermit(int maximumAxioms) {
        requireLoaded()
        if (maximumAxioms <= 0) throw new IllegalArgumentException("maximumAxioms must be positive")
        if (ontology.axiomCount > maximumAxioms) {
            throw new IllegalArgumentException(
                "HermiT module has ${ontology.axiomCount} axioms; maximum is ${maximumAxioms}")
        }
        def profile = new OWL2DLProfile().checkOntology(ontology)
        if (!profile.inProfile) {
            throw new IllegalArgumentException("OWL 2 DL profile violations:\n" +
                profile.violations.collect { it.toString() }.join("\n"))
        }
        OWLReasoner dl = new ReasonerFactory().createReasoner(ontology)
        try {
            if (!dl.consistent) throw new IllegalStateException("HermiT module is inconsistent")
            def unsatisfiable = dl.unsatisfiableClasses.entitiesMinusBottom
            if (!unsatisfiable.empty) {
                throw new IllegalStateException("HermiT module has unsatisfiable classes: " +
                    unsatisfiable.collect { it.getIRI().toString() }.sort().join(", "))
            }
        } finally {
            dl.dispose()
        }
    }

    /** Extract a bounded bottom-locality TBox module; source ABox individuals are excluded. */
    void extractModule(File signatureFile, File output, int maximumAxioms) {
        requireLoaded()
        if (maximumAxioms <= 0) throw new IllegalArgumentException("maximumAxioms must be positive")
        def signature = new TreeSet(Comparator.comparing { it.getIRI().toString() })
        signatureFile.readLines("UTF-8").collect { it.trim() }.findAll {
            it && !it.startsWith("#")
        }.each { value ->
            signature << manager.OWLDataFactory.getOWLClass(IRI.create(value))
        }
        if (signature.empty) throw new IllegalArgumentException("locality signature is empty")
        def extractor = new SyntacticLocalityModuleExtractor(manager, ontology, ModuleType.BOT)
        def extracted = extractor.extract(signature).findAll { axiom ->
            !axiom.individualsInSignature().findAny().present
        }.toSet()
        if (extracted.size() > maximumAxioms) {
            throw new IllegalArgumentException(
                "Locality module has ${extracted.size()} axioms; maximum is ${maximumAxioms}")
        }
        def module = manager.createOntology(extracted, IRI.create("https://w3id.org/physiomap/source-module"))
        output.parentFile?.mkdirs()
        manager.saveOntology(module, new FunctionalSyntaxDocumentFormat(), IRI.create(output))
        println "Extracted locality TBox module: ${extracted.size()} axioms / ${signature.size()} signature entities"
    }

    /** Merge the generated PhysioMap TBox with cached source modules into one primary KB. */
    static void mergeTBoxes(File output, List<File> inputs) {
        def manager = OWLManager.createOWLOntologyManager()
        def axioms = new HashSet()
        inputs.each { input ->
            def loaded = manager.loadOntologyFromOntologyDocument(input)
            axioms.addAll(loaded.axioms().filter { axiom ->
                !axiom.individualsInSignature().findAny().present
            }.collect(java.util.stream.Collectors.toSet()))
            manager.removeOntology(loaded)
        }
        def merged = manager.createOntology(axioms, IRI.create("https://w3id.org/physiomap/kb/merged"))
        output.parentFile?.mkdirs()
        manager.saveOntology(merged, new FunctionalSyntaxDocumentFormat(), IRI.create(output))
        println "Merged primary TBox: ${axioms.size()} axioms from ${inputs.size()} artifacts"
    }

    static void main(String[] args) {
        if (args.length >= 4 && args[0] == "--merge") {
            mergeTBoxes(new File(args[1]), args[2..-1].collect { new File(it) })
            return
        }
        if (!(args.length == 1 || (args.length == 2 && args[0] == "--dl-profile") ||
              (args.length == 3 && args[0] in ["--project", "--hermit"]) ||
              (args.length == 5 && args[0] == "--module"))) {
            System.err.println "usage: PhysioMapOntology <el.owl> | --project <el.owl> <output.tsv> | --dl-profile <dl.owl> | --hermit <module.owl> <maximum-axioms> | --module <source.owl> <signature.txt> <output.owl> <maximum-axioms> | --merge <output.owl> <base.owl> <module.owl>..."
            System.exit(2)
        }
        def validator = new PhysioMapOntology()
        String ontologyPath = args.length == 1 ? args[0] : args[1]
        validator.load(ontologyPath)
        if (args.length == 5) {
            validator.extractModule(new File(args[2]), new File(args[3]), Integer.parseInt(args[4]))
            return
        }
        if (args.length == 2 && args[0] == "--dl-profile") {
            validator.checkDlProfile()
            return
        }
        if (args.length == 3 && args[0] == "--hermit") {
            validator.checkHermit(Integer.parseInt(args[2]))
            println "Bounded HermiT module validation: OK"
            return
        }
        validator.classify()
        if (args.length == 3 && args[0] == "--project") {
            validator.project(new File(args[2]))
            println "ELK projection entailments: ${args[2]}"
        }
        println "OWL 2 EL profile, consistency, and classification: OK"
        validator.reasoner.dispose()
    }
}
