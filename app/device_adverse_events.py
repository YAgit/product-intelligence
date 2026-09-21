from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
import logging
from typing import Any

import httpx

from app.config import settings
from app.openfda import DeviceRecord, OpenFdaError


OPENFDA_DEVICE_EVENT_URL = "https://api.fda.gov/device/event.json"
MAX_RETRIEVED_DEVICE_REPORTS = 1000
MAX_PROBLEM_TERMS = 25
DEVICE_RETRIEVAL_SORT = "date_received:desc"

logger = logging.getLogger(__name__)

DEVICE_EVENT_LIMITATIONS = [
    "A report does not establish that the device caused or contributed to the reported event.",
    "Report counts are not incidence or comparative risk because device-use and exposure denominators are unavailable.",
    "Reports may be duplicated, incomplete, influenced by reporting practices, or vary in quality.",
    "A single report may describe multiple devices, patients, outcomes, or coded problem terms.",
    "Higher reporting volume does not by itself establish higher device risk or a confirmed safety signal.",
    "The absence of reports does not establish that a device is safe.",
]


@dataclass(frozen=True)
class DeviceEventMatch:
    field: str
    value: str
    label: str


@dataclass(frozen=True)
class DeviceAdverseEventReport:
    received_date: date | None
    event_type: str
    device_problems: tuple[str, ...]
    patient_problems: tuple[str, ...]


@dataclass(frozen=True)
class DeviceAdverseEventDataset:
    reports: list[DeviceAdverseEventReport]
    available_reports: int
    selected_match: DeviceEventMatch | None
    attempted_matches: tuple[DeviceEventMatch, ...]


def _usable_match_value(value: str) -> str | None:
    normalized = value.strip()
    if not normalized or normalized.casefold() == "not available":
        return None
    return normalized


def build_device_event_match_candidates(device: DeviceRecord) -> list[DeviceEventMatch]:
    candidates: list[DeviceEventMatch] = []
    values = (
        ("device.udi_di", device.device_identifier, "Exact Device Identifier"),
        ("device.model_number.exact", device.version_or_model_number, "Exact model number"),
        ("device.catalog_number.exact", device.catalog_number, "Exact catalog number"),
        ("device.brand_name.exact", device.brand_name, "Exact brand name fallback"),
    )
    for field, value, label in values:
        normalized = _usable_match_value(value)
        if normalized is not None:
            candidates.append(DeviceEventMatch(field=field, value=normalized, label=label))
    return candidates


def build_device_adverse_event_search(
    match: DeviceEventMatch,
    start_date: date,
    end_date: date,
) -> str:
    if start_date > end_date:
        raise ValueError("The device adverse-event start date must be on or before the end date.")
    if not match.value.strip():
        raise ValueError("A device matching value is required.")

    escaped_value = match.value.replace("\\", "\\\\").replace('"', '\\"')
    start = start_date.strftime("%Y%m%d")
    end = end_date.strftime("%Y%m%d")
    return f'{match.field}:"{escaped_value}" AND date_received:[{start} TO {end}]'


def _parse_received_date(value: Any) -> date | None:
    raw_value = str(value or "").strip()
    if len(raw_value) != 8 or not raw_value.isdigit():
        return None
    try:
        return datetime.strptime(raw_value, "%Y%m%d").date()
    except ValueError:
        return None


def _unique_terms(values: Any) -> tuple[str, ...]:
    if not isinstance(values, list):
        return ()
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        term = str(value or "").strip()
        if term and term not in seen:
            seen.add(term)
            terms.append(term)
    return tuple(terms)


def _event_type(value: Any) -> str:
    normalized = str(value or "").strip().casefold()
    if normalized == "death":
        return "death"
    if normalized == "injury":
        return "injury"
    if normalized == "malfunction":
        return "malfunction"
    return "other"


def parse_device_adverse_event_report(payload: dict[str, Any]) -> DeviceAdverseEventReport:
    patient_problems: list[str] = []
    seen_patient_problems: set[str] = set()
    patients = payload.get("patient")
    if isinstance(patients, list):
        for patient in patients:
            if not isinstance(patient, dict):
                continue
            for term in _unique_terms(patient.get("patient_problems")):
                if term not in seen_patient_problems:
                    seen_patient_problems.add(term)
                    patient_problems.append(term)

    return DeviceAdverseEventReport(
        received_date=_parse_received_date(payload.get("date_received")),
        event_type=_event_type(payload.get("event_type")),
        device_problems=_unique_terms(payload.get("product_problems")),
        patient_problems=tuple(patient_problems),
    )


