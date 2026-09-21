from fastapi.testclient import TestClient

from app.adverse_events import (
    AdverseEventDataset,
    get_adverse_event_client,
    parse_adverse_event_report,
)
from app.chatbot import ChatMessage, ChatReply, get_chatbot_client
from app.device_adverse_events import (
    DeviceAdverseEventDataset,
    DeviceEventMatch,
    get_device_adverse_event_client,
    parse_device_adverse_event_report,
)
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


class FakeAdverseEventClient:
    def __init__(
        self,
        dataset: AdverseEventDataset | None = None,
        error: Exception | None = None,
    ) -> None:
        self.dataset = dataset or AdverseEventDataset(reports=[], available_reports=0)
        self.error = error
        self.calls: list[tuple[str, object, object]] = []

    async def get_reports(self, brand_name, start_date, end_date):
        self.calls.append((brand_name, start_date, end_date))
        if self.error is not None:
            raise self.error
        return self.dataset


class FakeDeviceAdverseEventClient:
    def __init__(
        self,
        dataset: DeviceAdverseEventDataset | None = None,
        error: Exception | None = None,
    ) -> None:
        self.dataset = dataset or DeviceAdverseEventDataset(
            reports=[],
            available_reports=0,
            selected_match=None,
            attempted_matches=(),
        )
        self.error = error
        self.calls: list[tuple[DeviceRecord, object, object]] = []

    async def get_reports(self, device, start_date, end_date):
        self.calls.append((device, start_date, end_date))
        if self.error is not None:
            raise self.error
        return self.dataset


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


def test_drug_search_api_returns_domain_matches() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        drug_matches=[
            make_match("Tylenol Children", "50580-111"),
            make_match("Tylenol Cold", "50580-222"),
        ]
    )

    response = client.get("/api/v1/drugs/search?query=Tylenol")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["query"] == "Tylenol"
    assert [item["product_ndc"] for item in response.json()["matches"]] == [
        "50580-111",
        "50580-222",
    ]


def test_drug_detail_and_summary_apis_return_selected_product() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(product=make_result())
    app.dependency_overrides[get_chatbot_client] = lambda: FakeChatbotClient(
        ChatReply(model_id="anthropic/claude-sonnet-5", content="Drug reply.")
    )

    detail_response = client.get("/api/v1/drugs/50580-599")
    summary_response = client.post("/api/v1/drugs/50580-599/summary")

    app.dependency_overrides.clear()

    assert detail_response.status_code == 200
    assert detail_response.json()["brand_name"] == "Infants TYLENOL"
    assert detail_response.json()["package_ndcs"] == ["50580-599-01", "50580-599-02"]
    assert summary_response.status_code == 200
    assert "pediatric acetaminophen" in summary_response.json()["content"]
    assert summary_response.json()["used_fallback"] is False


def test_drug_chat_api_returns_reply() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(product=make_result())
    app.dependency_overrides[get_chatbot_client] = lambda: FakeChatbotClient(
        ChatReply(
            model_id="anthropic/claude-sonnet-5",
            content="The selected product contains acetaminophen.",
        )
    )

    response = client.post(
        "/api/v1/drugs/50580-599/chat",
        json={
            "message": "What is the active ingredient?",
            "history": [{"role": "user", "content": "Tell me about this product."}],
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["content"] == "The selected product contains acetaminophen."
    assert response.json()["model_id"] == "anthropic/claude-sonnet-5"


def test_device_search_and_detail_apis_return_domain_data() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        device_matches=[make_device_match("LARYNGOSCOPY ALLIGATOR FORCEPS", "record-1")],
        device=make_device(),
    )

    search_response = client.get("/api/v1/devices/search?query=1301-294")
    detail_response = client.get("/api/v1/devices/record-1")

    app.dependency_overrides.clear()

    assert search_response.status_code == 200
    assert search_response.json()["matches"][0]["record_key"] == "record-1"
    assert detail_response.status_code == 200
    assert detail_response.json()["device_identifier"] == "00192896058644"
    assert detail_response.json()["product_codes"] == ["KAE - FORCEPS, ENT"]


def test_device_summary_and_chat_apis_return_ai_responses() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(device=make_device())
    app.dependency_overrides[get_chatbot_client] = lambda: FakeChatbotClient(
        ChatReply(model_id="anthropic/claude-sonnet-5", content="Drug reply."),
        device_reply=ChatReply(
            model_id="openai/gpt-5.6-luna",
            content="Review the device sterility labeling.",
            used_fallback=True,
        ),
    )

    summary_response = client.post("/api/v1/devices/record-1/summary")
    chat_response = client.post(
        "/api/v1/devices/record-1/chat",
        json={"message": "What should I review?", "history": []},
    )

    app.dependency_overrides.clear()

    assert summary_response.status_code == 200
    assert "FDA-listed forceps" in summary_response.json()["content"]
    assert chat_response.status_code == 200
    assert chat_response.json()["used_fallback"] is True
    assert chat_response.json()["content"] == "Review the device sterility labeling."


def test_api_translates_validation_not_found_and_upstream_errors() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        error=SearchValidationError("Product names must be at least 2 characters.")
    )
    validation_response = client.get("/api/v1/drugs/search?query=x")

    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(product=None)
    not_found_response = client.get("/api/v1/drugs/00000-000")

    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        error=OpenFdaError("openFDA could not be reached right now.")
    )
    upstream_response = client.get("/api/v1/devices/search?query=forceps")

    app.dependency_overrides.clear()

    assert validation_response.status_code == 422
    assert validation_response.json()["detail"] == "Product names must be at least 2 characters."
    assert not_found_response.status_code == 404
    assert not_found_response.json()["detail"] == "Drug not found."
    assert upstream_response.status_code == 502
    assert "openFDA could not be reached" in upstream_response.json()["detail"]


