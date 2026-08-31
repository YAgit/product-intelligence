from __future__ import annotations

from dataclasses import dataclass
import re

import httpx

from app.config import settings
from app.openfda import DeviceRecord, DrugRecord


OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
PRIMARY_MODEL_ID = "anthropic/claude-sonnet-5"
FALLBACK_MODEL_ID = "openai/gpt-5.6-luna"
MAX_CHAT_TOKENS = 280
MAX_SUMMARY_TOKENS = 420
MAX_SUMMARY_WORDS = 250
MAX_CHAT_CHARS = 250


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ChatReply:
    model_id: str | None
    content: str
    used_fallback: bool = False
    error: str | None = None


def build_product_context(drug: DrugRecord | None) -> str:
    if drug is None:
        return "No specific FDA product is currently selected."

    ingredients = ", ".join(drug.active_ingredients) if drug.active_ingredients else "Not available"
    routes = ", ".join(drug.route) if drug.route else "Not available"
    package_ndcs = ", ".join(drug.package_ndcs[:4]) if drug.package_ndcs else "Not available"
    return (
        f"Selected product:\n"
        f"- Brand name: {drug.brand_name}\n"
        f"- Generic name: {drug.generic_name}\n"
        f"- Labeler: {drug.labeler_name}\n"
        f"- Product NDC: {drug.product_ndc}\n"
        f"- Package NDCs: {package_ndcs}\n"
        f"- Dosage form: {drug.dosage_form}\n"
        f"- Route: {routes}\n"
        f"- Ingredients: {ingredients}\n"
        f"- Marketing category: {drug.marketing_category}\n"
        f"- Product type: {drug.product_type}\n"
        f"- Application number: {drug.application_number}\n"
        f"- Marketed since: {drug.marketing_start_date}\n"
    )


def build_device_context(device: DeviceRecord | None) -> str:
    if device is None:
        return "No specific FDA device is currently selected."

    product_codes = ", ".join(device.product_codes) if device.product_codes else "Not available"
    storage = (
        "; ".join(device.storage_and_handling_conditions)
        if device.storage_and_handling_conditions
        else "Not available"
    )
    packaging = (
        "; ".join(device.packaging_configurations)
        if device.packaging_configurations
        else "Not available"
    )
    return (
        f"Selected device:\n"
        f"- Device Identifier: {device.device_identifier}\n"
        f"- Brand name: {device.brand_name}\n"
        f"- Company: {device.company_name}\n"
        f"- Version or model number: {device.version_or_model_number}\n"
        f"- Catalog number: {device.catalog_number}\n"
        f"- Device description: {device.device_description}\n"
        f"- FDA product codes: {product_codes}\n"
        f"- Commercial distribution status: {device.commercial_distribution_status}\n"
        f"- Prescription or OTC status: {device.prescription_otc_status}\n"
        f"- Single use indicator: {device.single_use_indicator}\n"
        f"- Sterility information: {device.sterility_information}\n"
        f"- MRI safety information: {device.mri_safety_information}\n"
        f"- Implantable-device indicator: {device.implantable_device_indicator}\n"
        f"- Latex information: {device.latex_information}\n"
        f"- Storage and handling: {storage}\n"
        f"- Packaging configurations: {packaging}\n"
    )


def build_chat_messages(
    user_message: str,
    drug: DrugRecord | None,
    prior_messages: list[ChatMessage],
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are a pharmaceutical product analyst. "
                "Answer only questions about pharmaceutical products, manufacturers, markets, dosage forms, ingredients, NDC-listed products, and closely related pharma product topics. "
                "If the user asks something outside pharmaceutical products, reply exactly: "
                "\"I cannot answer questions that are not about pharmaceutical products.\" "
                "Keep the answer to around 250 characters when possible, but always finish the sentence cleanly even if that runs slightly longer. "
                "Be concise, practical, and grounded. Do not claim access to private data or live web browsing."
            ),
        },
        {
            "role": "system",
            "content": build_product_context(drug),
        },
        *[
            {"role": message.role, "content": message.content}
            for message in prior_messages
            if message.role in {"user", "assistant"} and message.content.strip()
        ],
        {
            "role": "user",
            "content": user_message.strip(),
        },
    ]


