import spock.lang.Specification

class PhysioMapOntologySpec extends Specification {

    /**
     * Declare a class as an SCM variable: `pm:MapVariable` membership plus its node id, together
     * with the timeless collection of its instances that mechanism relations are asserted of.
     */
    private static String variable(String name) {
        return """Declaration(Class(pm:trait/${name}))
SubClassOf(pm:trait/${name} pm:MapVariable)
AnnotationAssertion(pm:nodeId pm:trait/${name} "${name}")
Declaration(Class(pm:collection/${name}))
AnnotationAssertion(pm:collectionFor pm:collection/${name} "${name}")
SubClassOf(pm:trait/${name} ObjectSomeValuesFrom(pm:memberOf pm:collection/${name}))
SubClassOf(pm:collection/${name} ObjectSomeValuesFrom(pm:hasMember pm:trait/${name}))"""
    }

    private static String variables(List<String> names) {
        return "Declaration(Class(pm:MapVariable))\nDeclaration(AnnotationProperty(pm:nodeId))\n" +
            "Declaration(AnnotationProperty(pm:collectionFor))\n" +
            "Declaration(ObjectProperty(pm:memberOf))\nDeclaration(ObjectProperty(pm:hasMember))\n" +
            names.collect { variable(it) }.join("\n")
    }

    private static File ontology(String body) {
        File file = File.createTempFile("physiomap-", ".owl")
        file.deleteOnExit()
        file.setText("""Prefix(pm:=<https://w3id.org/physiomap/>)
Ontology(<https://w3id.org/physiomap/test>
${body}
)
""", "UTF-8")
        return file
    }

    def "ELK projection generalizes the source but does not specialize the target"() {
        given: "a causal claim on b's collection, with a more general source and a subclass target"
        File input = ontology("""
${variables(["a", "a_super", "b", "b_sub", "unrelated"])}
Declaration(ObjectProperty(pm:causedBy))
SubClassOf(pm:trait/a pm:trait/a_super)
SubClassOf(pm:trait/b_sub pm:trait/b)
SubClassOf(pm:collection/b ObjectSomeValuesFrom(pm:hasMember ObjectSomeValuesFrom(pm:causedBy pm:trait/a)))
""")
        File output = File.createTempFile("projection-", ".tsv")
        output.deleteOnExit()
        def tool = new PhysioMapOntology()

        when:
        tool.load(input.absolutePath)
        tool.classify()
        tool.project(output)
        def rows = output.readLines().toSet()

        then: "a member caused by an `a` is caused by an `a_super`, so the source generalizes"
        rows.contains("causal-collection-v2\ta\tb\t")
        rows.contains("causal-collection-v2\ta_super\tb\t")

        and: "the witness member need not fall under b_sub, so the target does not specialize"
        !rows.any { it.endsWith("\tb_sub\t") }
        !rows.any { it.contains("unrelated") }

        and: "indexed projection equals brute-force entailment over sources and collections"
        def factory = tool.manager.OWLDataFactory
        def names = ["a", "a_super", "b", "b_sub", "unrelated"]
        def causedBy = factory.getOWLObjectProperty(
            org.semanticweb.owlapi.model.IRI.create("https://w3id.org/physiomap/causedBy"))
        def hasMember = factory.getOWLObjectProperty(
            org.semanticweb.owlapi.model.IRI.create("https://w3id.org/physiomap/hasMember"))
        def brute = new TreeSet<String>()
        names.each { source -> names.each { target ->
            def sourceClass = factory.getOWLClass(
                org.semanticweb.owlapi.model.IRI.create("https://w3id.org/physiomap/trait/${source}"))
            def collection = factory.getOWLClass(
                org.semanticweb.owlapi.model.IRI.create("https://w3id.org/physiomap/collection/${target}"))
            def query = factory.getOWLSubClassOfAxiom(collection,
                factory.getOWLObjectSomeValuesFrom(hasMember,
                    factory.getOWLObjectSomeValuesFrom(causedBy, sourceClass)))
            if (tool.reasoner.isEntailed(query)) {
                brute << "causal-collection-v2\t${source}\t${target}\t"
            }
        }}
        rows.findAll { it.startsWith("causal-collection-v2") }.toSet() == brute

        cleanup:
        tool.reasoner?.dispose()
    }

