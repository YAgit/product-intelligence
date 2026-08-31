from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.chatbot import ChatMessage, ChatReply, PharmaChatbotClient, get_chatbot_client
from app.config import settings
from app.openfda import (
    DeviceSearchPageData,
    OpenFdaClient,
    OpenFdaError,
    SearchPageData,
    SearchValidationError,
    get_openfda_client,
)


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _render_drug_page(request: Request, page_data: SearchPageData) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.app_name,
            "has_openrouter_key": bool(settings.openrouter_api_key),
            "has_openfda_key": bool(settings.openfda_api_key),
            "page": page_data,
            "active_tab": "drug",
        },
    )


def _render_device_page(request: Request, page_data: DeviceSearchPageData) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="device.html",
        context={
            "app_name": settings.app_name,
            "has_openrouter_key": bool(settings.openrouter_api_key),
            "has_openfda_key": bool(settings.openfda_api_key),
            "page": page_data,
            "active_tab": "device",
        },
    )


@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    query: str = "",
    product_ndc: str = "",
    openfda_client: OpenFdaClient = Depends(get_openfda_client),
    chatbot_client: PharmaChatbotClient = Depends(get_chatbot_client),
) -> HTMLResponse:
    page_data = SearchPageData(
        query=query.strip(),
        selected_product_ndc=product_ndc.strip(),
        matches=[],
        chat_messages=[],
    )
    if page_data.query:
        try:
            matches = await openfda_client.search_matches(page_data.query)
        except SearchValidationError as exc:
            page_data = SearchPageData(query=page_data.query, error=str(exc))
        except OpenFdaError as exc:
            page_data = SearchPageData(
                query=page_data.query,
                error=f"FDA lookup failed: {exc}",
            )
        else:
            if not matches:
                page_data = SearchPageData(
                    query=page_data.query,
                    error="No FDA NDC matches were found for that search.",
                    matches=[],
                    chat_messages=[],
                )
            elif page_data.selected_product_ndc:
                try:
                    result = await openfda_client.get_product(page_data.selected_product_ndc)
                except OpenFdaError as exc:
                    page_data = SearchPageData(
                        query=page_data.query,
                        selected_product_ndc=page_data.selected_product_ndc,
                        matches=matches,
                        error=f"FDA lookup failed: {exc}",
                        chat_messages=[],
                    )
                else:
                    if result is None:
                        page_data = SearchPageData(
                            query=page_data.query,
                            selected_product_ndc=page_data.selected_product_ndc,
                            matches=matches,
                            error="The selected FDA product could not be loaded.",
                            chat_messages=[],
                        )
                    else:
                        summary = await chatbot_client.summarize_product(result)
                        page_data = SearchPageData(
                            query=page_data.query,
                            selected_product_ndc=page_data.selected_product_ndc,
                            matches=matches,
                            result=result,
                            chat_messages=[],
                            competitive_summary=summary.content,
                            competitive_summary_model=summary.model_id,
                            chat_notice=(
                                "Anthropic was unavailable, so OpenAI produced the product summary."
                                if summary.used_fallback
                                else None
                            ),
                        )
            elif len(matches) == 1:
                selected = matches[0]
                result = await openfda_client.get_product(selected.product_ndc)
                summary = await chatbot_client.summarize_product(result) if result else None
                page_data = SearchPageData(
                    query=page_data.query,
                    selected_product_ndc=selected.product_ndc,
                    matches=matches,
                    result=result,
                    chat_messages=[],
                    competitive_summary=summary.content if summary else None,
                    competitive_summary_model=summary.model_id if summary else None,
                    chat_notice=(
                        "Anthropic was unavailable, so OpenAI produced the product summary."
                        if summary and summary.used_fallback
                        else None
                    ),
                )
            else:
                page_data = SearchPageData(
                    query=page_data.query,
                    matches=matches,
                    selected_product_ndc="",
                    chat_notice="Multiple products matched. Select the exact product to continue.",
                    chat_messages=[],
                )

    return _render_drug_page(request, page_data)


