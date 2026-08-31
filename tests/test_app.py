from fastapi.testclient import TestClient

from app.chatbot import ChatMessage, ChatReply, get_chatbot_client
from app.main import app
from app.openfda import (
    DeviceMatch,
    DeviceRecord,
    DrugMatch,
    DrugRecord,
    OpenFdaError,
    SearchValidationError,
    get_openfda_client,
)


client = TestClient(app)


class FakeOpenFdaClient:
    def __init__(
        self,
        *,
        drug_matches: list[DrugMatch] | None = None,
        product: DrugRecord | None = None,
        device_matches: list[DeviceMatch] | None = None,
        device: DeviceRecord | None = None,
        error: Exception | None = None,
    ) -> None:
        self.drug_matches = drug_matches or []
        self.product = product
        self.device_matches = device_matches or []
        self.device = device
        self.error = error
        self.search_calls = 0
        self.product_calls = 0
        self.device_search_calls = 0
        self.device_calls = 0

    async def search_matches(self, query: str, *, limit: int = 8) -> list[DrugMatch]:
        self.search_calls += 1
        if self.error is not None:
            raise self.error
        return self.drug_matches

    async def get_product(self, product_ndc: str) -> DrugRecord | None:
        self.product_calls += 1
        if self.error is not None:
            raise self.error
        return self.product

    async def search_device_matches(self, query: str, *, limit: int = 8) -> list[DeviceMatch]:
        self.device_search_calls += 1
        if self.error is not None:
            raise self.error
        return self.device_matches

    async def get_device(self, record_key: str) -> DeviceRecord | None:
        self.device_calls += 1
        if self.error is not None:
            raise self.error
        return self.device


class FakeChatbotClient:
    def __init__(
        self,
        reply: ChatReply,
        summary: ChatReply | None = None,
        device_reply: ChatReply | None = None,
        device_summary: ChatReply | None = None,
    ) -> None:
        self.reply = reply
        self.summary = summary or ChatReply(
            model_id="anthropic/claude-sonnet-5",
            content="Store-brand pediatric acetaminophen products create the main competitive pressure for this selected product.",
        )
        self.device_reply = device_reply or reply
        self.device_summary = device_summary or ChatReply(
            model_id="anthropic/claude-sonnet-5",
            content="This selected device is an FDA-listed forceps model with single-use, sterility, and MRI labeling details that should be checked against the device record before operational use.",
        )

    async def summarize_product(self, drug: DrugRecord | None) -> ChatReply:
        return self.summary

    async def answer(
        self,
        user_message: str,
        drug: DrugRecord | None,
        prior_messages: list[ChatMessage] | None = None,
    ) -> ChatReply:
        return self.reply

    async def summarize_device(self, device: DeviceRecord | None) -> ChatReply:
        return self.device_summary

    async def answer_device(
        self,
        user_message: str,
        device: DeviceRecord | None,
        prior_messages: list[ChatMessage] | None = None,
    ) -> ChatReply:
        return self.device_reply


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


def make_match(brand_name: str, product_ndc: str) -> DrugMatch:
    return DrugMatch(
        brand_name=brand_name,
        generic_name="acetaminophen",
        labeler_name="Kenvue Brands LLC",
        product_ndc=product_ndc,
        dosage_form="SUSPENSION",
        product_type="HUMAN OTC DRUG",
        marketing_category="OTC MONOGRAPH DRUG",
    )