def build_device_chat_messages(
    user_message: str,
    device: DeviceRecord | None,
    prior_messages: list[ChatMessage],
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are a pharmaceutical device analyst. "
                "Answer only questions about FDA-listed medical devices, device manufacturers, device identifiers, model numbers, catalog numbers, labeling, packaging, distribution status, and closely related device topics. "
                "If the user asks something outside medical devices or pharmaceutical products, reply exactly: "
                "\"I cannot answer questions that are not about pharmaceutical devices or pharmaceutical products.\" "
                "Keep the answer to around 250 characters when possible, but always finish the sentence cleanly even if that runs slightly longer. "
                "Be concise, practical, and grounded. Do not claim access to private data or live web browsing."
            ),
        },
        {
            "role": "system",
            "content": build_device_context(device),
        },
        *[
            {"role": message.role, "content": message.content}
            for message in prior_messages
            if message.role in {"user", "assistant"} and message.content.strip()
        ],
        {
            "role": "user",
            "content": user_message.strip(),
        },
    ]


def build_competitive_summary_messages(drug: DrugRecord | None) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are a pharmaceutical product analyst. "
                "Provide a concise overview of a pharmaceutical product. "
                "Keep the answer under 250 words, plain text, no bullets. Aim for 160 to 220 words. "
                "Include what the product is generally used for and the most relevant product details a typical user would care about, "
                "such as dosage form, active ingredient, manufacturer, route, market category, or positioning when helpful. "
                "End with a complete sentence. Do not end mid-sentence or with an unfinished parenthesis. "
                "If uncertain, say so briefly."
            ),
        },
        {
            "role": "system",
            "content": build_product_context(drug),
        },
        {
            "role": "user",
            "content": "Provide a short overview of the selected pharmaceutical product.",
        },
    ]


def build_device_summary_messages(device: DeviceRecord | None) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are a pharmaceutical device analyst. "
                "Provide a concise overview of a medical device. "
                "Keep the answer under 250 words, plain text, no bullets. Aim for 160 to 220 words. "
                "Include what the device is, the most useful FDA-backed details a typical user would care about, "
                "such as device identifier, manufacturer, model number, product code, distribution status, sterility, single-use status, or MRI safety when relevant. "
                "End with a complete sentence. Do not end mid-sentence or with an unfinished parenthesis. "
                "If uncertain, say so briefly."
            ),
        },
        {
            "role": "system",
            "content": build_device_context(device),
        },
        {
            "role": "user",
            "content": "Provide a short overview of the selected medical device.",
        },
    ]


def normalize_summary_text(text: str) -> str:
    compact = " ".join(text.split())
    words = compact.split()
    truncated = len(words) > MAX_SUMMARY_WORDS
    if truncated:
        compact = " ".join(words[:MAX_SUMMARY_WORDS])

    compact = compact.rstrip(" ,;:-")
    sentence_matches = list(re.finditer(r"[.!?](?:['\")\\]]+)?(?=\s|$)", compact))
    if sentence_matches:
        last_sentence_end = sentence_matches[-1].end()
        sentence_safe = compact[:last_sentence_end].strip()
        if sentence_safe:
            compact = sentence_safe
            truncated = truncated or last_sentence_end < len(" ".join(words[:MAX_SUMMARY_WORDS] if len(words) > MAX_SUMMARY_WORDS else words))

    if not compact.endswith((".", "!", "?")):
        compact = compact.rstrip(" ,;:-(")
        compact = re.sub(r"\s*\([^()]*$", "", compact).strip()
        sentence_matches = list(re.finditer(r"[.!?](?:['\")\\]]+)?(?=\s|$)", compact))
        if sentence_matches:
            compact = compact[: sentence_matches[-1].end()].strip()
            truncated = True

    if truncated and compact.endswith((".", "!", "?")):
        return compact
    return compact


def normalize_chat_text(text: str) -> str:
    compact = " ".join(text.split()).rstrip(" ,;:-")
    if len(compact) <= MAX_CHAT_CHARS:
        if compact.endswith((".", "!", "?")):
            return compact
        compact = compact.rstrip(" ,;:-(")
        compact = re.sub(r"\s*\([^()]*$", "", compact).strip()
        sentence_matches = list(re.finditer(r"[.!?](?:['\")\\]]+)?(?=\s|$)", compact))
        if sentence_matches:
            return compact[: sentence_matches[-1].end()].strip()
        return compact

    search_window = compact[: MAX_CHAT_CHARS + 120]
    sentence_matches = list(re.finditer(r"[.!?](?:['\")\\]]+)?(?=\s|$)", search_window))
    for match in sentence_matches:
        if match.end() >= MAX_CHAT_CHARS - 40:
            return search_window[: match.end()].strip()

    fallback = search_window[:MAX_CHAT_CHARS].rstrip(" ,;:-(")
    fallback = re.sub(r"\s*\([^()]*$", "", fallback).strip()
    sentence_matches = list(re.finditer(r"[.!?](?:['\")\\]]+)?(?=\s|$)", fallback))
    if sentence_matches:
        return fallback[: sentence_matches[-1].end()].strip()
    return fallback


