from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
import logging
from typing import Any

import httpx

from app.config import settings
from app.openfda import OpenFdaError


OPENFDA_DRUG_EVENT_URL = "https://api.fda.gov/drug/event.json"
FAERS_MATCH_FIELD = "patient.drug.openfda.brand_name.exact"
MAX_RETRIEVED_REPORTS = 1000
MAX_REACTIONS = 25
RETRIEVAL_SORT = "receivedate:desc"

logger = logging.getLogger(__name__)

FAERS_LIMITATIONS = [
    "A report does not establish that the product caused the reported event.",
    "Report counts are not incidence or prevalence because exposure and denominator data are unavailable.",
    "Reports may be duplicated, incomplete, influenced by reporting bias, or vary in quality.",
    "Higher reporting volume does not by itself establish higher product risk or a confirmed safety signal.",
    "The absence of reports does not establish that a product is safe.",
]


@dataclass(frozen=True)
class AdverseEventReport:
    received_date: date | None
    serious: bool
    outcomes: frozenset[str]
    reactions: tuple[str, ...]


@dataclass(frozen=True)
class AdverseEventDataset:
    reports: list[AdverseEventReport]
    available_reports: int


def build_adverse_event_search(brand_name: str, start_date: date, end_date: date) -> str:
    normalized_brand = brand_name.strip()
    if not normalized_brand:
        raise ValueError("A selected drug brand name is required for adverse-event matching.")
    if start_date > end_date:
        raise ValueError("The adverse-event start date must be on or before the end date.")

    escaped_brand = normalized_brand.replace("\\", "\\\\").replace('"', '\\"')
    start = start_date.strftime("%Y%m%d")
    end = end_date.strftime("%Y%m%d")
    return f'{FAERS_MATCH_FIELD}:"{escaped_brand}" AND receivedate:[{start} TO {end}]'


def _parse_received_date(value: Any) -> date | None:
    raw_value = str(value or "").strip()
    if len(raw_value) != 8 or not raw_value.isdigit():
        return None
    try:
        return datetime.strptime(raw_value, "%Y%m%d").date()
    except ValueError:
        return None


def _flag_is_true(payload: dict[str, Any], field: str) -> bool:
    return str(payload.get(field, "")).strip() == "1"


