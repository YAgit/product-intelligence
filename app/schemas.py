from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DomainModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DrugMatchResponse(DomainModel):
    brand_name: str
    generic_name: str
    labeler_name: str
    product_ndc: str
    dosage_form: str
    product_type: str
    marketing_category: str


class DrugResponse(DrugMatchResponse):
    package_ndcs: list[str]
    package_descriptions: list[str]
    active_ingredients: list[str]
    route: list[str]
    application_number: str
    listing_expiration_date: str
    marketing_start_date: str
    finished: bool | None


class DrugSearchResponse(BaseModel):
    query: str
    matches: list[DrugMatchResponse]


class DeviceMatchResponse(DomainModel):
    record_key: str
    device_identifier: str
    brand_name: str
    company_name: str
    version_or_model_number: str
    catalog_number: str
    product_code: str


class DeviceResponse(DomainModel):
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


class DeviceSearchResponse(BaseModel):
    query: str
    matches: list[DeviceMatchResponse]


class ChatMessageRequest(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatMessageRequest] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    content: str
    model_id: str | None
    used_fallback: bool
    error: str | None


class HealthResponse(BaseModel):
    status: Literal["ok"]


class AdverseEventMatchingResponse(BaseModel):
    field: str
    value: str
    start_date: date
    end_date: date


class AdverseEventRetrievalResponse(BaseModel):
    retrieved_reports: int
    available_reports: int
    retrieval_limit: int
    truncated: bool
    sort: str


class AdverseEventOverviewResponse(BaseModel):
    total_reports: int
    serious_reports: int
    non_serious_reports: int
    serious_percentage: float
    reporting_period_start: date | None
    reporting_period_end: date | None


class SeriousOutcomeResponse(BaseModel):
    outcome: str
    label: str
    report_count: int


class AdverseEventTrendResponse(BaseModel):
    period: str
    total_reports: int
    serious_reports: int


class AdverseEventReactionResponse(BaseModel):
    term: str
    report_count: int
    report_percentage: float
    serious_report_count: int


class AdverseEventAnalyticsResponse(BaseModel):
    matching: AdverseEventMatchingResponse
    retrieval: AdverseEventRetrievalResponse
    overview: AdverseEventOverviewResponse
    outcomes: list[SeriousOutcomeResponse]
    trends: list[AdverseEventTrendResponse]
    reactions: list[AdverseEventReactionResponse]
    limitations: list[str]
    source: str
