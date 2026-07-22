try:
    from backend.workers.tampa_bay_lead_worker import normalize_element, worker_metrics_text
except ModuleNotFoundError:
    from workers.tampa_bay_lead_worker import normalize_element, worker_metrics_text


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
    assert "State mismatch" in record["osint_flags"]
    assert "outside target Florida county bounds" in record["osint_flags"]


def test_worker_metrics_text() -> None:
    metrics = worker_metrics_text(
        {
            "ok": True,
            "total_records": 12,
            "new_records": 3,
            "errors": [{"error": "source failed"}],
            "last_run_at": "2026-07-20T12:00:00+00:00",
            "quality": {"approved_for_package": 7, "review_recommended": 4, "hold_for_manual_review": 1},
        }
    )

    assert 'nexus_worker_up{worker="tampa_bay_lead_worker"} 1' in metrics
    assert 'nexus_worker_total_records{worker="tampa_bay_lead_worker"} 12' in metrics
    assert 'nexus_worker_failed_source_runs{worker="tampa_bay_lead_worker"} 1' in metrics
    assert 'nexus_worker_quality_records{worker="tampa_bay_lead_worker",status="approved_for_package"} 7' in metrics
