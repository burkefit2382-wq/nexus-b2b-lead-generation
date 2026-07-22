import json

try:
    from backend.workers.osint_pipeline import (
        canonical_identity,
        compliance_result,
        deduplicate,
        normalize_record,
        run_pipeline,
    )
except ModuleNotFoundError:
    from workers.osint_pipeline import (
        canonical_identity,
        compliance_result,
        deduplicate,
        normalize_record,
        run_pipeline,
    )


def lead(**overrides):
    record = {
        "lead_id": "lead-1",
        "name": "Acme Roofing",
        "category": "Home services",
        "county": "Hillsborough",
        "city": "Tampa",
        "state": "FL",
        "postcode": "33602",
        "street": "1 Main Street",
        "phone": "(813) 555-0100",
        "website": "acme.example/",
        "source": "OpenStreetMap Overpass public data",
        "source_id": "osm:node:1",
        "score": 95,
        "osint_quality_score": 95,
        "review_status": "approved_for_package",
        "collected_at": "2026-07-22T00:00:00+00:00",
    }
    record.update(overrides)
    return record


def test_normalization_produces_stable_business_identity() -> None:
    first = normalize_record(lead(), 365)
    second = normalize_record(lead(phone="+1 813 555 0100", website="https://www.acme.example"), 365)

    assert first["phone"] == "+18135550100"
    assert first["website"] == "https://acme.example"
    assert canonical_identity(first) == canonical_identity(second)
    assert first["retention_expires_at"].startswith("2027-07-22")


def test_deduplication_merges_source_attribution() -> None:
    first = normalize_record(lead(), 365)
    second = normalize_record(lead(lead_id="lead-2", source_id="osm:way:2", osint_quality_score=90), 365)

    unique, duplicates = deduplicate([first, second])

    assert duplicates == 1
    merged = next(iter(unique.values()))
    assert merged["duplicate_count"] == 2
    assert merged["source_ids"] == ["osm:node:1", "osm:way:2"]


def test_compliance_quarantines_non_allowlisted_and_suppressed_records() -> None:
    record = normalize_record(lead(source="Private broker database"), 365)
    result = compliance_result(record, {record["canonical_id"]})

    assert result["allowed"] is False
    assert result["reasons"] == ["source_not_allowlisted", "suppression_match"]


def test_pipeline_routes_records_and_writes_auditable_outputs(tmp_path) -> None:
    records = [
        lead(),
        lead(lead_id="lead-2", source_id="osm:way:2"),
        lead(lead_id="lead-3", name="Review LLC", website="review.example", phone="", review_status="review_recommended"),
        lead(lead_id="lead-4", name="Blocked LLC", website="blocked.example", source="Unknown source"),
    ]

    processed, summary = run_pipeline(records, tmp_path, export_enabled=False)

    assert len(processed) == 3
    assert summary["duplicates_merged"] == 1
    assert summary["approved_records"] == 1
    assert summary["manual_review_records"] == 1
    assert summary["quarantined_records"] == 1
    assert summary["hubspot_export_enabled"] is False
    assert (tmp_path / "pipeline_manifest.json").exists()
    assert len((tmp_path / "approved_leads.jsonl").read_text(encoding="utf-8").splitlines()) == 1
    manifest = json.loads((tmp_path / "pipeline_manifest.json").read_text(encoding="utf-8"))
    assert manifest["pipeline_version"] == "1.0"


def test_pipeline_expires_records_outside_retention_window(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NEXUS_OSINT_RETENTION_DAYS", "1")

    processed, summary = run_pipeline([lead(collected_at="2020-01-01T00:00:00+00:00")], tmp_path, export_enabled=False)

    assert processed == {}
    assert summary["input_records"] == 1
    assert summary["expired_records"] == 1