def parse_adverse_event_report(payload: dict[str, Any]) -> AdverseEventReport:
    outcome_fields = {
        "death": "seriousnessdeath",
        "hospitalization": "seriousnesshospitalization",
        "life_threatening": "seriousnesslifethreatening",
        "disability": "seriousnessdisabling",
        "congenital_anomaly": "seriousnesscongenitalanomali",
        "other_serious": "seriousnessother",
    }
    outcomes = frozenset(
        outcome for outcome, field in outcome_fields.items() if _flag_is_true(payload, field)
    )

    patient = payload.get("patient")
    patient_payload = patient if isinstance(patient, dict) else {}
    reaction_payloads = patient_payload.get("reaction")
    reactions: list[str] = []
    seen: set[str] = set()
    if isinstance(reaction_payloads, list):
        for item in reaction_payloads:
            if not isinstance(item, dict):
                continue
            term = str(item.get("reactionmeddrapt", "")).strip()
            if term and term not in seen:
                seen.add(term)
                reactions.append(term)

    return AdverseEventReport(
        received_date=_parse_received_date(payload.get("receivedate")),
        serious=_flag_is_true(payload, "serious"),
        outcomes=outcomes,
        reactions=tuple(reactions),
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


def calculate_adverse_event_analytics(
    dataset: AdverseEventDataset,
    *,
    brand_name: str,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    reports = dataset.reports
    total = len(reports)
    serious = sum(report.serious for report in reports)
    valid_dates = sorted(
        report.received_date for report in reports if report.received_date is not None
    )

    outcome_labels = {
        "death": "Death",
        "hospitalization": "Hospitalization",
        "life_threatening": "Life-threatening event",
        "disability": "Disability",
        "congenital_anomaly": "Congenital anomaly",
        "other_serious": "Other serious outcome",
    }
    outcomes = [
        {
            "outcome": outcome,
            "label": label,
            "report_count": sum(outcome in report.outcomes for report in reports),
        }
        for outcome, label in outcome_labels.items()
    ]

    reaction_counts: Counter[str] = Counter()
    serious_reaction_counts: Counter[str] = Counter()
    for report in reports:
        reaction_counts.update(report.reactions)
        if report.serious:
            serious_reaction_counts.update(report.reactions)

    reactions = [
        {
            "term": term,
            "report_count": count,
            "report_percentage": round((count / total) * 100, 1) if total else 0.0,
            "serious_report_count": serious_reaction_counts[term],
        }
        for term, count in sorted(
            reaction_counts.items(), key=lambda item: (-item[1], item[0].casefold())
        )[:MAX_REACTIONS]
    ]

    trend_counts: dict[tuple[int, int], list[int]] = {
        period: [0, 0] for period in _quarter_range(start_date, end_date)
    }
    for report in reports:
        if report.received_date is None:
            continue
        period = _quarter_start(report.received_date)
        if period not in trend_counts:
            continue
        trend_counts[period][0] += 1
        if report.serious:
            trend_counts[period][1] += 1

    trends = [
        {
            "period": f"{year} Q{quarter}",
            "total_reports": counts[0],
            "serious_reports": counts[1],
        }
        for (year, quarter), counts in trend_counts.items()
    ]

    return {
        "matching": {
            "field": FAERS_MATCH_FIELD,
            "value": brand_name,
            "start_date": start_date,
            "end_date": end_date,
        },
        "retrieval": {
            "retrieved_reports": total,
            "available_reports": dataset.available_reports,
            "retrieval_limit": MAX_RETRIEVED_REPORTS,
            "truncated": dataset.available_reports > total,
            "sort": RETRIEVAL_SORT,
        },
        "overview": {
            "total_reports": total,
            "serious_reports": serious,
            "non_serious_reports": total - serious,
            "serious_percentage": round((serious / total) * 100, 1) if total else 0.0,
            "reporting_period_start": valid_dates[0] if valid_dates else None,
            "reporting_period_end": valid_dates[-1] if valid_dates else None,
        },
        "outcomes": outcomes,
        "trends": trends,
        "reactions": reactions,
        "limitations": FAERS_LIMITATIONS,
        "source": "FDA Adverse Event Reporting System (FAERS) via openFDA",
    }


class AdverseEventClient:
    async def get_reports(
        self,
        brand_name: str,
        start_date: date,
        end_date: date,
        *,
        limit: int = MAX_RETRIEVED_REPORTS,
    ) -> AdverseEventDataset:
        search_expression = build_adverse_event_search(brand_name, start_date, end_date)
        params: dict[str, str | int] = {
            "search": search_expression,
            "limit": min(limit, MAX_RETRIEVED_REPORTS),
            "sort": RETRIEVAL_SORT,
        }
        if settings.openfda_api_key:
            params["api_key"] = settings.openfda_api_key

        timeout = httpx.Timeout(20.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.get(OPENFDA_DRUG_EVENT_URL, params=params)
            except httpx.HTTPError as exc:
                logger.warning("openFDA adverse-event request failed: %s", type(exc).__name__)
                raise OpenFdaError("openFDA adverse-event data could not be reached right now.") from exc

        if response.status_code == 404:
            return AdverseEventDataset(reports=[], available_reports=0)
        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            message = payload.get("error", {}).get("message") or (
                "openFDA returned an unexpected adverse-event error."
            )
            logger.warning(
                "openFDA adverse-event request returned status %s", response.status_code
            )
            raise OpenFdaError(message)

        try:
            payload = response.json()
        except ValueError as exc:
            raise OpenFdaError("openFDA returned an invalid adverse-event response.") from exc

        if not isinstance(payload, dict):
            raise OpenFdaError("openFDA returned an invalid adverse-event response.")

        results = payload.get("results", [])
        if not isinstance(results, list):
            raise OpenFdaError("openFDA returned an invalid adverse-event response.")

        meta = payload.get("meta", {})
        meta_results = meta.get("results", {}) if isinstance(meta, dict) else {}
        available_reports = meta_results.get("total", len(results))
        try:
            available_count = int(available_reports)
        except (TypeError, ValueError):
            available_count = len(results)

        reports = [parse_adverse_event_report(item) for item in results if isinstance(item, dict)]
        return AdverseEventDataset(
            reports=reports,
            available_reports=max(available_count, len(reports)),
        )


def get_adverse_event_client() -> AdverseEventClient:
    return AdverseEventClient()
