from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

from app.config import settings


OPENFDA_NDC_URL = "https://api.fda.gov/drug/ndc.json"
OPENFDA_DEVICE_UDI_URL = "https://api.fda.gov/device/udi.json"
NAME_QUERY_MIN_LENGTH = 2
PRODUCT_NDC_PATTERNS = ((4, 4), (5, 3), (5, 4))
PACKAGE_NDC_PATTERNS = ((4, 4, 2), (5, 3, 2), (5, 4, 1), (5, 4, 2))
NDC_ALLOWED_PATTERN = re.compile(r"^[0-9-]+$")
UDI_DI_PATTERN = re.compile(r"\(01\)\s*([0-9]{14})")
DEVICE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9\-().\s+/]+$")


class SearchValidationError(ValueError):
    """Raised when a user search cannot be converted into an openFDA query."""


class OpenFdaError(RuntimeError):
    """Raised when the upstream openFDA service cannot fulfill a request."""


@dataclass(frozen=True)
class DrugRecord:
    brand_name: str
    generic_name: str
    labeler_name: str
    product_ndc: str
    package_ndcs: list[str]
    package_descriptions: list[str]
    active_ingredients: list[str]
    route: list[str]
    dosage_form: str
    marketing_category: str
    product_type: str
    application_number: str
    listing_expiration_date: str
    marketing_start_date: str
    finished: bool | None


@dataclass(frozen=True)
class DrugMatch:
    brand_name: str
    generic_name: str
    labeler_name: str
    product_ndc: str
    dosage_form: str
    product_type: str
    marketing_category: str


@dataclass(frozen=True)
class DeviceRecord:
    record_key: str
    device_identifier: str
    brand_name: str
    company_name: str
    version_or_model_number: str
    catalog_number: str
    device_description: str
    product_codes: list[str]
    commercial_distribution_status: str
    prescription_otc_status: str
    single_use_indicator: str
    sterility_information: str
    mri_safety_information: str
    implantable_device_indicator: str
    latex_information: str
    storage_and_handling_conditions: list[str]
    packaging_configurations: list[str]


@dataclass(frozen=True)
class DeviceMatch:
    record_key: str
    device_identifier: str
    brand_name: str
    company_name: str
    version_or_model_number: str
    catalog_number: str
    product_code: str


@dataclass(frozen=True)
class SearchPageData:
    query: str = ""
    error: str | None = None
    result: DrugRecord | None = None
    matches: list[DrugMatch] = field(default_factory=list)
    selected_product_ndc: str = ""
    chat_messages: list[Any] = field(default_factory=list)
    chat_input: str = ""
    chat_notice: str | None = None
    competitive_summary: str | None = None
    competitive_summary_model: str | None = None


@dataclass(frozen=True)
class DeviceSearchPageData:
    query: str = ""
    error: str | None = None
    result: DeviceRecord | None = None
    matches: list[DeviceMatch] = field(default_factory=list)
    selected_record_key: str = ""
    chat_messages: list[Any] = field(default_factory=list)
    chat_input: str = ""
    chat_notice: str | None = None
    device_summary: str | None = None
    device_summary_model: str | None = None


def _escape_query_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _format_date(raw_value: str) -> str:
    if len(raw_value) != 8 or not raw_value.isdigit():
        return raw_value or "Not available"

    try:
        return datetime.strptime(raw_value, "%Y%m%d").strftime("%B %d, %Y")
    except ValueError:
        return raw_value


def _format_active_ingredients(items: list[dict[str, Any]]) -> list[str]:
    formatted: list[str] = []
    for item in items:
        name = str(item.get("name", "")).strip()
        strength = str(item.get("strength", "")).strip()
        if not name:
            continue
        formatted.append(f"{name} ({strength})" if strength else name)
    return formatted


def _string_or_not_available(value: Any) -> str:
    text = str(value).strip()
    return text or "Not available"


def _boolish_to_label(value: Any, *, true_label: str, false_label: str) -> str:
    normalized = str(value).strip().lower()
    if normalized == "true":
        return true_label
    if normalized == "false":
        return false_label
    return "Not available"


def _product_codes(payload: dict[str, Any]) -> list[str]:
    codes = payload.get("product_codes", []) or []
    formatted: list[str] = []
    for item in codes:
        code = str(item.get("code", "")).strip()
        name = str(item.get("name", "")).strip()
        if code and name:
            formatted.append(f"{code} - {name}")
        elif code:
            formatted.append(code)
    return formatted


def _device_identifier_from_identifiers(payload: dict[str, Any]) -> str:
    identifiers = payload.get("identifiers", []) or []
    for item in identifiers:
        if str(item.get("type", "")).strip().lower() == "primary":
            identifier = str(item.get("id", "")).strip()
            if identifier:
                return identifier
    for item in identifiers:
        identifier = str(item.get("id", "")).strip()
        if identifier:
            return identifier
    return "Not available"


