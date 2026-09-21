import asyncio
from datetime import date

import pytest

from app.device_adverse_events import (
    DeviceAdverseEventDataset,
    DeviceAdverseEventClient,
    DeviceEventMatch,
    build_device_adverse_event_search,
    build_device_event_match_candidates,
    calculate_device_adverse_event_analytics,
    parse_device_adverse_event_report,
)
from app.openfda import DeviceRecord


def make_device(**overrides: str) -> DeviceRecord:
    values = {
        "record_key": "record-1",
        "device_identifier": "00763000411923",
        "brand_name": "Vanta",
        "company_name": "Medtronic",
        "version_or_model_number": "977006",
        "catalog_number": "977006-C",
        "device_description": "Spinal-cord stimulator",
        "product_codes": ["LGW - STIMULATOR"],
        "commercial_distribution_status": "In Commercial Distribution",
        "prescription_otc_status": "Prescription",
        "single_use_indicator": "Single use",
        "sterility_information": "Not available",
        "mri_safety_information": "Not available",
        "implantable_device_indicator": "Implantable",
        "latex_information": "Not available",
        "storage_and_handling_conditions": [],
        "packaging_configurations": [],
    }
    values.update(overrides)
    return DeviceRecord(**values)


def test_device_match_candidates_follow_explicit_fallback_order() -> None:
    candidates = build_device_event_match_candidates(make_device())

    assert [(candidate.field, candidate.value) for candidate in candidates] == [
        ("device.udi_di", "00763000411923"),
        ("device.model_number.exact", "977006"),
        ("device.catalog_number.exact", "977006-C"),
        ("device.brand_name.exact", "Vanta"),
    ]


def test_device_match_candidates_skip_unavailable_values() -> None:
    candidates = build_device_event_match_candidates(
        make_device(device_identifier="Not available", version_or_model_number="")
    )

    assert [candidate.field for candidate in candidates] == [
        "device.catalog_number.exact",
        "device.brand_name.exact",
    ]


def test_build_device_adverse_event_search_uses_exact_value_and_inclusive_dates() -> None:
    search = build_device_adverse_event_search(
        DeviceEventMatch(
            field="device.model_number.exact",
            value='Model "A"',
            label="Exact model number",
        ),
        date(2025, 1, 1),
        date(2025, 12, 31),
    )

    assert 'device.model_number.exact:"Model \\"A\\""' in search
    assert "date_received:[20250101 TO 20251231]" in search


def test_build_device_adverse_event_search_rejects_invalid_date_order() -> None:
    with pytest.raises(ValueError, match="start date"):
        build_device_adverse_event_search(
            DeviceEventMatch("device.udi_di", "123", "Exact Device Identifier"),
            date(2025, 2, 1),
            date(2025, 1, 1),
        )


def test_parse_device_adverse_event_report_extracts_and_deduplicates_source_terms() -> None:
    report = parse_device_adverse_event_report(
        {
            "date_received": "20250415",
            "event_type": "Injury",
            "product_problems": ["High impedance", "High impedance", "Material rupture"],
            "patient": [
                {"patient_problems": ["Pain", "Pain"]},
                {"patient_problems": ["Pain", "Swelling"]},
            ],
        }
    )

    assert report.received_date == date(2025, 4, 15)
    assert report.event_type == "injury"
    assert report.device_problems == ("High impedance", "Material rupture")
    assert report.patient_problems == ("Pain", "Swelling")


