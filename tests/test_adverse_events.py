from datetime import date

import pytest

from app.adverse_events import (
    AdverseEventDataset,
    calculate_adverse_event_analytics,
    build_adverse_event_search,
    parse_adverse_event_report,
)


def test_build_adverse_event_search_uses_exact_brand_and_inclusive_dates() -> None:
    search = build_adverse_event_search(
        'Brand "A"',
        date(2024, 1, 1),
        date(2024, 12, 31),
    )

    assert 'patient.drug.openfda.brand_name.exact:"Brand \\"A\\""' in search
    assert "receivedate:[20240101 TO 20241231]" in search


def test_build_adverse_event_search_rejects_invalid_date_order() -> None:
    with pytest.raises(ValueError, match="start date"):
        build_adverse_event_search("Eliquis", date(2025, 1, 1), date(2024, 1, 1))


def test_parse_adverse_event_report_extracts_source_fields_and_deduplicates_reactions() -> None:
    report = parse_adverse_event_report(
        {
            "receivedate": "20240415",
            "serious": "1",
            "seriousnessdeath": "1",
            "seriousnesshospitalization": "1",
            "patient": {
                "reaction": [
                    {"reactionmeddrapt": "NAUSEA"},
                    {"reactionmeddrapt": "NAUSEA"},
                    {"reactionmeddrapt": "HEADACHE"},
                ]
            },
        }
    )

    assert report.received_date == date(2024, 4, 15)
    assert report.serious is True
    assert report.outcomes == frozenset({"death", "hospitalization"})
    assert report.reactions == ("NAUSEA", "HEADACHE")


def test_calculate_adverse_event_analytics_is_deterministic() -> None:
    dataset = AdverseEventDataset(
        reports=[
            parse_adverse_event_report(
                {
                    "receivedate": "20240115",
                    "serious": "1",
                    "seriousnesshospitalization": "1",
                    "patient": {
                        "reaction": [
                            {"reactionmeddrapt": "NAUSEA"},
                            {"reactionmeddrapt": "HEADACHE"},
                        ]
                    },
                }
            ),
            parse_adverse_event_report(
                {
                    "receivedate": "20240420",
                    "serious": "2",
                    "patient": {"reaction": [{"reactionmeddrapt": "NAUSEA"}]},
                }
            ),
            parse_adverse_event_report(
                {
                    "receivedate": "invalid",
                    "serious": "1",
                    "seriousnessdeath": "1",
                    "patient": {"reaction": [{"reactionmeddrapt": "FATIGUE"}]},
                }
            ),
        ],
        available_reports=5,
    )

    analytics = calculate_adverse_event_analytics(
        dataset,
        brand_name="Eliquis",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 9, 30),
    )

    assert analytics["overview"] == {
        "total_reports": 3,
        "serious_reports": 2,
        "non_serious_reports": 1,
        "serious_percentage": 66.7,
        "reporting_period_start": date(2024, 1, 15),
        "reporting_period_end": date(2024, 4, 20),
    }
    assert analytics["retrieval"]["truncated"] is True
    assert analytics["outcomes"][0]["report_count"] == 1
    assert analytics["outcomes"][1]["report_count"] == 1
    assert analytics["reactions"][0] == {
        "term": "NAUSEA",
        "report_count": 2,
        "report_percentage": 66.7,
        "serious_report_count": 1,
    }
    assert analytics["trends"] == [
        {"period": "2024 Q1", "total_reports": 1, "serious_reports": 1},
        {"period": "2024 Q2", "total_reports": 1, "serious_reports": 0},
        {"period": "2024 Q3", "total_reports": 0, "serious_reports": 0},
    ]


def test_calculate_adverse_event_analytics_handles_empty_results() -> None:
    analytics = calculate_adverse_event_analytics(
        AdverseEventDataset(reports=[], available_reports=0),
        brand_name="No Reports Brand",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 3, 31),
    )

    assert analytics["overview"]["total_reports"] == 0
    assert analytics["overview"]["serious_percentage"] == 0.0
    assert analytics["overview"]["reporting_period_start"] is None
    assert analytics["reactions"] == []
    assert analytics["trends"] == [
        {"period": "2025 Q1", "total_reports": 0, "serious_reports": 0}
    ]