def make_device() -> DeviceRecord:
    return DeviceRecord(
        record_key="c8557a3c-3f34-4b70-9461-302eb8d841be",
        device_identifier="00192896058644",
        brand_name="LARYNGOSCOPY ALLIGATOR FORCEPS",
        company_name="SONTEC INSTRUMENTS, INC.",
        version_or_model_number="1301-294",
        catalog_number="1301-294",
        device_description="LARYNGOSCOPIC ALLIGATOR FORCEPS OVAL TIP RIGHT UP-ANGLE OPENED POINTED BLADE CONICAL FLEXIBLE TUBE SHAFT",
        product_codes=["KAE - FORCEPS, ENT"],
        commercial_distribution_status="In Commercial Distribution",
        prescription_otc_status="Prescription",
        single_use_indicator="Not labeled as single use",
        sterility_information="Not labeled as sterile; Sterilization required before use; Methods: Moist Heat or Steam Sterilization",
        mri_safety_information="Labeling does not contain MRI Safety Information",
        implantable_device_indicator="Not implantable",
        latex_information="Labeled as not made with natural rubber latex",
        storage_and_handling_conditions=["Temperature: 20 C to 25 C"],
        packaging_configurations=["00192896058644 (Primary, GS1)", "Base package count: 1"],
    )


def make_device_match(brand_name: str, record_key: str) -> DeviceMatch:
    return DeviceMatch(
        record_key=record_key,
        device_identifier="00192896058644",
        brand_name=brand_name,
        company_name="SONTEC INSTRUMENTS, INC.",
        version_or_model_number="1301-294",
        catalog_number="1301-294",
        product_code="KAE - FORCEPS, ENT",
    )


def test_health_route() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_page_renders() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Drug Search" in response.text
    assert "Device Search" in response.text
    assert "Important Drug Disclaimer" in response.text
    assert "Pharma Analyst Chatbot" in response.text


def test_home_page_shows_multiple_match_selection() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        drug_matches=[
            make_match("Tylenol Children", "50580-111"),
            make_match("Tylenol Cold", "50580-222"),
        ]
    )

    response = client.get("/?query=Tylenol")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Select A Product Match" in response.text
    assert "Tylenol Children" in response.text
    assert "Tylenol Cold" in response.text
    assert 'data-scroll-target="match-panel"' in response.text


def test_home_page_renders_selected_product() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        drug_matches=[make_match("Infants TYLENOL", "50580-599")],
        product=make_result(),
    )

    response = client.get("/?query=Tylenol&product_ndc=50580-599")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Infants TYLENOL" in response.text
    assert "Pharma Analyst Chatbot" in response.text
    assert "Product overview" in response.text
    assert 'data-scroll-target="details-panel"' in response.text


def test_home_page_shows_invalid_query_message() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        error=SearchValidationError("NDC codes must contain 10 or 11 digits.")
    )

    response = client.get("/?query=1234")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "NDC codes must contain 10 or 11 digits." in response.text


def test_home_page_shows_no_results_message() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(drug_matches=[])

    response = client.get("/?query=UnknownDrug")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "No FDA NDC matches were found for that search." in response.text


