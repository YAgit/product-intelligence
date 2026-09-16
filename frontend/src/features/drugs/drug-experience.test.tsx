import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

import { AdverseEventIntelligence } from "@/features/drugs/adverse-event-intelligence";
import { DrugExperience } from "@/features/drugs/drug-experience";
import {
  chatAboutDrug,
  getDrugAdverseEvents,
  getDrug,
  searchDrugs,
  summarizeDrug,
} from "@/lib/api";
import type { Drug, DrugMatch } from "@/types/api";

vi.mock("@/lib/api", () => ({
  searchDrugs: vi.fn(),
  getDrug: vi.fn(),
  summarizeDrug: vi.fn(),
  chatAboutDrug: vi.fn(),
  getDrugAdverseEvents: vi.fn(),
  errorMessage: (error: unknown) => error instanceof Error ? error.message : "Request failed.",
}));

const drug: Drug = {
  brand_name: "Infants TYLENOL",
  generic_name: "acetaminophen",
  labeler_name: "Kenvue Brands LLC",
  product_ndc: "50580-599",
  dosage_form: "SUSPENSION",
  product_type: "HUMAN OTC DRUG",
  marketing_category: "OTC MONOGRAPH DRUG",
  package_ndcs: ["50580-599-01"],
  package_descriptions: ["1 BOTTLE in 1 CARTON"],
  active_ingredients: ["ACETAMINOPHEN (160 mg/5mL)"],
  route: ["ORAL"],
  application_number: "M013",
  listing_expiration_date: "December 31, 2026",
  marketing_start_date: "June 26, 2017",
  finished: true,
};

const matches: DrugMatch[] = [
  {
    brand_name: "Infants TYLENOL",
    generic_name: "acetaminophen",
    labeler_name: "Kenvue Brands LLC",
    product_ndc: "50580-599",
    dosage_form: "SUSPENSION",
    product_type: "HUMAN OTC DRUG",
    marketing_category: "OTC MONOGRAPH DRUG",
  },
  {
    brand_name: "Tylenol Cold",
    generic_name: "acetaminophen combination",
    labeler_name: "Kenvue Brands LLC",
    product_ndc: "50580-222",
    dosage_form: "LIQUID",
    product_type: "HUMAN OTC DRUG",
    marketing_category: "OTC MONOGRAPH DRUG",
  },
];

const summary = {
  content: "This is an FDA-listed pediatric acetaminophen product.",
  model_id: "anthropic/claude-sonnet-5",
  used_fallback: false,
  error: null,
};

test("requires explicit selection for ambiguous drug results and loads details", async () => {
  const user = userEvent.setup();
  vi.mocked(searchDrugs).mockResolvedValue({ query: "Tylenol", matches });
  vi.mocked(getDrug).mockResolvedValue(drug);
  vi.mocked(summarizeDrug).mockResolvedValue(summary);

  render(<DrugExperience />);
  await user.type(screen.getByLabelText("Product name or NDC code"), "Tylenol");
  await user.click(screen.getByRole("button", { name: "Search" }));

  expect(await screen.findByRole("heading", { name: "Select A Product Match" })).toBeTruthy();
  expect(getDrug).not.toHaveBeenCalled();

  await user.click(screen.getByRole("button", { name: /Infants TYLENOL/ }));

  expect(await screen.findByText("ACETAMINOPHEN (160 mg/5mL)")).toBeTruthy();
  expect(screen.getByText(summary.content)).toBeTruthy();
  expect(getDrug).toHaveBeenCalledWith("50580-599");
});

test("automatically loads one drug match and sends chat history", async () => {
  const user = userEvent.setup();
  vi.mocked(searchDrugs).mockResolvedValue({ query: "50580-599", matches: [matches[0]] });
  vi.mocked(getDrug).mockResolvedValue(drug);
  vi.mocked(summarizeDrug).mockResolvedValue(summary);
  vi.mocked(chatAboutDrug).mockResolvedValue({
    content: "The active ingredient is acetaminophen.",
    model_id: "anthropic/claude-sonnet-5",
    used_fallback: false,
    error: null,
  });

  render(<DrugExperience />);
  await user.type(screen.getByLabelText("Product name or NDC code"), "50580-599");
  await user.click(screen.getByRole("button", { name: "Search" }));
  await screen.findByText(summary.content);

  await user.type(screen.getByLabelText("Ask the analyst"), "What is the active ingredient?");
  await user.click(screen.getByRole("button", { name: "Send question" }));

  expect(await screen.findByText("The active ingredient is acetaminophen.")).toBeTruthy();
  expect(chatAboutDrug).toHaveBeenCalledWith(
    "50580-599",
    "What is the active ingredient?",
    [],
  );
});