def _sterility_information(payload: dict[str, Any]) -> str:
    sterilization = payload.get("sterilization")
    if not isinstance(sterilization, dict):
        return "Not available"

    bits: list[str] = []
    sterile = _boolish_to_label(
        sterilization.get("is_sterile"),
        true_label="Sterile",
        false_label="Not labeled as sterile",
    )
    if sterile != "Not available":
        bits.append(sterile)

    prior_use = _boolish_to_label(
        sterilization.get("is_sterilization_prior_use"),
        true_label="Sterilization required before use",
        false_label="No sterilization-before-use statement",
    )
    if prior_use != "Not available":
        bits.append(prior_use)

    methods = sterilization.get("sterilization_methods", []) or []
    method_values = [str(item).strip() for item in methods if str(item).strip()]
    if method_values:
        bits.append(f"Methods: {', '.join(method_values)}")

    return "; ".join(bits) if bits else "Not available"


def _implantable_indicator(payload: dict[str, Any]) -> str:
    gmdn_terms = payload.get("gmdn_terms", []) or []
    implantable_values = {str(item.get("implantable", "")).strip().lower() for item in gmdn_terms}
    if "true" in implantable_values:
        return "Implantable"
    if "false" in implantable_values and implantable_values != {""}:
        return "Not implantable"
    return "Not available"


def _latex_information(payload: dict[str, Any]) -> str:
    no_nrl = str(payload.get("is_labeled_as_no_nrl", "")).strip().lower()
    has_nrl = str(payload.get("is_labeled_as_nrl", "")).strip().lower()
    if no_nrl == "true":
        return "Labeled as not made with natural rubber latex"
    if has_nrl == "true":
        return "Labeled as containing natural rubber latex"
    return "Not available"


def _storage_conditions(payload: dict[str, Any]) -> list[str]:
    storage = payload.get("storage", []) or []
    formatted: list[str] = []
    for item in storage:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type", "")).strip()
        value = str(item.get("value", "")).strip()
        unit = str(item.get("unit", "")).strip()
        text = str(item.get("text", "")).strip()
        if item_type and value:
            suffix = f" {unit}" if unit else ""
            formatted.append(f"{item_type}: {value}{suffix}")
        elif item_type and text:
            formatted.append(f"{item_type}: {text}")
        elif text:
            formatted.append(text)
    return formatted


def _packaging_configurations(payload: dict[str, Any]) -> list[str]:
    identifiers = payload.get("identifiers", []) or []
    configurations: list[str] = []
    for item in identifiers:
        identifier = str(item.get("id", "")).strip()
        item_type = str(item.get("type", "")).strip()
        agency = str(item.get("issuing_agency", "")).strip()
        if not identifier:
            continue
        label_bits = [bit for bit in [item_type, agency] if bit]
        if label_bits:
            configurations.append(f"{identifier} ({', '.join(label_bits)})")
        else:
            configurations.append(identifier)

    count = str(payload.get("device_count_in_base_package", "")).strip()
    if count:
        configurations.append(f"Base package count: {count}")
    return configurations


def build_name_search(query: str) -> str:
    stripped = query.strip()
    if len(stripped) < NAME_QUERY_MIN_LENGTH:
        raise SearchValidationError("Product names must be at least 2 characters.")

    escaped = _escape_query_value(stripped)
    return (
        f'brand_name:"{escaped}" OR '
        f'brand_name_base:"{escaped}" OR '
        f'generic_name:"{escaped}"'
    )


def build_ndc_search(query: str) -> str:
    compact = query.strip().replace(" ", "")
    if not compact:
        raise SearchValidationError("Enter a product name or NDC code.")
    if not NDC_ALLOWED_PATTERN.fullmatch(compact):
        raise SearchValidationError("NDC codes may only contain digits and hyphens.")

    digits_only = compact.replace("-", "")
    hyphen_count = compact.count("-")
    if len(digits_only) < 7 or len(digits_only) > 11:
        raise SearchValidationError("NDC codes must contain between 7 and 11 digits.")

    clauses: list[str] = []
    seen: set[str] = set()

    def add_clause(value: str, *, package_only: bool = False) -> None:
        if package_only:
            candidates = [f"package_ndc:{value}"]
        else:
            candidates = [f"product_ndc:{value}", f"package_ndc:{value}"]
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                clauses.append(candidate)

    if hyphen_count == 1:
        add_clause(compact, package_only=False)
        return " OR ".join(clauses)

    if hyphen_count == 2:
        parts = compact.split("-")
        if len(parts) == 3 and all(parts):
            add_clause("-".join(parts[:2]), package_only=False)
            add_clause(compact, package_only=True)
            return " OR ".join(clauses)

    if len(digits_only) in {7, 8, 9}:
        for pattern in PRODUCT_NDC_PATTERNS:
            if sum(pattern) != len(digits_only):
                continue
            parts: list[str] = []
            cursor = 0
            for size in pattern:
                parts.append(digits_only[cursor : cursor + size])
                cursor += size
            add_clause("-".join(parts), package_only=False)
        return " OR ".join(clauses)

    patterns = PACKAGE_NDC_PATTERNS if len(digits_only) == 10 else ((5, 4, 2),)
    for pattern in patterns:
        if sum(pattern) != len(digits_only):
            continue
        parts = []
        cursor = 0
        for size in pattern:
            parts.append(digits_only[cursor : cursor + size])
            cursor += size
        if len(parts) == 3:
            add_clause("-".join(parts[:2]), package_only=False)
            add_clause("-".join(parts), package_only=True)

    return " OR ".join(clauses)


