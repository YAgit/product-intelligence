import pytest

from app.openfda import (
    DeviceMatch,
    SearchValidationError,
    build_device_search,
    build_name_search,
    build_ndc_search,
    build_openfda_search,
    parse_device_match,
    parse_device_record,
    parse_drug_match,
    parse_drug_record,
)


def test_build_name_search_uses_brand_and_generic_fields() -> None:
    search = build_name_search("Eliquis")

    assert 'brand_name:"Eliquis"' in search
    assert 'brand_name_base:"Eliquis"' in search
    assert 'generic_name:"Eliquis"' in search


def test_build_ndc_search_accepts_hyphenated_package_ndc() -> None:
    search = build_ndc_search("50580-599-01")

    assert "product_ndc:50580-599" in search
    assert "package_ndc:50580-599-01" in search


def test_build_ndc_search_accepts_hyphenated_product_ndc() -> None:
    search = build_ndc_search("50580-599")

    assert search == "product_ndc:50580-599 OR package_ndc:50580-599"


def test_build_ndc_search_generates_variants_for_digits_only_ndc() -> None:
    search = build_ndc_search("5058059901")

    assert "product_ndc:50580-599" in search
    assert "package_ndc:5058-0599-01" in search
    assert "package_ndc:50580-599-01" in search
    assert "package_ndc:50580-5990-1" in search


def test_build_openfda_search_rejects_short_ndc() -> None:
    with pytest.raises(SearchValidationError):
        build_openfda_search("1234")


def test_build_openfda_search_accepts_digits_only_product_ndc() -> None:
    search = build_openfda_search("00033765")

    assert "product_ndc:0003-3765" in search


def test_build_device_search_accepts_udi_barcode_text() -> None:
    search = build_device_search("(01)00192896058644(17)260101")

    assert 'identifiers.id:"00192896058644"' in search
    assert 'brand_name.exact:"(01)00192896058644(17)260101"' in search


def test_build_device_search_accepts_model_or_catalog_number() -> None:
    search = build_device_search("1301-294")

    assert 'version_or_model_number:"1301-294"' in search
    assert 'catalog_number:"1301-294"' in search


def test_build_device_search_rejects_short_values() -> None:
    with pytest.raises(SearchValidationError):
        build_device_search("X")


def test_parse_drug_record_formats_expected_fields() -> None:
    record = parse_drug_record(
        {
            "brand_name": "Infants TYLENOL",
            "generic_name": "acetaminophen",
            "labeler_name": "Kenvue Brands LLC",
            "product_ndc": "50580-599",
            "packaging": [
                {
                    "package_ndc": "50580-599-01",
                    "description": "1 BOTTLE in 1 CARTON",
                }
            ],
            "active_ingredients": [
                {
                    "name": "ACETAMINOPHEN",
                    "strength": "160 mg/5mL",
                }
            ],
            "route": ["ORAL"],
            "dosage_form": "SUSPENSION",
            "marketing_category": "OTC MONOGRAPH DRUG",
            "product_type": "HUMAN OTC DRUG",
            "application_number": "M013",
            "listing_expiration_date": "20261231",
            "marketing_start_date": "20170626",
            "finished": True,
        }
    )

    assert record.package_ndcs == ["50580-599-01"]
    assert record.active_ingredients == ["ACETAMINOPHEN (160 mg/5mL)"]
    assert record.listing_expiration_date == "December 31, 2026"
    assert record.marketing_start_date == "June 26, 2017"


def test_parse_drug_match_formats_expected_fields() -> None:
    match = parse_drug_match(
        {
            "brand_name": "Infants TYLENOL",
            "generic_name": "acetaminophen",
            "labeler_name": "Kenvue Brands LLC",
            "product_ndc": "50580-599",
            "dosage_form": "SUSPENSION",
            "product_type": "HUMAN OTC DRUG",
            "marketing_category": "OTC MONOGRAPH DRUG",
        }
    )

    assert match.brand_name == "Infants TYLENOL"
    assert match.product_ndc == "50580-599"


def test_parse_device_record_formats_expected_fields() -> None:
    record = parse_device_record(
        {
            "public_device_record_key": "record-1",
            "brand_name": "LARYNGOSCOPY ALLIGATOR FORCEPS",
            "company_name": "SONTEC INSTRUMENTS, INC.",
            "version_or_model_number": "1301-294",
            "catalog_number": "1301-294",
            "device_description": "LARYNGOSCOPIC ALLIGATOR FORCEPS",
            "commercial_distribution_status": "In Commercial Distribution",
            "is_rx": True,
            "is_single_use": False,
            "mri_safety": "Labeling does not contain MRI Safety Information",
            "is_labeled_as_no_nrl": True,
            "device_count_in_base_package": 1,
            "identifiers": [
                {
                    "id": "00192896058644",
                    "type": "Primary",
                    "issuing_agency": "GS1",
                }
            ],
            "product_codes": [{"code": "KAE", "name": "FORCEPS, ENT"}],
            "sterilization": {
                "is_sterile": False,
                "is_sterilization_prior_use": True,
                "sterilization_methods": ["Moist Heat or Steam Sterilization"],
            },
            "gmdn_terms": [{"implantable": False}],
            "storage": [{"type": "Temperature", "value": "20 to 25", "unit": "C"}],
        }
    )

    assert record.device_identifier == "00192896058644"
    assert record.prescription_otc_status == "Prescription"
    assert record.single_use_indicator == "Not labeled as single use"
    assert record.latex_information == "Labeled as not made with natural rubber latex"
    assert record.packaging_configurations[-1] == "Base package count: 1"


def test_parse_device_match_formats_expected_fields() -> None:
    match = parse_device_match(
        {
            "public_device_record_key": "record-1",
            "brand_name": "LARYNGOSCOPY ALLIGATOR FORCEPS",
            "company_name": "SONTEC INSTRUMENTS, INC.",
            "version_or_model_number": "1301-294",
            "catalog_number": "1301-294",
            "identifiers": [{"id": "00192896058644", "type": "Primary"}],
            "product_codes": [{"code": "KAE", "name": "FORCEPS, ENT"}],
        }
    )

    assert match == DeviceMatch(
        record_key="record-1",
        device_identifier="00192896058644",
        brand_name="LARYNGOSCOPY ALLIGATOR FORCEPS",
        company_name="SONTEC INSTRUMENTS, INC.",
        version_or_model_number="1301-294",
        catalog_number="1301-294",
        product_code="KAE - FORCEPS, ENT",
    )
