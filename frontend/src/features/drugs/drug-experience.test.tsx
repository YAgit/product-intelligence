import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

import { DrugExperience } from "@/features/drugs/drug-experience";
import {
  chatAboutDrug,
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
