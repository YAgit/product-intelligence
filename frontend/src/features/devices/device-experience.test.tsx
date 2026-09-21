import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

import { DeviceExperience } from "@/features/devices/device-experience";
import { DeviceAdverseEventIntelligence } from "@/features/devices/device-adverse-event-intelligence";
import {
  chatAboutDevice,
  getDevice,
  getDeviceAdverseEvents,
  searchDevices,
  summarizeDevice,
} from "@/lib/api";
import type { Device, DeviceMatch } from "@/types/api";

vi.mock("@/lib/api", () => ({
  searchDevices: vi.fn(),
  getDevice: vi.fn(),
  summarizeDevice: vi.fn(),
  chatAboutDevice: vi.fn(),
  getDeviceAdverseEvents: vi.fn(),
  errorMessage: (error: unknown) => error instanceof Error ? error.message : "Request failed.",
}));

const device: Device = {
  record_key: "record-1",
  device_identifier: "00192896058644",
  brand_name: "LARYNGOSCOPY ALLIGATOR FORCEPS",
  company_name: "SONTEC INSTRUMENTS, INC.",
  version_or_model_number: "1301-294",
  catalog_number: "1301-294",
  device_description: "Laryngoscopic alligator forceps.",
  product_codes: ["KAE - FORCEPS, ENT"],
  commercial_distribution_status: "In Commercial Distribution",
  prescription_otc_status: "Prescription",
  single_use_indicator: "Not labeled as single use",
  sterility_information: "Sterilization required before use",
  mri_safety_information: "No MRI safety information",
  implantable_device_indicator: "Not implantable",
  latex_information: "Not made with natural rubber latex",
  storage_and_handling_conditions: ["Temperature: 20 C to 25 C"],
  packaging_configurations: ["00192896058644 (Primary, GS1)"],
};

const match: DeviceMatch = {
  record_key: "record-1",
  device_identifier: "00192896058644",
  brand_name: "LARYNGOSCOPY ALLIGATOR FORCEPS",
  company_name: "SONTEC INSTRUMENTS, INC.",
  version_or_model_number: "1301-294",
  catalog_number: "1301-294",
  product_code: "KAE - FORCEPS, ENT",
};

test("loads a single device match and supports device chat", async () => {
  const user = userEvent.setup();
  vi.mocked(searchDevices).mockResolvedValue({ query: "1301-294", matches: [match] });
  vi.mocked(getDevice).mockResolvedValue(device);
  vi.mocked(summarizeDevice).mockResolvedValue({
    content: "This is an FDA-listed forceps model.",
    model_id: "anthropic/claude-sonnet-5",
    used_fallback: false,
    error: null,
  });
  vi.mocked(chatAboutDevice).mockResolvedValue({
    content: "Review the sterility information before use.",
    model_id: "openai/gpt-5.6-luna",
    used_fallback: true,
    error: null,
  });

  render(<DeviceExperience />);
  await user.type(screen.getByLabelText(/UDI barcode text, DI/), "1301-294");
  await user.click(screen.getByRole("button", { name: "Search" }));

  expect(await screen.findByText("Sterilization required before use")).toBeTruthy();
  expect(screen.getByRole("tab", { name: "FDA Results" }).getAttribute("aria-selected")).toBe("true");
  expect(screen.getByRole("tab", { name: "Adverse Events" })).toBeTruthy();
  await user.type(screen.getByLabelText("Ask the analyst"), "What should I review?");
  await user.click(screen.getByRole("button", { name: "Send question" }));

  expect(await screen.findByText("Review the sterility information before use.")).toBeTruthy();
  expect(await screen.findByText(/device chatbot used OpenAI/)).toBeTruthy();
});

test("requires explicit selection when multiple devices match and keeps the result in view", async () => {
  const user = userEvent.setup();
  const scrollIntoView = vi.mocked(HTMLElement.prototype.scrollIntoView);
  vi.mocked(searchDevices).mockResolvedValue({
    query: "forceps",
    matches: [match, { ...match, record_key: "record-2", brand_name: "FORCEPS PLUS" }],
  });
  vi.mocked(getDevice).mockResolvedValue(device);
  vi.mocked(summarizeDevice).mockResolvedValue({
    content: "This is an FDA-listed forceps model.",
    model_id: "anthropic/claude-sonnet-5",
    used_fallback: false,
    error: null,
  });

  render(<DeviceExperience />);
  await user.type(screen.getByLabelText(/UDI barcode text, DI/), "forceps");
  await user.click(screen.getByRole("button", { name: "Search" }));

  expect(await screen.findByRole("heading", { name: "Select A Device Match" })).toBeTruthy();
  expect(getDevice).not.toHaveBeenCalled();

  await user.click(screen.getByRole("button", { name: /LARYNGOSCOPY ALLIGATOR FORCEPS/ }));

  expect(await screen.findByText("Sterilization required before use")).toBeTruthy();
  expect(scrollIntoView).toHaveBeenLastCalledWith({ block: "start" });
});