@app.post("/chat", response_class=HTMLResponse)
async def chat(
    request: Request,
    query: str = Form(""),
    product_ndc: str = Form(""),
    message: str = Form(""),
    competitive_summary: str = Form(""),
    competitive_summary_model: str = Form(""),
    history_roles: list[str] = Form(default=[]),
    history_contents: list[str] = Form(default=[]),
    openfda_client: OpenFdaClient = Depends(get_openfda_client),
    chatbot_client: PharmaChatbotClient = Depends(get_chatbot_client),
) -> HTMLResponse:
    page_data = SearchPageData(
        query=query.strip(),
        selected_product_ndc=product_ndc.strip(),
        matches=[],
        chat_messages=[],
        chat_input=message.strip(),
    )
    prior_messages = [
        ChatMessage(role=role, content=content)
        for role, content in zip(history_roles, history_contents, strict=False)
        if role in {"user", "assistant"} and content.strip()
    ]

    if not page_data.query or not page_data.selected_product_ndc:
        page_data = SearchPageData(
            query=page_data.query,
            selected_product_ndc=page_data.selected_product_ndc,
            error="Select a pharmaceutical product before using the chatbot.",
            matches=[],
            chat_messages=prior_messages,
            chat_input=page_data.chat_input,
        )
    elif not page_data.chat_input:
        page_data = SearchPageData(
            query=page_data.query,
            selected_product_ndc=page_data.selected_product_ndc,
            error="Enter a pharma product question for the chatbot.",
            matches=[],
            chat_messages=prior_messages,
        )
    else:
        try:
            result = await openfda_client.get_product(page_data.selected_product_ndc)
        except (SearchValidationError, OpenFdaError) as exc:
            page_data = SearchPageData(
                query=page_data.query,
                selected_product_ndc=page_data.selected_product_ndc,
                error=f"FDA lookup failed: {exc}",
                matches=[],
                chat_messages=prior_messages,
                chat_input=page_data.chat_input,
            )
        else:
            if result is None:
                page_data = SearchPageData(
                    query=page_data.query,
                    selected_product_ndc=page_data.selected_product_ndc,
                    error="The selected FDA product could not be loaded.",
                    matches=[],
                    chat_messages=prior_messages,
                )
            else:
                cached_summary = competitive_summary.strip()
                cached_summary_model = competitive_summary_model.strip() or None
                if cached_summary:
                    summary = ChatReply(
                        model_id=cached_summary_model,
                        content=cached_summary,
                    )
                    reply = await chatbot_client.answer(page_data.chat_input, result, prior_messages)
                else:
                    summary, reply = await asyncio.gather(
                        chatbot_client.summarize_product(result),
                        chatbot_client.answer(page_data.chat_input, result, prior_messages),
                    )
                updated_messages = [
                    *prior_messages,
                    ChatMessage(role="user", content=page_data.chat_input),
                    ChatMessage(role="assistant", content=reply.content),
                ]
                notices: list[str] = []
                if summary.used_fallback:
                    notices.append("Anthropic was unavailable, so OpenAI produced the product summary.")
                if reply.used_fallback:
                    notices.append("Anthropic was unavailable, so the chatbot used OpenAI for this reply.")
                page_data = SearchPageData(
                    query=page_data.query,
                    selected_product_ndc=page_data.selected_product_ndc,
                    matches=[],
                    result=result,
                    chat_messages=updated_messages,
                    chat_notice=" ".join(notices) if notices else reply.error,
                    competitive_summary=summary.content,
                    competitive_summary_model=summary.model_id,
                )

    return _render_drug_page(request, page_data)


@app.get("/devices", response_class=HTMLResponse)
async def devices(
    request: Request,
    query: str = "",
    record_key: str = "",
    openfda_client: OpenFdaClient = Depends(get_openfda_client),
    chatbot_client: PharmaChatbotClient = Depends(get_chatbot_client),
) -> HTMLResponse:
    page_data = DeviceSearchPageData(
        query=query.strip(),
        selected_record_key=record_key.strip(),
        matches=[],
        chat_messages=[],
    )
    if page_data.query:
        try:
            matches = await openfda_client.search_device_matches(page_data.query)
        except SearchValidationError as exc:
            page_data = DeviceSearchPageData(query=page_data.query, error=str(exc))
        except OpenFdaError as exc:
            page_data = DeviceSearchPageData(
                query=page_data.query,
                error=f"FDA device lookup failed: {exc}",
            )
        else:
            if not matches:
                page_data = DeviceSearchPageData(
                    query=page_data.query,
                    error="No FDA device matches were found for that search.",
                )
            elif page_data.selected_record_key:
                try:
                    result = await openfda_client.get_device(page_data.selected_record_key)
                except OpenFdaError as exc:
                    page_data = DeviceSearchPageData(
                        query=page_data.query,
                        selected_record_key=page_data.selected_record_key,
                        matches=matches,
                        error=f"FDA device lookup failed: {exc}",
                    )
                else:
                    if result is None:
                        page_data = DeviceSearchPageData(
                            query=page_data.query,
                            selected_record_key=page_data.selected_record_key,
                            matches=matches,
                            error="The selected FDA device could not be loaded.",
                        )
                    else:
                        summary = await chatbot_client.summarize_device(result)
                        page_data = DeviceSearchPageData(
                            query=page_data.query,
                            selected_record_key=page_data.selected_record_key,
                            matches=matches,
                            result=result,
                            device_summary=summary.content,
                            device_summary_model=summary.model_id,
                            chat_notice=(
                                "Anthropic was unavailable, so OpenAI produced the device summary."
                                if summary.used_fallback
                                else None
                            ),
                        )
            elif len(matches) == 1:
                selected = matches[0]
                result = await openfda_client.get_device(selected.record_key)
                summary = await chatbot_client.summarize_device(result) if result else None
                page_data = DeviceSearchPageData(
                    query=page_data.query,
                    selected_record_key=selected.record_key,
                    matches=matches,
                    result=result,
                    device_summary=summary.content if summary else None,
                    device_summary_model=summary.model_id if summary else None,
                    chat_notice=(
                        "Anthropic was unavailable, so OpenAI produced the device summary."
                        if summary and summary.used_fallback
                        else None
                    ),
                )
            else:
                page_data = DeviceSearchPageData(
                    query=page_data.query,
                    matches=matches,
                    chat_notice="Multiple devices matched. Select the exact device to continue.",
                )

    return _render_device_page(request, page_data)


