from app.chatbot import (
    ChatMessage,
    PRIMARY_MODEL_ID,
    FALLBACK_MODEL_ID,
    build_chat_messages,
    build_competitive_summary_messages,
    build_product_context,
    normalize_chat_text,
    normalize_summary_text,
)
from app.openfda import DrugRecord


def make_result() -> DrugRecord:
    return DrugRecord(
        brand_name="Infants TYLENOL",
        generic_name="acetaminophen",
        labeler_name="Kenvue Brands LLC",
        product_ndc="50580-599",
        package_ndcs=["50580-599-01", "50580-599-02"],
        package_descriptions=["1 BOTTLE in 1 CARTON"],
        active_ingredients=["ACETAMINOPHEN (160 mg/5mL)"],
        route=["ORAL"],
        dosage_form="SUSPENSION",
        marketing_category="OTC MONOGRAPH DRUG",
        product_type="HUMAN OTC DRUG",
        application_number="M013",
        listing_expiration_date="December 31, 2026",
        marketing_start_date="June 26, 2017",
        finished=True,
    )


def test_build_product_context_includes_selected_product_details() -> None:
    context = build_product_context(make_result())

    assert "Brand name: Infants TYLENOL" in context
    assert "Product NDC: 50580-599" in context


def test_build_chat_messages_includes_prior_history_and_new_question() -> None:
    messages = build_chat_messages(
        "What competitors does this product face?",
        make_result(),
        [
            ChatMessage(role="user", content="Tell me about this product."),
            ChatMessage(role="assistant", content="It is an OTC acetaminophen suspension."),
        ],
    )

    assert messages[0]["role"] == "system"
    assert messages[-1]["content"] == "What competitors does this product face?"
    assert any(message["content"] == "Tell me about this product." for message in messages)


def test_build_competitive_summary_messages_reference_selected_product() -> None:
    messages = build_competitive_summary_messages(make_result())

    assert messages[-1]["content"] == "Provide a short overview of the selected pharmaceutical product."
    assert "Brand name: Infants TYLENOL" in messages[1]["content"]


def test_normalize_summary_text_limits_to_250_words() -> None:
    summary = normalize_summary_text(" ".join(["word"] * 320))

    assert len(summary.split()) <= 250


def test_normalize_summary_text_drops_incomplete_tail() -> None:
    summary = normalize_summary_text(
        "Sentence one is complete. Sentence two is also complete. Sentence three ends with an unfinished parenthesis (325"
    )

    assert summary == "Sentence one is complete. Sentence two is also complete."


def test_primary_and_fallback_models_are_defined() -> None:
    assert PRIMARY_MODEL_ID.startswith("anthropic/")
    assert FALLBACK_MODEL_ID.startswith("openai/")


def test_summary_token_budget_supports_250_word_overview() -> None:
    from app.chatbot import MAX_SUMMARY_TOKENS

    assert MAX_SUMMARY_TOKENS >= 350


def test_normalize_chat_text_prefers_complete_sentence_near_limit() -> None:
    text = (
        "Levothyroxine treats hypothyroidism by replacing thyroid hormone. "
        "This prescription tablet is taken orally and is made by Amneal Pharmaceuticals NY LLC. "
        "It should be taken consistently and monitored with thyroid labs."
    )

    summary = normalize_chat_text(text)

    assert summary.endswith(".")
    assert len(summary) >= 210


def test_normalize_chat_text_drops_incomplete_tail() -> None:
    text = (
        "TYLENOL Extra Strength contains acetaminophen and is used for pain and fever relief. "
        "The Extra Strength designation (500 mg per tablet) distinguishes it from Regular Strength TYLENOL (325"
    )

    summary = normalize_chat_text(text)

    assert summary == "TYLENOL Extra Strength contains acetaminophen and is used for pain and fever relief."