test("shows a useful drug search error", async () => {
  const user = userEvent.setup();
  vi.mocked(searchDrugs).mockRejectedValue(new Error("FDA service is unavailable."));

  render(<DrugExperience />);
  await user.type(screen.getByLabelText("Product name or NDC code"), "Eliquis");
  await user.click(screen.getByRole("button", { name: "Search" }));

  expect((await screen.findByRole("alert")).textContent).toContain("FDA service is unavailable.");
});

test("loads adverse-event evidence for the explicitly selected drug", async () => {
  const user = userEvent.setup();
  vi.mocked(searchDrugs).mockResolvedValue({ query: "50580-599", matches: [matches[0]] });
  vi.mocked(getDrug).mockResolvedValue(drug);
  vi.mocked(summarizeDrug).mockResolvedValue(summary);
  vi.mocked(getDrugAdverseEvents).mockResolvedValue({
    matching: {
      field: "patient.drug.openfda.brand_name.exact",
      value: "Infants TYLENOL",
      start_date: "2025-01-01",
      end_date: "2025-12-31",
    },
    retrieval: {
      retrieved_reports: 2,
      available_reports: 1200,
      retrieval_limit: 1000,
      truncated: true,
      sort: "receivedate:desc",
    },
    overview: {
      total_reports: 2,
      serious_reports: 1,
      non_serious_reports: 1,
      serious_percentage: 50,
      reporting_period_start: "2025-02-01",
      reporting_period_end: "2025-05-01",
    },
    outcomes: [
      { outcome: "death", label: "Death", report_count: 0 },
      { outcome: "hospitalization", label: "Hospitalization", report_count: 1 },
    ],
    trends: [
      { period: "2025 Q1", total_reports: 1, serious_reports: 1 },
      { period: "2025 Q2", total_reports: 1, serious_reports: 0 },
    ],
    reactions: [
      { term: "NAUSEA", report_count: 2, report_percentage: 100, serious_report_count: 1 },
    ],
    limitations: ["A report does not establish causality."],
    source: "FDA Adverse Event Reporting System (FAERS) via openFDA",
  });

  render(<DrugExperience />);
  await user.type(screen.getByLabelText("Product name or NDC code"), "50580-599");
  await user.click(screen.getByRole("button", { name: "Search" }));
  await screen.findByText(summary.content);

  await user.clear(screen.getByLabelText("Start date"));
  await user.type(screen.getByLabelText("Start date"), "2025-01-01");
  await user.clear(screen.getByLabelText("End date"));
  await user.type(screen.getByLabelText("End date"), "2025-12-31");
  await user.click(screen.getByRole("button", { name: "Load adverse events" }));

  expect(await screen.findByText("NAUSEA")).toBeTruthy();
  expect(screen.getByText("50.0%")).toBeTruthy();
  expect(screen.getByText(/openFDA reported 1,200 matching reports/)).toBeTruthy();
  expect(screen.getByText("FDA Adverse Event Reporting System (FAERS) via openFDA")).toBeTruthy();
  expect(getDrugAdverseEvents).toHaveBeenCalledWith("50580-599", "2025-01-01", "2025-12-31");
});

test("validates the adverse-event date range before calling the API", async () => {
  const user = userEvent.setup();
  render(<AdverseEventIntelligence drug={drug} />);

  await user.clear(screen.getByLabelText("Start date"));
  await user.type(screen.getByLabelText("Start date"), "2025-12-31");
  await user.clear(screen.getByLabelText("End date"));
  await user.type(screen.getByLabelText("End date"), "2025-01-01");
  await user.click(screen.getByRole("button", { name: "Load adverse events" }));

  expect((await screen.findByRole("alert")).textContent).toContain(
    "The start date must be on or before the end date.",
  );
  expect(getDrugAdverseEvents).not.toHaveBeenCalled();
});
