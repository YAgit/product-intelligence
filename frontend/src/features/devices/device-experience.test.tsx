import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

import { DeviceExperience } from "@/features/devices/device-experience";
import {
  chatAboutDevice,
  getDevice,
  searchDevices,
  summarizeDevice,
} from "@/lib/api";
import type { Device, DeviceMatch } from "@/types/api";

vi.mock("@/lib/api", () => ({
  searchDevices: vi.fn(),
  getDevice: vi.fn(),
  summarizeDevice: vi.fn(),
  chatAboutDevice: vi.fn(),
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
  await user.type(screen.getByLabelText("Ask the analyst"), "What should I review?");
  await user.click(screen.getByRole("button", { name: "Send question" }));

  expect(await screen.findByText("Review the sterility information before use.")).toBeTruthy();
  expect(await screen.findByText(/device chatbot used OpenAI/)).toBeTruthy();
});

test("requires explicit selection when multiple devices match", async () => {
  const user = userEvent.setup();
  vi.mocked(searchDevices).mockResolvedValue({
    query: "forceps",
    matches: [match, { ...match, record_key: "record-2", brand_name: "FORCEPS PLUS" }],
  });

  render(<DeviceExperience />);
  await user.type(screen.getByLabelText(/UDI barcode text, DI/), "forceps");
  await user.click(screen.getByRole("button", { name: "Search" }));

  expect(await screen.findByRole("heading", { name: "Select A Device Match" })).toBeTruthy();
  expect(getDevice).not.toHaveBeenCalled();
});
