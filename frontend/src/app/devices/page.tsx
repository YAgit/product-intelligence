import type { Metadata } from "next";

import { DeviceExperience } from "@/features/devices/device-experience";

export const metadata: Metadata = {
  title: "Device Search | Product Intelligence Platform",
};

export default function DevicesPage() {
  return <DeviceExperience />;
}