def test_calculate_device_adverse_event_analytics_is_deterministic() -> None:
    exact_di = DeviceEventMatch("device.udi_di", "00763000411923", "Exact Device Identifier")
    dataset = DeviceAdverseEventDataset(
        reports=[
            parse_device_adverse_event_report(
                {
                    "date_received": "20250115",
                    "event_type": "Death",
                    "product_problems": ["Failure to deliver therapy"],
                    "patient": [{"patient_problems": ["Pain"]}],
                }
            ),
            parse_device_adverse_event_report(
                {
                    "date_received": "20250420",
                    "event_type": "Malfunction",
                    "product_problems": ["High impedance", "Failure to deliver therapy"],
                    "patient": [{"patient_problems": ["Pain", "No clinical signs"]}],
                }
            ),
            parse_device_adverse_event_report(
                {"date_received": "bad", "event_type": "Unknown"}
            ),
        ],
        available_reports=1200,
        selected_match=exact_di,
        attempted_matches=(exact_di,),
    )

    analytics = calculate_device_adverse_event_analytics(
        dataset,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 6, 30),
    )

    assert analytics["matching"]["field"] == "device.udi_di"
    assert analytics["retrieval"] == {
        "retrieved_reports": 3,
        "available_reports": 1200,
        "retrieval_limit": 1000,
        "truncated": True,
        "sort": "date_received:desc",
    }
    assert analytics["overview"]["reporting_period_start"] == date(2025, 1, 15)
    assert analytics["overview"]["reporting_period_end"] == date(2025, 4, 20)
    assert analytics["event_types"] == [
        {"event_type": "death", "label": "Death", "report_count": 1, "report_percentage": 33.3},
        {"event_type": "injury", "label": "Injury", "report_count": 0, "report_percentage": 0.0},
        {"event_type": "malfunction", "label": "Malfunction", "report_count": 1, "report_percentage": 33.3},
        {"event_type": "other", "label": "Other or not specified", "report_count": 1, "report_percentage": 33.3},
    ]
    assert analytics["trends"][0]["death_reports"] == 1
    assert analytics["trends"][1]["malfunction_reports"] == 1
    assert analytics["device_problems"][0] == {
        "term": "Failure to deliver therapy",
        "report_count": 2,
        "report_percentage": 66.7,
    }
    assert analytics["patient_problems"][0] == {
        "term": "Pain",
        "report_count": 2,
        "report_percentage": 66.7,
    }


def test_empty_device_event_analytics_exposes_every_attempted_match() -> None:
    attempts = tuple(build_device_event_match_candidates(make_device()))
    analytics = calculate_device_adverse_event_analytics(
        DeviceAdverseEventDataset(
            reports=[],
            available_reports=0,
            selected_match=None,
            attempted_matches=attempts,
        ),
        start_date=date(2025, 1, 1),
        end_date=date(2025, 3, 31),
    )

    assert analytics["matching"]["field"] is None
    assert len(analytics["matching"]["attempted"]) == 4
    assert analytics["overview"]["total_reports"] == 0


def test_device_event_client_stops_at_first_successful_match(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, status_code: int, payload: dict) -> None:
            self.status_code = status_code
            self._payload = payload

        def json(self) -> dict:
            return self._payload

    class FakeAsyncClient:
        requests: list[dict] = []

        def __init__(self, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            pass

        async def get(self, url, params):
            self.requests.append(params)
            if len(self.requests) == 1:
                return FakeResponse(404, {"error": {"message": "No matches found"}})
            return FakeResponse(
                200,
                {
                    "meta": {"results": {"total": 1}},
                    "results": [
                        {
                            "date_received": "20250201",
                            "event_type": "Malfunction",
                            "product_problems": ["High impedance"],
                        }
                    ],
                },
            )

    monkeypatch.setattr(
        "app.device_adverse_events.httpx.AsyncClient",
        FakeAsyncClient,
    )

    dataset = asyncio.run(
        DeviceAdverseEventClient().get_reports(
            make_device(),
            date(2025, 1, 1),
            date(2025, 12, 31),
        )
    )

    assert dataset.selected_match is not None
    assert dataset.selected_match.field == "device.model_number.exact"
    assert [match.field for match in dataset.attempted_matches] == [
        "device.udi_di",
        "device.model_number.exact",
    ]
    assert len(FakeAsyncClient.requests) == 2