    def "profile violations fail before ELK"() {
        given:
        File input = ontology("""
Declaration(Class(pm:trait/a))
SubClassOf(pm:trait/a ObjectComplementOf(pm:trait/a))
""")
        def tool = new PhysioMapOntology()

        when:
        tool.load(input.absolutePath)
        tool.classify()

        then:
        thrown(IllegalArgumentException)
    }

    def "unsatisfiable trait class fails release validation"() {
        given:
        File input = ontology("""
Declaration(Class(pm:trait/a))
Declaration(Class(pm:X))
Declaration(Class(pm:Y))
DisjointClasses(pm:X pm:Y)
SubClassOf(pm:trait/a pm:X)
SubClassOf(pm:trait/a pm:Y)
""")
        def tool = new PhysioMapOntology()

        when:
        tool.load(input.absolutePath)
        tool.classify()

        then:
        def error = thrown(IllegalStateException)
        error.message.contains("Unsatisfiable classes")

        cleanup:
        tool.reasoner?.dispose()
    }

    def "bounded HermiT accepts a DL module and enforces its size limit"() {
        given:
        File input = ontology("""
Declaration(Class(pm:A))
Declaration(Class(pm:B))
DisjointClasses(pm:A pm:B)
""")
        def tool = new PhysioMapOntology()
        tool.load(input.absolutePath)

        expect:
        tool.checkHermit(10) == null

        when:
        tool.checkHermit(1)

        then:
        thrown(IllegalArgumentException)
    }

    def "bounded HermiT rejects deliberate unsatisfiability"() {
        given:
        File input = ontology("""
Declaration(Class(pm:A))
Declaration(Class(pm:B))
Declaration(Class(pm:Broken))
DisjointClasses(pm:A pm:B)
SubClassOf(pm:Broken pm:A)
SubClassOf(pm:Broken pm:B)
""")
        def tool = new PhysioMapOntology()
        tool.load(input.absolutePath)

        when:
        tool.checkHermit(20)

        then:
        def error = thrown(IllegalStateException)
        error.message.contains("unsatisfiable")
    }

    def "locality extraction retains source TBox and excludes source ABox"() {
        given:
        File input = ontology("""
Declaration(Class(pm:Used))
Declaration(Class(pm:Parent))
Declaration(Class(pm:Unrelated))
Declaration(NamedIndividual(pm:population_member))
SubClassOf(pm:Used pm:Parent)
ClassAssertion(pm:Used pm:population_member)
""")
        File signature = File.createTempFile("signature-", ".txt")
        signature.setText("https://w3id.org/physiomap/Used\n", "UTF-8")
        File output = File.createTempFile("module-", ".owl")
        def tool = new PhysioMapOntology()
        tool.load(input.absolutePath)

        when:
        tool.extractModule(signature, output, 20)
        String rendered = output.getText("UTF-8")

        then:
        rendered.contains("Used")
        rendered.contains("Parent")
        !rendered.contains("population_member")
        !rendered.contains("Unrelated")
    }

    def "all registered asserted pattern shapes are projected and unrelated traits stay negative"() {
        given:
        File input = ontology("""
${variables(["a", "b", "m", "r", "n", "d", "unrelated"])}
Declaration(ObjectProperty(pm:causedBy))
Declaration(ObjectProperty(pm:constitutedBy))
Declaration(ObjectProperty(pm:modulates))
Declaration(ObjectProperty(pm:hasNumerator))
Declaration(ObjectProperty(pm:hasDenominator))
SubClassOf(pm:collection/b ObjectSomeValuesFrom(pm:hasMember ObjectSomeValuesFrom(pm:causedBy pm:trait/a)))
SubClassOf(pm:trait/b ObjectSomeValuesFrom(pm:constitutedBy pm:trait/a))
SubClassOf(pm:trait/r ObjectSomeValuesFrom(pm:hasNumerator pm:trait/n))
SubClassOf(pm:trait/r ObjectSomeValuesFrom(pm:hasDenominator pm:trait/d))
SubClassOf(pm:collection/m ObjectSomeValuesFrom(pm:hasMember ObjectSomeValuesFrom(pm:modulates ObjectIntersectionOf(pm:trait/b ObjectSomeValuesFrom(pm:causedBy pm:trait/a)))))
""")
        File output = File.createTempFile("projection-", ".tsv")
        def tool = new PhysioMapOntology(); tool.load(input.absolutePath); tool.classify()

        when:
        tool.project(output)
        def rows = output.readLines().toSet()

        then:
        rows.contains("causal-collection-v2\ta\tb\t")
        rows.contains("constitution-v1\ta\tb\t")
        rows.contains("ratio-v1\tr\tn\td")
        rows.contains("multiplicative-modulation-v2\tm\ta\tb")
        !rows.any { it.contains("unrelated") }

        cleanup:
        tool.reasoner?.dispose()
    }