@app.post("/devices/chat", response_class=HTMLResponse)
async def device_chat(
    request: Request,
    query: str = Form(""),
    record_key: str = Form(""),
    message: str = Form(""),
    device_summary: str = Form(""),
    device_summary_model: str = Form(""),
    history_roles: list[str] = Form(default=[]),
    history_contents: list[str] = Form(default=[]),
    openfda_client: OpenFdaClient = Depends(get_openfda_client),
    chatbot_client: PharmaChatbotClient = Depends(get_chatbot_client),
) -> HTMLResponse:
    page_data = DeviceSearchPageData(
        query=query.strip(),
        selected_record_key=record_key.strip(),
        matches=[],
        chat_messages=[],
        chat_input=message.strip(),
    )
    prior_messages = [
        ChatMessage(role=role, content=content)
        for role, content in zip(history_roles, history_contents, strict=False)
        if role in {"user", "assistant"} and content.strip()
    ]

    if not page_data.query or not page_data.selected_record_key:
        page_data = DeviceSearchPageData(
            query=page_data.query,
            selected_record_key=page_data.selected_record_key,
            error="Select an FDA device before using the chatbot.",
            chat_messages=prior_messages,
            chat_input=page_data.chat_input,
        )
    elif not page_data.chat_input:
        page_data = DeviceSearchPageData(
            query=page_data.query,
            selected_record_key=page_data.selected_record_key,
            error="Enter a device question for the chatbot.",
            chat_messages=prior_messages,
        )
    else:
        try:
            result = await openfda_client.get_device(page_data.selected_record_key)
        except (SearchValidationError, OpenFdaError) as exc:
            page_data = DeviceSearchPageData(
                query=page_data.query,
                selected_record_key=page_data.selected_record_key,
                error=f"FDA device lookup failed: {exc}",
                chat_messages=prior_messages,
                chat_input=page_data.chat_input,
            )
        else:
            if result is None:
                page_data = DeviceSearchPageData(
                    query=page_data.query,
                    selected_record_key=page_data.selected_record_key,
                    error="The selected FDA device could not be loaded.",
                    chat_messages=prior_messages,
                )
            else:
                cached_summary = device_summary.strip()
                cached_summary_model = device_summary_model.strip() or None
                if cached_summary:
                    summary = ChatReply(model_id=cached_summary_model, content=cached_summary)
                    reply = await chatbot_client.answer_device(
                        page_data.chat_input,
                        result,
                        prior_messages,
                    )
                else:
                    summary, reply = await asyncio.gather(
                        chatbot_client.summarize_device(result),
                        chatbot_client.answer_device(page_data.chat_input, result, prior_messages),
                    )
                updated_messages = [
                    *prior_messages,
                    ChatMessage(role="user", content=page_data.chat_input),
                    ChatMessage(role="assistant", content=reply.content),
                ]
                notices: list[str] = []
                if summary.used_fallback:
                    notices.append("Anthropic was unavailable, so OpenAI produced the device summary.")
                if reply.used_fallback:
                    notices.append("Anthropic was unavailable, so the device chatbot used OpenAI for this reply.")
                page_data = DeviceSearchPageData(
                    query=page_data.query,
                    selected_record_key=page_data.selected_record_key,
                    result=result,
                    chat_messages=updated_messages,
                    chat_notice=" ".join(notices) if notices else reply.error,
                    device_summary=summary.content,
                    device_summary_model=summary.model_id,
                )

    return _render_device_page(request, page_data)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
