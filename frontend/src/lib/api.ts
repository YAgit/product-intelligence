import type {
  AnalysisResponse,
  ChatMessage,
  Device,
  DeviceSearchResponse,
  Drug,
  DrugSearchResponse,
} from "@/types/api";

export const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ApiErrorBody = {
  detail?: string;
};

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "The request could not be completed.";
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new Error(body.detail ?? `API request failed with status ${response.status}.`);
  }

  return response.json() as Promise<T>;
}

export function searchDrugs(query: string): Promise<DrugSearchResponse> {
  return apiRequest(`/api/v1/drugs/search?query=${encodeURIComponent(query)}`);
}

export function getDrug(productNdc: string): Promise<Drug> {
  return apiRequest(`/api/v1/drugs/${encodeURIComponent(productNdc)}`);
}

export function summarizeDrug(productNdc: string): Promise<AnalysisResponse> {
  return apiRequest(`/api/v1/drugs/${encodeURIComponent(productNdc)}/summary`, { method: "POST" });
}

export function chatAboutDrug(
  productNdc: string,
  message: string,
  history: ChatMessage[],
): Promise<AnalysisResponse> {
  return apiRequest(`/api/v1/drugs/${encodeURIComponent(productNdc)}/chat`, {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });
}

export function searchDevices(query: string): Promise<DeviceSearchResponse> {
  return apiRequest(`/api/v1/devices/search?query=${encodeURIComponent(query)}`);
}

export function getDevice(recordKey: string): Promise<Device> {
  return apiRequest(`/api/v1/devices/${encodeURIComponent(recordKey)}`);
}

export function summarizeDevice(recordKey: string): Promise<AnalysisResponse> {
  return apiRequest(`/api/v1/devices/${encodeURIComponent(recordKey)}/summary`, { method: "POST" });
}

export function chatAboutDevice(
  recordKey: string,
  message: string,
  history: ChatMessage[],
): Promise<AnalysisResponse> {
  return apiRequest(`/api/v1/devices/${encodeURIComponent(recordKey)}/chat`, {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });
}