    def "domain consequences are entailed in the enforced EL artifact"() {
        given:
        File input = ontology("""
Declaration(Class(pm:Quality))
Declaration(Class(pm:trait/x))
Declaration(Class(pm:Q))
Declaration(ObjectProperty(pm:hasQuality))
ObjectPropertyRange(pm:hasQuality pm:Quality)
SubClassOf(pm:trait/x ObjectSomeValuesFrom(pm:hasQuality pm:Q))
""")
        def tool = new PhysioMapOntology(); tool.load(input.absolutePath); tool.classify()
        def x = tool.manager.OWLDataFactory.getOWLClass(org.semanticweb.owlapi.model.IRI.create("https://w3id.org/physiomap/trait/x"))
        def quality = tool.manager.OWLDataFactory.getOWLClass(org.semanticweb.owlapi.model.IRI.create("https://w3id.org/physiomap/Quality"))
        def q = tool.manager.OWLDataFactory.getOWLClass(org.semanticweb.owlapi.model.IRI.create("https://w3id.org/physiomap/Q"))

        expect: "the range axiom is enforced inside the EL artifact"
        tool.reasoner.isEntailed(tool.manager.OWLDataFactory.getOWLSubClassOfAxiom(q, quality))
        x != null

        cleanup:
        tool.reasoner?.dispose()
    }

    def "part-inclusive grouping classes classify variables without becoming variables"() {
        given: "a whole-organ variable, a part variable, and the defined grouping class"
        File input = ontology("""
${variables(["kidney_volume", "glomerular_volume"])}
Declaration(Class(pm:Trait))
SubClassOf(pm:MapVariable pm:Trait)
Declaration(Class(pm:grouping/kidney_volume))
SubClassOf(pm:grouping/kidney_volume pm:Trait)
Declaration(Class(pm:kidney)) Declaration(Class(pm:glomerulus)) Declaration(Class(pm:PartOfKidney))
Declaration(Class(pm:volume))
Declaration(ObjectProperty(pm:hasPart)) Declaration(ObjectProperty(pm:partOf))
Declaration(ObjectProperty(pm:hasQuality))
TransitiveObjectProperty(pm:partOf)
SubObjectPropertyOf(ObjectPropertyChain(pm:hasPart pm:partOf) pm:hasPart)
SubClassOf(pm:glomerulus ObjectSomeValuesFrom(pm:partOf pm:kidney))
SubClassOf(pm:kidney pm:PartOfKidney)
SubClassOf(ObjectSomeValuesFrom(pm:partOf pm:kidney) pm:PartOfKidney)
SubClassOf(pm:trait/glomerular_volume ObjectSomeValuesFrom(pm:hasPart ObjectIntersectionOf(pm:glomerulus ObjectSomeValuesFrom(pm:hasQuality pm:volume))))
EquivalentClasses(pm:grouping/kidney_volume ObjectSomeValuesFrom(pm:hasPart ObjectIntersectionOf(pm:PartOfKidney ObjectSomeValuesFrom(pm:hasQuality pm:volume))))
""")
        File output = File.createTempFile("projection-", ".tsv")
        output.deleteOnExit()
        def tool = new PhysioMapOntology(); tool.load(input.absolutePath); tool.classify()

        when:
        tool.project(output)
        def classification = new File(output.parentFile, "trait-classification.tsv").readLines()

        then: "the part trait is classified under the grouping"
        classification.any {
            it.startsWith("glomerular_volume\t") &&
                it.contains("https://w3id.org/physiomap/grouping/kidney_volume")
        }

        and: "the grouping class itself is not an SCM variable, so it gets no row"
        classification.findAll { !it.startsWith("node_id") && it.trim() }.size() == 2

        cleanup:
        tool.reasoner?.dispose()
    }
}