def test_chat_route_renders_reply() -> None:
    fake_openfda_client = FakeOpenFdaClient(
        drug_matches=[make_match("Infants TYLENOL", "50580-599")],
        product=make_result(),
    )
    app.dependency_overrides[get_openfda_client] = lambda: fake_openfda_client
    app.dependency_overrides[get_chatbot_client] = lambda: FakeChatbotClient(
        ChatReply(
            model_id="anthropic/claude-sonnet-5",
            content="This product mainly competes with store-brand pediatric acetaminophen products.",
        )
    )

    response = client.post(
        "/chat",
        data={
            "query": "Tylenol",
            "product_ndc": "50580-599",
            "message": "What competitors does this product face?",
            "competitive_summary": "Store-brand pediatric acetaminophen products create the main competitive pressure for this selected product.",
            "competitive_summary_model": "anthropic/claude-sonnet-5",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "What competitors does this product face?" in response.text
    assert "store-brand pediatric acetaminophen" in response.text
    assert "Product overview" in response.text
    assert 'action="/chat#chat-panel"' in response.text
    assert 'data-scroll-target="chat-panel"' in response.text
    assert fake_openfda_client.search_calls == 0
    assert 'name="competitive_summary"' in response.text


def test_chat_route_shows_fallback_notice() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        drug_matches=[make_match("Infants TYLENOL", "50580-599")],
        product=make_result(),
    )
    app.dependency_overrides[get_chatbot_client] = lambda: FakeChatbotClient(
        ChatReply(
            model_id="openai/gpt-5.6-luna",
            content="Fallback response.",
            used_fallback=True,
        )
    )

    response = client.post(
        "/chat",
        data={
            "query": "Tylenol",
            "product_ndc": "50580-599",
            "message": "Tell me about this product.",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "used OpenAI for this reply" in response.text


def test_chat_route_requires_selected_product() -> None:
    response = client.post(
        "/chat",
        data={
            "query": "Tylenol",
            "product_ndc": "",
            "message": "Tell me about this product.",
        },
    )

    assert response.status_code == 200
    assert "Select a pharmaceutical product before using the chatbot." in response.text


def test_home_page_shows_upstream_error_message() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        error=OpenFdaError("openFDA could not be reached right now.")
    )

    response = client.get("/?query=Eliquis")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "FDA lookup failed: openFDA could not be reached right now." in response.text


def test_device_page_renders() -> None:
    response = client.get("/devices")

    assert response.status_code == 200
    assert "Device Search" in response.text
    assert "Important Device Disclaimer" in response.text
    assert "Device Analyst Chatbot" in response.text


def test_device_page_shows_multiple_match_selection() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        device_matches=[
            make_device_match("LARYNGOSCOPY ALLIGATOR FORCEPS", "record-1"),
            make_device_match("LARYNGOSCOPY ALLIGATOR FORCEPS PLUS", "record-2"),
        ]
    )

    response = client.get("/devices?query=1301-294")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Select A Device Match" in response.text
    assert '<select id="record_key"' in response.text
    assert 'data-scroll-target="device-match-panel"' in response.text


def test_device_page_renders_selected_device() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        device_matches=[make_device_match("LARYNGOSCOPY ALLIGATOR FORCEPS", "record-1")],
        device=make_device(),
    )

    response = client.get("/devices?query=1301-294&record_key=record-1")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "LARYNGOSCOPY ALLIGATOR FORCEPS" in response.text
    assert "FDA Device Details" in response.text
    assert "Device overview" in response.text
    assert "Packaging Configurations" in response.text
    assert 'data-scroll-target="device-details-panel"' in response.text


def test_device_page_shows_no_results_message() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(device_matches=[])

    response = client.get("/devices?query=UnknownDevice")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "No FDA device matches were found for that search." in response.text


def test_device_chat_route_renders_reply() -> None:
    fake_openfda_client = FakeOpenFdaClient(
        device_matches=[make_device_match("LARYNGOSCOPY ALLIGATOR FORCEPS", "record-1")],
        device=make_device(),
    )
    app.dependency_overrides[get_openfda_client] = lambda: fake_openfda_client
    app.dependency_overrides[get_chatbot_client] = lambda: FakeChatbotClient(
        ChatReply(
            model_id="anthropic/claude-sonnet-5",
            content="Drug reply.",
        ),
        device_reply=ChatReply(
            model_id="anthropic/claude-sonnet-5",
            content="This device is in commercial distribution and its sterility and MRI labeling should be reviewed before use.",
        ),
    )

    response = client.post(
        "/devices/chat",
        data={
            "query": "1301-294",
            "record_key": "record-1",
            "message": "What should I notice first?",
            "device_summary": "This selected device is an FDA-listed forceps model with single-use, sterility, and MRI labeling details that should be checked against the device record before operational use.",
            "device_summary_model": "anthropic/claude-sonnet-5",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "What should I notice first?" in response.text
    assert "sterility and MRI labeling" in response.text
    assert 'action="/devices/chat#device-chat-panel"' in response.text
    assert 'data-scroll-target="device-chat-panel"' in response.text
    assert fake_openfda_client.device_search_calls == 0
    assert 'name="device_summary"' in response.text


def test_device_chat_route_requires_selected_device() -> None:
    response = client.post(
        "/devices/chat",
        data={
            "query": "1301-294",
            "record_key": "",
            "message": "Tell me about this device.",
        },
    )

    assert response.status_code == 200
    assert "Select an FDA device before using the chatbot." in response.text