def _quarter_start(value: date) -> tuple[int, int]:
    return value.year, ((value.month - 1) // 3) + 1


def _quarter_range(start_date: date, end_date: date) -> list[tuple[int, int]]:
    year, quarter = _quarter_start(start_date)
    end_year, end_quarter = _quarter_start(end_date)
    periods: list[tuple[int, int]] = []
    while (year, quarter) <= (end_year, end_quarter):
        periods.append((year, quarter))
        if quarter == 4:
            year += 1
            quarter = 1
        else:
            quarter += 1
    return periods


def _problem_analytics(terms: Counter[str], total: int) -> list[dict[str, Any]]:
    return [
        {
            "term": term,
            "report_count": count,
            "report_percentage": round((count / total) * 100, 1) if total else 0.0,
        }
        for term, count in sorted(
            terms.items(), key=lambda item: (-item[1], item[0].casefold())
        )[:MAX_PROBLEM_TERMS]
    ]


def calculate_device_adverse_event_analytics(
    dataset: DeviceAdverseEventDataset,
    *,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    reports = dataset.reports
    total = len(reports)
    valid_dates = sorted(
        report.received_date for report in reports if report.received_date is not None
    )
    event_type_labels = {
        "death": "Death",
        "injury": "Injury",
        "malfunction": "Malfunction",
        "other": "Other or not specified",
    }
    event_type_counts = Counter(report.event_type for report in reports)

    device_problem_counts: Counter[str] = Counter()
    patient_problem_counts: Counter[str] = Counter()
    for report in reports:
        device_problem_counts.update(report.device_problems)
        patient_problem_counts.update(report.patient_problems)

    trend_counts: dict[tuple[int, int], Counter[str]] = {
        period: Counter() for period in _quarter_range(start_date, end_date)
    }
    for report in reports:
        if report.received_date is None:
            continue
        period = _quarter_start(report.received_date)
        if period in trend_counts:
            trend_counts[period]["total"] += 1
            trend_counts[period][report.event_type] += 1

    selected_match = dataset.selected_match
    return {
        "matching": {
            "field": selected_match.field if selected_match else None,
            "value": selected_match.value if selected_match else None,
            "strategy": selected_match.label if selected_match else "No matching strategy returned reports",
            "start_date": start_date,
            "end_date": end_date,
            "attempted": [
                {"field": match.field, "value": match.value, "strategy": match.label}
                for match in dataset.attempted_matches
            ],
        },
        "retrieval": {
            "retrieved_reports": total,
            "available_reports": dataset.available_reports,
            "retrieval_limit": MAX_RETRIEVED_DEVICE_REPORTS,
            "truncated": dataset.available_reports > total,
            "sort": DEVICE_RETRIEVAL_SORT,
        },
        "overview": {
            "total_reports": total,
            "reporting_period_start": valid_dates[0] if valid_dates else None,
            "reporting_period_end": valid_dates[-1] if valid_dates else None,
        },
        "event_types": [
            {
                "event_type": event_type,
                "label": label,
                "report_count": event_type_counts[event_type],
                "report_percentage": (
                    round((event_type_counts[event_type] / total) * 100, 1) if total else 0.0
                ),
            }
            for event_type, label in event_type_labels.items()
        ],
        "trends": [
            {
                "period": f"{year} Q{quarter}",
                "total_reports": counts["total"],
                "death_reports": counts["death"],
                "injury_reports": counts["injury"],
                "malfunction_reports": counts["malfunction"],
                "other_reports": counts["other"],
            }
            for (year, quarter), counts in trend_counts.items()
        ],
        "device_problems": _problem_analytics(device_problem_counts, total),
        "patient_problems": _problem_analytics(patient_problem_counts, total),
        "limitations": DEVICE_EVENT_LIMITATIONS,
        "source": "FDA Manufacturer and User Facility Device Experience (MAUDE) via openFDA",
    }


class DeviceAdverseEventClient:
    async def get_reports(
        self,
        device: DeviceRecord,
        start_date: date,
        end_date: date,
        *,
        limit: int = MAX_RETRIEVED_DEVICE_REPORTS,
    ) -> DeviceAdverseEventDataset:
        candidates = build_device_event_match_candidates(device)
        if not candidates:
            raise ValueError("The selected device does not have an identifier for event matching.")

        attempted: list[DeviceEventMatch] = []
        timeout = httpx.Timeout(20.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            for match in candidates:
                attempted.append(match)
                params: dict[str, str | int] = {
                    "search": build_device_adverse_event_search(match, start_date, end_date),
                    "limit": min(limit, MAX_RETRIEVED_DEVICE_REPORTS),
                    "sort": DEVICE_RETRIEVAL_SORT,
                }
                if settings.openfda_api_key:
                    params["api_key"] = settings.openfda_api_key

                try:
                    response = await client.get(OPENFDA_DEVICE_EVENT_URL, params=params)
                except httpx.HTTPError as exc:
                    logger.warning(
                        "openFDA device adverse-event request failed: %s", type(exc).__name__
                    )
                    raise OpenFdaError(
                        "openFDA device adverse-event data could not be reached right now."
                    ) from exc

                if response.status_code == 404:
                    continue
                if response.status_code >= 400:
                    try:
                        payload = response.json()
                    except ValueError:
                        payload = {}
                    if not isinstance(payload, dict):
                        payload = {}
                    message = payload.get("error", {}).get("message") or (
                        "openFDA returned an unexpected device adverse-event error."
                    )
                    logger.warning(
                        "openFDA device adverse-event request returned status %s",
                        response.status_code,
                    )
                    raise OpenFdaError(message)

                try:
                    payload = response.json()
                except ValueError as exc:
                    raise OpenFdaError(
                        "openFDA returned an invalid device adverse-event response."
                    ) from exc
                if not isinstance(payload, dict):
                    raise OpenFdaError(
                        "openFDA returned an invalid device adverse-event response."
                    )

                results = payload.get("results", [])
                if not isinstance(results, list):
                    raise OpenFdaError(
                        "openFDA returned an invalid device adverse-event response."
                    )
                reports = [
                    parse_device_adverse_event_report(item)
                    for item in results
                    if isinstance(item, dict)
                ]
                if not reports:
                    continue

                meta = payload.get("meta", {})
                meta_results = meta.get("results", {}) if isinstance(meta, dict) else {}
                available_reports = meta_results.get("total", len(reports))
                try:
                    available_count = int(available_reports)
                except (TypeError, ValueError):
                    available_count = len(reports)
                return DeviceAdverseEventDataset(
                    reports=reports,
                    available_reports=max(available_count, len(reports)),
                    selected_match=match,
                    attempted_matches=tuple(attempted),
                )

        return DeviceAdverseEventDataset(
            reports=[],
            available_reports=0,
            selected_match=None,
            attempted_matches=tuple(attempted),
        )


def get_device_adverse_event_client() -> DeviceAdverseEventClient:
    return DeviceAdverseEventClient()
