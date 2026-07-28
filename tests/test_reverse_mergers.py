from utils.reverse_mergers import (
    candidate_from_edgar,
    candidate_from_sedar,
    classify_filing,
    classify_sedar_filing,
    extract_transaction_terms,
    validate_manual_record,
)
from utils.filing_intelligence import build_filing_document


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


def test_generic_business_combination_is_not_automatically_a_spac():
    result = classify_filing(
        "Item 1.01. The company entered into a business combination agreement "
        "and described the transaction as a reverse acquisition."
    )
    assert result["transaction_type"] == "us_reverse_merger"


def test_extracts_target_value_and_announcement_status():
    text = (
        "Item 1.01. The company entered into a definitive merger agreement. "
        "The acquisition of Acme Robotics, Inc., a Delaware corporation, has "
        "a transaction value of approximately $425 million."
    )
    terms = extract_transaction_terms(text, public_company="Example Shell Corp.")
    assert terms["private_target"] == "Acme Robotics, Inc."
    assert terms["deal_value"] == 425_000_000
    assert terms["announced"] is True
    assert terms["completed"] is False

    record = candidate_from_edgar({
        "entity_name": "Example Shell Corp.",
        "accession_number": "0001",
        "file_url": "https://www.sec.gov/example.txt",
        "filing_date": "2026-01-02",
        "form_type": "8-K",
    }, text=text + " This is a reverse merger.")
    assert record["status"] == "announced"
    assert record["private_target"] == "Acme Robotics, Inc."
    assert record["deal_value"] == 425_000_000


def test_document_pipeline_selects_primary_and_transaction_exhibits():
    raw = """
    <DOCUMENT><TYPE>8-K
    <SEQUENCE>1
    <FILENAME>form8k.htm
    <DESCRIPTION>Current report
    <TEXT><h2>Item 1.01</h2><p>Definitive merger agreement.</p></TEXT>
    </DOCUMENT>
    <DOCUMENT><TYPE>EX-99.1
    <SEQUENCE>2
    <FILENAME>release.htm
    <DESCRIPTION>Transaction press release
    <TEXT><p>The acquisition of Acme Robotics, Inc., a Delaware corporation,
    has a transaction value of $425 million.</p></TEXT>
    </DOCUMENT>
    <DOCUMENT><TYPE>GRAPHIC
    <SEQUENCE>3
    <TEXT>irrelevant image</TEXT>
    </DOCUMENT>
    """
    filing = build_filing_document(raw)
    assert [doc["document_type"] for doc in filing["documents"]] == ["8-K", "EX-99.1"]
    assert "1.01" in filing["sections"]
    assert "Acme Robotics" in filing["combined_text"]
    assert len(filing["sha256"]) == 64


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


def test_classify_sedar_rto_filing():
    result = classify_sedar_filing(
        "The company completed the reverse takeover of Acme Holdings Ltd. "
        "pursuant to a share exchange agreement. Material change report filed.",
        document_name="Material change report",
    )
    assert result["transaction_type"] == "ca_rto"
    assert result["completed"] is True
    assert "reverse-takeover language" in result["signals"]
    assert result["confidence"] >= 0.6


def test_classify_sedar_cpc_qualifying_transaction():
    result = classify_sedar_filing(
        "The capital pool company announced its qualifying transaction "
        "with an operating company. The transaction remains subject to "
        "shareholder approval.",
        document_name="Qualifying transaction",
    )
    assert result["transaction_type"] == "ca_cpc_qt"
    assert "CPC qualifying-transaction language" in result["signals"]
    assert result["completed"] is False
    assert "completion_not_confirmed" in result["risk_flags"]


def test_classify_sedar_spac_qualifying_acquisition():
    result = classify_sedar_filing(
        "The special purpose acquisition company completed its qualifying "
        "acquisition. Redemption rights were exercised by public shareholders.",
    )
    assert result["transaction_type"] == "ca_spac_qa"
    assert result["completed"] is True


def test_candidate_from_sedar_builds_ca_record():
    record = candidate_from_sedar(
        {
            "profile_name": "Example Capital Pool Corp.",
            "profile_number": "000123456",
            "document_name": "Qualifying transaction",
            "submitted_date": "2026-02-01",
            "jurisdiction": "Ontario",
            "download_url": "https://www.sedarplus.ca/csa-party/viewInstance/resource.html?node=W1&drmKey=k1",
        },
        text=(
            "The capital pool company completed its qualifying transaction "
            "with Acme Operating Ltd. The acquisition of Acme Operating "
            "Ltd., a British Columbia corporation, has a transaction "
            "value of approximately $50 million."
        ),
    )
    assert record["jurisdiction"] == "CA"
    assert record["transaction_type"] == "ca_cpc_qt"
    assert record["status"] == "completed"
    assert record["transaction_key"].startswith("sedar:")
    assert record["source_type"] == "SEDAR+"
    assert record["source_url"] == "https://www.sedarplus.ca/csa-party/000123456.html?_locale=en"
    assert "drmKey=k1" in record["metadata"]["resource_url"]
    assert record["metadata"]["ingestion"] == "sedarplus_scraper"
    assert record["metadata"]["document_mirrored"] is False
    assert record["private_target"] == "Acme Operating Ltd."
    assert record["deal_value"] == 50_000_000


def test_candidate_from_sedar_candidate_is_not_persisted_by_discovery():
    record = candidate_from_sedar(
        {
            "profile_name": "Generic Issuer Inc.",
            "profile_number": "000999999",
            "document_name": "Annual report",
            "submitted_date": "2026-03-01",
            "jurisdiction": "British Columbia",
            "download_url": "https://www.sedarplus.ca/example",
        },
        text="This is a routine annual report with no transaction language.",
    )
    assert record["transaction_type"] == "candidate"


def test_candidate_from_sedar_uses_full_text_search_match_as_evidence():
    record = candidate_from_sedar({
        "profile_name": "Example Mining Inc.",
        "profile_number": "000123456",
        "document_name": "Management information circular - English.pdf",
        "submitted_date": "2026-07-01",
        "jurisdiction": "British Columbia",
        "download_url": "https://www.sedarplus.ca/example",
        "matched_query": "reverse takeover",
    })
    assert record["transaction_type"] == "ca_rto"
    assert record["metadata"]["matched_query"] == "reverse takeover"
    assert record["metadata"]["document_text_available"] is False
