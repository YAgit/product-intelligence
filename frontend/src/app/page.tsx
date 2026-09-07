import type { Metadata } from "next";

import { DrugExperience } from "@/features/drugs/drug-experience";

export const metadata: Metadata = {
  title: "Drug Search | Product Intelligence Platform",
};

export default function Home() {
  return <DrugExperience />;
}