def build_openfda_search(query: str) -> str:
    stripped = query.strip()
    if not stripped:
        raise SearchValidationError("Enter a product name or NDC code.")

    if any(character.isalpha() for character in stripped):
        return build_name_search(stripped)

    return build_ndc_search(stripped)


def _extract_device_identifier_candidates(query: str) -> list[str]:
    stripped = query.strip()
    candidates: list[str] = []

    match = UDI_DI_PATTERN.search(stripped)
    if match:
        candidates.append(match.group(1))

    collapsed = re.sub(r"[^A-Za-z0-9]", "", stripped).upper()
    if collapsed and any(character.isdigit() for character in collapsed):
        candidates.append(collapsed)

    seen: set[str] = set()
    return [value for value in candidates if not (value in seen or seen.add(value))]


def build_device_search(query: str) -> str:
    stripped = query.strip()
    if len(stripped) < NAME_QUERY_MIN_LENGTH:
        raise SearchValidationError("Device searches must be at least 2 characters.")
    if not DEVICE_IDENTIFIER_PATTERN.fullmatch(stripped):
        raise SearchValidationError(
            "Device searches may only contain letters, digits, spaces, and common barcode symbols."
        )

    escaped = _escape_query_value(stripped)
    clauses = [
        f'brand_name.exact:"{escaped}"',
        f'brand_name:"{escaped}"',
        f'version_or_model_number:"{escaped}"',
        f'catalog_number:"{escaped}"',
    ]

    for candidate in _extract_device_identifier_candidates(stripped):
        escaped_candidate = _escape_query_value(candidate)
        clauses.append(f'identifiers.id:"{escaped_candidate}"')

    seen: set[str] = set()
    return " OR ".join([clause for clause in clauses if not (clause in seen or seen.add(clause))])


def parse_drug_record(payload: dict[str, Any]) -> DrugRecord:
    packaging = payload.get("packaging", []) or []
    active_ingredients = payload.get("active_ingredients", []) or []
    route = payload.get("route", []) or []

    return DrugRecord(
        brand_name=str(payload.get("brand_name", "")).strip() or "Not available",
        generic_name=str(payload.get("generic_name", "")).strip() or "Not available",
        labeler_name=str(payload.get("labeler_name", "")).strip() or "Not available",
        product_ndc=str(payload.get("product_ndc", "")).strip() or "Not available",
        package_ndcs=[
            str(item.get("package_ndc", "")).strip()
            for item in packaging
            if str(item.get("package_ndc", "")).strip()
        ],
        package_descriptions=[
            str(item.get("description", "")).strip()
            for item in packaging
            if str(item.get("description", "")).strip()
        ],
        active_ingredients=_format_active_ingredients(active_ingredients),
        route=[str(item).strip() for item in route if str(item).strip()],
        dosage_form=str(payload.get("dosage_form", "")).strip() or "Not available",
        marketing_category=(
            str(payload.get("marketing_category", "")).strip() or "Not available"
        ),
        product_type=str(payload.get("product_type", "")).strip() or "Not available",
        application_number=(
            str(payload.get("application_number", "")).strip() or "Not available"
        ),
        listing_expiration_date=_format_date(
            str(payload.get("listing_expiration_date", "")).strip()
        ),
        marketing_start_date=_format_date(
            str(payload.get("marketing_start_date", "")).strip()
        ),
        finished=payload.get("finished"),
    )


def parse_drug_match(payload: dict[str, Any]) -> DrugMatch:
    return DrugMatch(
        brand_name=str(payload.get("brand_name", "")).strip() or "Not available",
        generic_name=str(payload.get("generic_name", "")).strip() or "Not available",
        labeler_name=str(payload.get("labeler_name", "")).strip() or "Not available",
        product_ndc=str(payload.get("product_ndc", "")).strip() or "Not available",
        dosage_form=str(payload.get("dosage_form", "")).strip() or "Not available",
        product_type=str(payload.get("product_type", "")).strip() or "Not available",
        marketing_category=(
            str(payload.get("marketing_category", "")).strip() or "Not available"
        ),
    )


