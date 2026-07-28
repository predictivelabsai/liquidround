from utils.reverse_mergers import classify_filing, validate_manual_record


def test_classifies_traditional_reverse_merger():
    result = classify_filing(
        "Item 2.01 Completion of Acquisition. Item 5.01 Change in Control. "
        "Item 5.06 Change in Shell Company Status. The issuer ceased to be a "
        "shell company following the reverse merger. Item 9.01 Financial Statements."
    )
    assert result["transaction_type"] == "us_reverse_merger"
    assert "former_shell_restrictions" in result["risk_flags"]
    assert result["confidence"] >= 0.8


def test_classifies_de_spac_separately():
    result = classify_filing(
        "Item 5.06. Following the business combination, the special purpose "
        "acquisition company ceased to be a shell company. Public shareholders "
        "had redemption rights over amounts in the trust account."
    )
    assert result["transaction_type"] == "us_de_spac"
    assert "redemption_and_sponsor_dilution" in result["risk_flags"]


def test_manual_canadian_record_keeps_citation_only():
    record = validate_manual_record({
        "jurisdiction": "CA",
        "transaction_type": "ca_cpc_qt",
        "public_company": "Example Capital Pool Corp.",
        "private_target": "Example Operating Co.",
        "source_url": "https://www.sedarplus.ca/example",
    })
    assert record["source_type"] == "SEDAR+ manual citation"
    assert record["metadata"]["document_mirrored"] is False
    assert record["review_status"] == "reviewed"
