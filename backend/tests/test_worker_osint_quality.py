try:
    from backend.workers.tampa_bay_lead_worker import apply_osint_quality, enrichment_summary, normalize_element
except ModuleNotFoundError:
    from workers.tampa_bay_lead_worker import apply_osint_quality, enrichment_summary, normalize_element


REAL_ESTATE_TARGET = {"kind": "real_estate", "label": "Real estate office"}


def test_osint_quality_approves_local_florida_business() -> None:
    record = normalize_element(
        {
            "type": "node",
            "id": 1,
            "lat": 27.9501,
            "lon": -82.4553,
            "tags": {
                "name": "Castillo Real Estate",
                "addr:housenumber": "625",
                "addr:street": "East Twiggs Street",
                "addr:city": "Tampa",
                "addr:state": "FL",
                "addr:postcode": "33602",
                "phone": "+1-855-676-0278",
                "website": "https://realestatecastillo.com",
            },
        },
        "Hillsborough County",
        REAL_ESTATE_TARGET,
        "2026-07-04T00:00:00+00:00",
    )

    assert record is not None
    assert record["quality_band"] == "High"
    assert record["review_status"] == "approved_for_package"
    assert record["osint_confidence"] == "High"
    assert record["osint_flags"] == ""
    assert record["data_completeness_score"] == 90
    assert record["source_risk"] == "Low"
    assert record["buyer_persona"] == "Real estate agent or brokerage"
    assert "Package-ready OSINT QA" in record["fit_signals"]
    assert "Public business/location data only" in record["compliance_notes"]


def test_osint_quality_holds_out_of_state_county_name_match() -> None:
    record = normalize_element(
        {
            "type": "way",
            "id": 2,
            "center": {"lat": 42.9756, "lon": -71.4752},
            "tags": {
                "name": "Berkshire Hathaway HomeServices",
                "addr:housenumber": "475",
                "addr:street": "Second Street",
                "addr:city": "Manchester",
                "addr:state": "NH",
                "addr:postcode": "03102",
                "phone": "+1-603-668-7770",
                "website": "https://verani.com/",
            },
        },
        "Hillsborough County",
        REAL_ESTATE_TARGET,
        "2026-07-04T00:00:00+00:00",
    )

    assert record is not None
    assert record["quality_band"] == "Low"
    assert record["review_status"] == "hold_for_manual_review"
    assert record["source_risk"] == "High"
    assert "State mismatch" in record["osint_flags"]
    assert "outside target Florida county bounds" in record["osint_flags"]


def test_backfill_adds_enrichment_fields_to_existing_record() -> None:
    record = {
        "lead_id": "tb-existing",
        "name": "Suncoast Cleaning",
        "category": "Home and professional cleaning",
        "county": "Pinellas",
        "city": "Clearwater",
        "state": "FL",
        "postcode": "33756",
        "street": "100 Court Street",
        "phone": "+1-727-555-0100",
        "website": "https://suncoastcleaning.example",
        "latitude": "27.9659",
        "longitude": "-82.8001",
    }

    apply_osint_quality(record)

    assert record["buyer_persona"] == "Cleaning and facility-services operator"
    assert record["recommended_offer"] in {
        "Commercial cleaning prospect pack",
        "Priority Commercial cleaning prospect pack",
    }
    assert "Structured local address" in record["fit_signals"]
    assert record["data_completeness_score"] >= 90
    assert record["source_risk"] == "Low"


def test_enrichment_summary_counts_risk_and_average_completeness() -> None:
    records = {
        "low": {"source_risk": "Low", "data_completeness_score": 100},
        "medium": {"source_risk": "Medium", "data_completeness_score": 60},
        "high": {"source_risk": "High", "data_completeness_score": 20},
    }

    summary = enrichment_summary(records)

    assert summary["average_data_completeness_score"] == 60.0
    assert summary["source_risk"] == {"Low": 1, "Medium": 1, "High": 1}
