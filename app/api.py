from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.adverse_events import (
    AdverseEventClient,
    calculate_adverse_event_analytics,
    get_adverse_event_client,
)
from app.chatbot import ChatMessage, ChatReply, PharmaChatbotClient, get_chatbot_client
from app.openfda import (
    DeviceRecord,
    DrugRecord,
    OpenFdaClient,
    OpenFdaError,
    SearchValidationError,
    get_openfda_client,
)
from app.schemas import (
    AdverseEventAnalyticsResponse,
    AnalysisResponse,
    ChatRequest,
    DeviceResponse,
    DeviceSearchResponse,
    DrugResponse,
    DrugSearchResponse,
    HealthResponse,
)


router = APIRouter(prefix="/api/v1")


def _fda_error(exc: Exception) -> HTTPException:
    if isinstance(exc, SearchValidationError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"FDA service error: {exc}",
    )


def _analysis_response(reply: ChatReply) -> AnalysisResponse:
    return AnalysisResponse(
        content=reply.content,
        model_id=reply.model_id,
        used_fallback=reply.used_fallback,
        error=reply.error,
    )


@router.get("/health", response_model=HealthResponse)
async def api_health() -> HealthResponse:
    return HealthResponse(status="ok")


async def _get_drug(openfda_client: OpenFdaClient, product_ndc: str) -> DrugRecord:
    try:
        drug = await openfda_client.get_product(product_ndc)
    except (SearchValidationError, OpenFdaError) as exc:
        raise _fda_error(exc) from exc
    if drug is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drug not found.")
    return drug


async def _get_device(openfda_client: OpenFdaClient, record_key: str) -> DeviceRecord:
    try:
        device = await openfda_client.get_device(record_key)
    except (SearchValidationError, OpenFdaError) as exc:
        raise _fda_error(exc) from exc
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    return device


@router.get("/drugs/search", response_model=DrugSearchResponse)
async def search_drugs(
    query: Annotated[str, Query(min_length=1)],
    openfda_client: OpenFdaClient = Depends(get_openfda_client),
) -> DrugSearchResponse:
    normalized_query = query.strip()
    try:
        matches = await openfda_client.search_matches(normalized_query)
    except (SearchValidationError, OpenFdaError) as exc:
        raise _fda_error(exc) from exc
    return DrugSearchResponse(query=normalized_query, matches=matches)


@router.get("/drugs/{product_ndc}", response_model=DrugResponse)
async def get_drug(
    product_ndc: str,
    openfda_client: OpenFdaClient = Depends(get_openfda_client),
) -> DrugRecord:
    return await _get_drug(openfda_client, product_ndc.strip())


@router.post("/drugs/{product_ndc}/summary", response_model=AnalysisResponse)
async def summarize_drug(
    product_ndc: str,
    openfda_client: OpenFdaClient = Depends(get_openfda_client),
    chatbot_client: PharmaChatbotClient = Depends(get_chatbot_client),
) -> AnalysisResponse:
    drug = await _get_drug(openfda_client, product_ndc.strip())
    return _analysis_response(await chatbot_client.summarize_product(drug))


@router.post("/drugs/{product_ndc}/chat", response_model=AnalysisResponse)
async def chat_about_drug(
    product_ndc: str,
    request: ChatRequest,
    openfda_client: OpenFdaClient = Depends(get_openfda_client),
    chatbot_client: PharmaChatbotClient = Depends(get_chatbot_client),
) -> AnalysisResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Enter a pharmaceutical product question.",
        )
    drug = await _get_drug(openfda_client, product_ndc.strip())
    history = [ChatMessage(role=item.role, content=item.content) for item in request.history]
    return _analysis_response(await chatbot_client.answer(message, drug, history))


@router.get(
    "/drugs/{product_ndc}/adverse-events",
    response_model=AdverseEventAnalyticsResponse,
)
async def get_drug_adverse_events(
    product_ndc: str,
    start_date: date,
    end_date: date,
    openfda_client: OpenFdaClient = Depends(get_openfda_client),
    adverse_event_client: AdverseEventClient = Depends(get_adverse_event_client),
) -> AdverseEventAnalyticsResponse:
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The adverse-event start date must be on or before the end date.",
        )

    drug = await _get_drug(openfda_client, product_ndc.strip())
    if not drug.brand_name or drug.brand_name == "Not available":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The selected drug does not have a brand name for FAERS matching.",
        )

    try:
        dataset = await adverse_event_client.get_reports(
            drug.brand_name,
            start_date,
            end_date,
        )
    except OpenFdaError as exc:
        raise _fda_error(exc) from exc

    analytics = calculate_adverse_event_analytics(
        dataset,
        brand_name=drug.brand_name,
        start_date=start_date,
        end_date=end_date,
    )
    return AdverseEventAnalyticsResponse.model_validate(analytics)


@router.get("/devices/search", response_model=DeviceSearchResponse)
async def search_devices(
    query: Annotated[str, Query(min_length=1)],
    openfda_client: OpenFdaClient = Depends(get_openfda_client),
) -> DeviceSearchResponse:
    normalized_query = query.strip()
    try:
        matches = await openfda_client.search_device_matches(normalized_query)
    except (SearchValidationError, OpenFdaError) as exc:
        raise _fda_error(exc) from exc
    return DeviceSearchResponse(query=normalized_query, matches=matches)


@router.get("/devices/{record_key}", response_model=DeviceResponse)
async def get_device(
    record_key: str,
    openfda_client: OpenFdaClient = Depends(get_openfda_client),
) -> DeviceRecord:
    return await _get_device(openfda_client, record_key.strip())


@router.post("/devices/{record_key}/summary", response_model=AnalysisResponse)
async def summarize_device(
    record_key: str,
    openfda_client: OpenFdaClient = Depends(get_openfda_client),
    chatbot_client: PharmaChatbotClient = Depends(get_chatbot_client),
) -> AnalysisResponse:
    device = await _get_device(openfda_client, record_key.strip())
    return _analysis_response(await chatbot_client.summarize_device(device))


@router.post("/devices/{record_key}/chat", response_model=AnalysisResponse)
async def chat_about_device(
    record_key: str,
    request: ChatRequest,
    openfda_client: OpenFdaClient = Depends(get_openfda_client),
    chatbot_client: PharmaChatbotClient = Depends(get_chatbot_client),
) -> AnalysisResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Enter a medical-device question.",
        )
    device = await _get_device(openfda_client, record_key.strip())
    history = [ChatMessage(role=item.role, content=item.content) for item in request.history]
    return _analysis_response(await chatbot_client.answer_device(message, device, history))
