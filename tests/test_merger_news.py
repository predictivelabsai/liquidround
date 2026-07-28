from utils.merger_news import canonical_url, classify_stage, parse_entry


def _entry(**values):
    defaults = {
        "title": "Buyer Corp. to Acquire Target Inc. for $425 Million",
        "summary": "The companies entered into a definitive agreement.",
        "link": "https://example.com/release?tracking=1",
        "id": "release-1",
        "published": "Tue, 28 Jul 2026 12:00:00 GMT",
    }
    defaults.update(values)
    return defaults


def test_merger_release_is_normalized_and_classified():
    record = parse_entry("prnewswire", _entry())
    assert record is not None
    assert record["event_stage"] == "announced"
    assert record["deal_value"] == 425_000_000
    assert record["source_url"] == "https://example.com/release"
    assert record["published_at"].tzinfo is not None


def test_noise_and_non_merger_releases_are_rejected():
    assert parse_entry("globenewswire", _entry(title="Form 8.3 - Example PLC")) is None
    assert parse_entry("businesswire", _entry(
        title="Manager UK Regulatory Announcement: Form 8.3",
        summary="A takeover disclosure.",
    )) is None
    assert parse_entry("businesswire", _entry(
        title="Company investigation alert",
        summary="A law firm investigates a proposal to acquire the company.",
    )) is None
    assert parse_entry("businesswire", _entry(
        title="Example Corp. Reports Quarterly Results",
        summary="Revenue increased year over year.",
    )) is None


def test_stage_and_reverse_merger_detection():
    record = parse_entry("globenewswire", _entry(
        title="Shell Corp. Completes Reverse Merger with Target LLC",
        summary="The company completed its acquisition and ceased to be a shell company.",
    ))
    assert record["event_stage"] == "completed"
    assert record["is_reverse_merger"] is True


def test_canonical_url_drops_tracking_parameters():
    assert canonical_url("HTTPS://Example.com/a?x=1#fragment") == "https://example.com/a"
