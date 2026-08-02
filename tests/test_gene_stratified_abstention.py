from math import isclose

from physiomap_core.model import Sign
from scripts.e2_baseline import gene_stratified_abstention_test


def test_gene_stratified_abstention_test_convolves_gene_nulls():
    rows = [
        ("G1", "n1", None, Sign.PLUS, None, Sign.MINUS),
        ("G1", "n2", Sign.PLUS, Sign.PLUS, None, Sign.PLUS),
        ("G2", "n3", None, Sign.MINUS, None, Sign.PLUS),
        ("G2", "n4", Sign.MINUS, Sign.MINUS, None, Sign.MINUS),
    ]

    result = gene_stratified_abstention_test(rows)

    assert result["genes"] == 2
    assert result["genes_with_both_call_statuses"] == 2
    assert result["informative_genes"] == 2
    assert result["abstention_errors"] == 2
    assert result["shared_commit_errors"] == 0
    assert isclose(result["expected_errors_under_null"], 1.0)
    assert isclose(result["exact_one_sided_p"], 0.25)