class PharmaChatbotClient:
    async def summarize_product(self, drug: DrugRecord | None) -> ChatReply:
        if not settings.openrouter_api_key:
            return ChatReply(
                model_id=None,
                content="The summary is unavailable because OPENROUTER_API_KEY is not configured.",
                error="OPENROUTER_API_KEY is not configured.",
            )

        return await self._complete_with_fallback(
            build_competitive_summary_messages(drug),
            max_tokens=MAX_SUMMARY_TOKENS,
            normalize=normalize_summary_text,
        )

    async def summarize_device(self, device: DeviceRecord | None) -> ChatReply:
        if not settings.openrouter_api_key:
            return ChatReply(
                model_id=None,
                content="The summary is unavailable because OPENROUTER_API_KEY is not configured.",
                error="OPENROUTER_API_KEY is not configured.",
            )

        return await self._complete_with_fallback(
            build_device_summary_messages(device),
            max_tokens=MAX_SUMMARY_TOKENS,
            normalize=normalize_summary_text,
        )

    async def answer(
        self,
        user_message: str,
        drug: DrugRecord | None,
        prior_messages: list[ChatMessage] | None = None,
    ) -> ChatReply:
        prior_messages = prior_messages or []
        if not settings.openrouter_api_key:
            return ChatReply(
                model_id=None,
                content="The chatbot is unavailable because OPENROUTER_API_KEY is not configured.",
                error="OPENROUTER_API_KEY is not configured.",
            )

        return await self._complete_with_fallback(
            build_chat_messages(user_message, drug, prior_messages),
            max_tokens=MAX_CHAT_TOKENS,
            normalize=normalize_chat_text,
        )

    async def answer_device(
        self,
        user_message: str,
        device: DeviceRecord | None,
        prior_messages: list[ChatMessage] | None = None,
    ) -> ChatReply:
        prior_messages = prior_messages or []
        if not settings.openrouter_api_key:
            return ChatReply(
                model_id=None,
                content="The chatbot is unavailable because OPENROUTER_API_KEY is not configured.",
                error="OPENROUTER_API_KEY is not configured.",
            )

        return await self._complete_with_fallback(
            build_device_chat_messages(user_message, device, prior_messages),
            max_tokens=MAX_CHAT_TOKENS,
            normalize=normalize_chat_text,
        )

    async def _complete_with_fallback(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        normalize,
    ) -> ChatReply:
        primary = await self._complete(
            PRIMARY_MODEL_ID,
            messages,
            max_tokens=max_tokens,
            normalize=normalize,
        )
        if primary.content:
            return primary

        fallback = await self._complete(
            FALLBACK_MODEL_ID,
            messages,
            max_tokens=max_tokens,
            normalize=normalize,
        )
        if fallback.content:
            return ChatReply(
                model_id=fallback.model_id,
                content=fallback.content,
                used_fallback=True,
            )

        return ChatReply(
            model_id=None,
            content="The chatbot could not answer right now.",
            error=fallback.error or primary.error or "Chat request failed.",
        )

    async def _complete(
        self,
        model_id: str,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        normalize,
    ) -> ChatReply:
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "X-OpenRouter-Title": settings.app_name,
        }
        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        if model_id.startswith("anthropic/") or model_id.startswith("openai/"):
            payload["include_reasoning"] = False
            payload["reasoning_effort"] = "none"

        timeout = httpx.Timeout(25.0, connect=8.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    OPENROUTER_CHAT_COMPLETIONS_URL,
                    headers=headers,
                    json=payload,
                )
            except httpx.HTTPError:
                return ChatReply(
                    model_id=model_id,
                    content="",
                    error="Provider request failed.",
                )

        if response.status_code >= 400:
            try:
                data = response.json()
            except ValueError:
                data = {}
            return ChatReply(
                model_id=model_id,
                content="",
                error=data.get("error", {}).get("message") or "Provider request failed.",
            )

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            return ChatReply(
                model_id=model_id,
                content="",
                error="Provider returned an unexpected response.",
            )

        if not isinstance(content, str) or not content.strip():
            return ChatReply(
                model_id=model_id,
                content="",
                error="Provider returned an empty response.",
            )

        return ChatReply(model_id=model_id, content=normalize(content))


def get_chatbot_client() -> PharmaChatbotClient:
    return PharmaChatbotClient()