def parse_device_record(payload: dict[str, Any]) -> DeviceRecord:
    return DeviceRecord(
        record_key=_string_or_not_available(payload.get("public_device_record_key")),
        device_identifier=_device_identifier_from_identifiers(payload),
        brand_name=_string_or_not_available(payload.get("brand_name")),
        company_name=_string_or_not_available(payload.get("company_name")),
        version_or_model_number=_string_or_not_available(payload.get("version_or_model_number")),
        catalog_number=_string_or_not_available(payload.get("catalog_number")),
        device_description=_string_or_not_available(payload.get("device_description")),
        product_codes=_product_codes(payload),
        commercial_distribution_status=_string_or_not_available(
            payload.get("commercial_distribution_status")
        ),
        prescription_otc_status=_prescription_otc_status(payload),
        single_use_indicator=_boolish_to_label(
            payload.get("is_single_use"),
            true_label="Single use",
            false_label="Not labeled as single use",
        ),
        sterility_information=_sterility_information(payload),
        mri_safety_information=_string_or_not_available(payload.get("mri_safety")),
        implantable_device_indicator=_implantable_indicator(payload),
        latex_information=_latex_information(payload),
        storage_and_handling_conditions=_storage_conditions(payload),
        packaging_configurations=_packaging_configurations(payload),
    )


def _prescription_otc_status(payload: dict[str, Any]) -> str:
    is_rx = str(payload.get("is_rx", "")).strip().lower()
    is_otc = str(payload.get("is_otc", "")).strip().lower()
    if is_rx == "true" and is_otc == "true":
        return "Prescription and over the counter"
    if is_rx == "true":
        return "Prescription"
    if is_otc == "true":
        return "Over the counter"
    if is_rx == "false" and is_otc == "false":
        return "Not labeled as prescription or over the counter"
    return "Not available"


def parse_device_match(payload: dict[str, Any]) -> DeviceMatch:
    codes = _product_codes(payload)
    return DeviceMatch(
        record_key=_string_or_not_available(payload.get("public_device_record_key")),
        device_identifier=_device_identifier_from_identifiers(payload),
        brand_name=_string_or_not_available(payload.get("brand_name")),
        company_name=_string_or_not_available(payload.get("company_name")),
        version_or_model_number=_string_or_not_available(payload.get("version_or_model_number")),
        catalog_number=_string_or_not_available(payload.get("catalog_number")),
        product_code=codes[0] if codes else "Not available",
    )


class OpenFdaClient:
    async def search_matches(self, query: str, *, limit: int = 8) -> list[DrugMatch]:
        search_expression = build_openfda_search(query)
        payload = await self._request(OPENFDA_NDC_URL, search_expression, limit=limit)
        results = payload.get("results", [])
        return [parse_drug_match(result) for result in results]

    async def get_product(self, product_ndc: str) -> DrugRecord | None:
        payload = await self._request(OPENFDA_NDC_URL, f"product_ndc:{product_ndc}", limit=1)
        results = payload.get("results", [])
        if not results:
            return None
        return parse_drug_record(results[0])

    async def search_device_matches(self, query: str, *, limit: int = 8) -> list[DeviceMatch]:
        search_expression = build_device_search(query)
        payload = await self._request(OPENFDA_DEVICE_UDI_URL, search_expression, limit=limit)
        results = payload.get("results", [])
        return [parse_device_match(result) for result in results]

    async def get_device(self, record_key: str) -> DeviceRecord | None:
        payload = await self._request(
            OPENFDA_DEVICE_UDI_URL,
            f'public_device_record_key:"{_escape_query_value(record_key)}"',
            limit=1,
        )
        results = payload.get("results", [])
        if not results:
            return None
        return parse_device_record(results[0])

    async def _request(self, url: str, search_expression: str, *, limit: int) -> dict[str, Any]:
        params = {
            "search": search_expression,
            "limit": limit,
        }
        if settings.openfda_api_key:
            params["api_key"] = settings.openfda_api_key

        timeout = httpx.Timeout(10.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.get(url, params=params)
            except httpx.HTTPError as exc:
                raise OpenFdaError("openFDA could not be reached right now.") from exc

        if response.status_code == 404:
            return {}

        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            message = (
                payload.get("error", {}).get("message")
                or "openFDA returned an unexpected error."
            )
            raise OpenFdaError(message)

        return response.json()


def get_openfda_client() -> OpenFdaClient:
    return OpenFdaClient()