def test_api_allows_configured_local_frontend_origin() -> None:
    response = client.options(
        "/api/v1/drugs/search?query=Tylenol",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_versioned_api_health_route() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_adverse_event_api_uses_selected_drug_brand_and_returns_analytics() -> None:
    adverse_client = FakeAdverseEventClient(
        AdverseEventDataset(
            reports=[
                parse_adverse_event_report(
                    {
                        "receivedate": "20240115",
                        "serious": "1",
                        "seriousnesshospitalization": "1",
                        "patient": {"reaction": [{"reactionmeddrapt": "NAUSEA"}]},
                    }
                )
            ],
            available_reports=1,
        )
    )
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        product=make_result()
    )
    app.dependency_overrides[get_adverse_event_client] = lambda: adverse_client

    response = client.get(
        "/api/v1/drugs/50580-599/adverse-events"
        "?start_date=2024-01-01&end_date=2024-12-31"
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["matching"]["field"] == "patient.drug.openfda.brand_name.exact"
    assert body["matching"]["value"] == "Infants TYLENOL"
    assert body["overview"]["serious_reports"] == 1
    assert body["outcomes"][1]["report_count"] == 1
    assert body["reactions"][0]["term"] == "NAUSEA"
    assert adverse_client.calls[0][0] == "Infants TYLENOL"


def test_adverse_event_api_rejects_invalid_date_order_without_querying_faers() -> None:
    adverse_client = FakeAdverseEventClient()
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        product=make_result()
    )
    app.dependency_overrides[get_adverse_event_client] = lambda: adverse_client

    response = client.get(
        "/api/v1/drugs/50580-599/adverse-events"
        "?start_date=2025-01-01&end_date=2024-01-01"
    )

    app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "start date" in response.json()["detail"]
    assert adverse_client.calls == []


def test_adverse_event_api_translates_upstream_failure() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        product=make_result()
    )
    app.dependency_overrides[get_adverse_event_client] = lambda: FakeAdverseEventClient(
        error=OpenFdaError("FAERS unavailable")
    )

    response = client.get(
        "/api/v1/drugs/50580-599/adverse-events"
        "?start_date=2024-01-01&end_date=2024-12-31"
    )

    app.dependency_overrides.clear()

    assert response.status_code == 502
    assert "FAERS unavailable" in response.json()["detail"]


def test_device_adverse_event_api_uses_selected_device_and_returns_analytics() -> None:
    match = DeviceEventMatch(
        field="device.udi_di",
        value="00192896058644",
        label="Exact Device Identifier",
    )
    adverse_client = FakeDeviceAdverseEventClient(
        DeviceAdverseEventDataset(
            reports=[
                parse_device_adverse_event_report(
                    {
                        "date_received": "20250115",
                        "event_type": "Injury",
                        "product_problems": ["Material rupture"],
                        "patient": [{"patient_problems": ["Pain"]}],
                    }
                )
            ],
            available_reports=1,
            selected_match=match,
            attempted_matches=(match,),
        )
    )
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        device=make_device()
    )
    app.dependency_overrides[get_device_adverse_event_client] = lambda: adverse_client

    response = client.get(
        "/api/v1/devices/record-1/adverse-events"
        "?start_date=2025-01-01&end_date=2025-12-31"
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["matching"]["field"] == "device.udi_di"
    assert body["matching"]["strategy"] == "Exact Device Identifier"
    assert body["event_types"][1]["report_count"] == 1
    assert body["device_problems"][0]["term"] == "Material rupture"
    assert body["patient_problems"][0]["term"] == "Pain"
    assert adverse_client.calls[0][0].record_key == make_device().record_key


def test_device_adverse_event_api_rejects_invalid_date_order_without_querying() -> None:
    adverse_client = FakeDeviceAdverseEventClient()
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        device=make_device()
    )
    app.dependency_overrides[get_device_adverse_event_client] = lambda: adverse_client

    response = client.get(
        "/api/v1/devices/record-1/adverse-events"
        "?start_date=2025-12-31&end_date=2025-01-01"
    )

    app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "start date" in response.json()["detail"]
    assert adverse_client.calls == []


def test_device_adverse_event_api_translates_upstream_failure() -> None:
    app.dependency_overrides[get_openfda_client] = lambda: FakeOpenFdaClient(
        device=make_device()
    )
    app.dependency_overrides[get_device_adverse_event_client] = lambda: (
        FakeDeviceAdverseEventClient(error=OpenFdaError("MAUDE unavailable"))
    )

    response = client.get(
        "/api/v1/devices/record-1/adverse-events"
        "?start_date=2025-01-01&end_date=2025-12-31"
    )

    app.dependency_overrides.clear()

    assert response.status_code == 502
    assert "MAUDE unavailable" in response.json()["detail"]