test("loads device adverse-event evidence from the selected result tab", async () => {
  const user = userEvent.setup();
  vi.mocked(searchDevices).mockResolvedValue({ query: "1301-294", matches: [match] });
  vi.mocked(getDevice).mockResolvedValue(device);
  vi.mocked(summarizeDevice).mockResolvedValue({
    content: "This is an FDA-listed forceps model.",
    model_id: "anthropic/claude-sonnet-5",
    used_fallback: false,
    error: null,
  });
  vi.mocked(getDeviceAdverseEvents).mockResolvedValue({
    matching: {
      field: "device.udi_di",
      value: "00192896058644",
      strategy: "Exact Device Identifier",
      start_date: "2025-01-01",
      end_date: "2025-12-31",
      attempted: [
        {
          field: "device.udi_di",
          value: "00192896058644",
          strategy: "Exact Device Identifier",
        },
      ],
    },
    retrieval: {
      retrieved_reports: 2,
      available_reports: 1200,
      retrieval_limit: 1000,
      truncated: true,
      sort: "date_received:desc",
    },
    overview: {
      total_reports: 2,
      reporting_period_start: "2025-02-01",
      reporting_period_end: "2025-05-01",
    },
    event_types: [
      { event_type: "death", label: "Death", report_count: 0, report_percentage: 0 },
      { event_type: "injury", label: "Injury", report_count: 1, report_percentage: 50 },
      { event_type: "malfunction", label: "Malfunction", report_count: 1, report_percentage: 50 },
      { event_type: "other", label: "Other or not specified", report_count: 0, report_percentage: 0 },
    ],
    trends: [
      {
        period: "2025 Q1",
        total_reports: 1,
        death_reports: 0,
        injury_reports: 1,
        malfunction_reports: 0,
        other_reports: 0,
      },
      {
        period: "2025 Q2",
        total_reports: 1,
        death_reports: 0,
        injury_reports: 0,
        malfunction_reports: 1,
        other_reports: 0,
      },
    ],
    device_problems: [
      { term: "Material rupture", report_count: 1, report_percentage: 50 },
    ],
    patient_problems: [
      { term: "Pain", report_count: 1, report_percentage: 50 },
    ],
    limitations: ["A report does not establish causality."],
    source: "FDA Manufacturer and User Facility Device Experience (MAUDE) via openFDA",
  });

  render(<DeviceExperience />);
  await user.type(screen.getByLabelText(/UDI barcode text, DI/), "1301-294");
  await user.click(screen.getByRole("button", { name: "Search" }));
  await screen.findByText("Sterilization required before use");
  await user.click(screen.getByRole("tab", { name: "Adverse Events" }));

  await user.clear(screen.getByLabelText("Start date"));
  await user.type(screen.getByLabelText("Start date"), "2025-01-01");
  await user.clear(screen.getByLabelText("End date"));
  await user.type(screen.getByLabelText("End date"), "2025-12-31");
  await user.click(screen.getByRole("button", { name: "Load adverse events" }));

  expect(await screen.findByText("Material rupture")).toBeTruthy();
  expect(screen.getByText("Pain")).toBeTruthy();
  expect(screen.getAllByText("Exact Device Identifier")).toHaveLength(2);
  expect(screen.getByText(/openFDA reported 1,200 matching reports/)).toBeTruthy();
  expect(getDeviceAdverseEvents).toHaveBeenCalledWith(
    "record-1",
    "2025-01-01",
    "2025-12-31",
  );
});

test("validates the device adverse-event date range before calling the API", async () => {
  const user = userEvent.setup();
  render(<DeviceAdverseEventIntelligence device={device} />);

  await user.clear(screen.getByLabelText("Start date"));
  await user.type(screen.getByLabelText("Start date"), "2025-12-31");
  await user.clear(screen.getByLabelText("End date"));
  await user.type(screen.getByLabelText("End date"), "2025-01-01");
  await user.click(screen.getByRole("button", { name: "Load adverse events" }));

  expect((await screen.findByRole("alert")).textContent).toContain(
    "The start date must be on or before the end date.",
  );
  expect(getDeviceAdverseEvents).not.toHaveBeenCalled();
});
