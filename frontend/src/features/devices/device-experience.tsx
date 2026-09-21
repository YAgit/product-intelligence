"use client";

import type { FormEvent } from "react";
import { useLayoutEffect, useRef, useState } from "react";

import { ChatPanel } from "@/components/chat-panel";
import {
  BusyOverlay,
  Disclaimer,
  ModeTabs,
  Notice,
  PageHero,
  PanelHeading,
  ResultTabs,
} from "@/components/page-chrome";
import { DeviceAdverseEventIntelligence } from "@/features/devices/device-adverse-event-intelligence";
import {
  chatAboutDevice,
  errorMessage,
  getDevice,
  searchDevices,
  summarizeDevice,
} from "@/lib/api";
import type { AnalysisResponse, ChatMessage, Device, DeviceMatch } from "@/types/api";

function scrollToPanel(id: string) {
  window.setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }), 0);
}

export function DeviceExperience() {
  const detailsPanelRef = useRef<HTMLElement>(null);
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<DeviceMatch[]>([]);
  const [device, setDevice] = useState<Device | null>(null);
  const [summary, setSummary] = useState<AnalysisResponse | null>(null);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [chatNotice, setChatNotice] = useState<string | null>(null);
  const [busyMessage, setBusyMessage] = useState<string | null>(null);
  const [resultTab, setResultTab] = useState<"fda" | "adverse-events">("fda");

  const busy = busyMessage !== null;
  const status = device ? "Result loaded" : error ? "Needs attention" : matches.length > 1 ? "Selection needed" : "Ready to search";

  useLayoutEffect(() => {
    if (device) {
      detailsPanelRef.current?.scrollIntoView({ block: "start" });
    }
  }, [device]);

  function resetResult() {
    setDevice(null);
    setSummary(null);
    setHistory([]);
    setMessage("");
    setChatNotice(null);
    setResultTab("fda");
  }

  async function loadDevice(recordKey: string) {
    setBusyMessage("Loading FDA device details and AI overview.");
    setError(null);
    setNotice(null);
    resetResult();

    try {
      const [selectedDevice, deviceSummary] = await Promise.all([
        getDevice(recordKey),
        summarizeDevice(recordKey),
      ]);
      setDevice(selectedDevice);
      setSummary(deviceSummary);
      if (deviceSummary.used_fallback) {
        setChatNotice("Anthropic was unavailable, so OpenAI produced the device overview.");
      } else if (deviceSummary.error) {
        setChatNotice(deviceSummary.error);
      }
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusyMessage(null);
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedQuery = input.trim();
    setQuery(normalizedQuery);
    setMatches([]);
    setError(null);
    setNotice(null);
    resetResult();

    if (!normalizedQuery) {
      setError("Enter UDI barcode text, a Device Identifier, brand name, or model/catalog number.");
      return;
    }

    setBusyMessage("Searching the live FDA Device UDI directory.");
    try {
      const response = await searchDevices(normalizedQuery);
      setMatches(response.matches);
      if (response.matches.length === 0) {
        setError("No FDA device matches were found for that search.");
      } else if (response.matches.length === 1) {
        setBusyMessage(null);
        await loadDevice(response.matches[0].record_key);
      } else {
        setNotice("Multiple devices matched. Select the exact FDA device to continue.");
        scrollToPanel("match-panel");
      }
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusyMessage(null);
    }
  }

  async function handleChat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = message.trim();
    if (!device || !question) return;

    setBusyMessage("The device analyst is preparing a response.");
    setChatNotice(null);
    try {
      const response = await chatAboutDevice(device.record_key, question, history);
      setHistory((current) => [
        ...current,
        { role: "user", content: question },
        { role: "assistant", content: response.content },
      ]);
      setMessage("");
      if (response.used_fallback) {
        setChatNotice("Anthropic was unavailable, so the device chatbot used OpenAI for this reply.");
      } else if (response.error) {
        setChatNotice(response.error);
      }
      scrollToPanel("chat-panel");
    } catch (requestError) {
      setChatNotice(errorMessage(requestError));
    } finally {
      setBusyMessage(null);
    }
  }

  return (
    <>
      <BusyOverlay message={busyMessage} />
      <div className="page-shell">
        <ModeTabs active="device" />
        <PageHero
          eyebrow="Pharmaceutical Device Intelligence"
          title="Device Search"
          description="Search a medical device by UDI barcode text, Device Identifier, brand name, or model and catalog number, then review FDA details and ask a device analyst."
          source="Live Device UDI directory"
          analyst="Device analyst chatbot"
          query={query}
          status={status}
        />

        <Disclaimer title="Important Device Disclaimer">
          <p>
            This application provides FDA UDI data and AI-generated responses for general informational purposes only. It is not medical advice, treatment, device-selection, emergency, legal, regulatory, procurement, or compliance guidance.
          </p>
          <p>
            Verify device information with official labeling and consult an appropriate qualified professional before acting. If this is an emergency, contact emergency services immediately.
          </p>
        </Disclaimer>

        <main className="content-stack">
          <section className="top-grid">
            <section className="panel">
              <PanelHeading title="Search" badge="Live FDA lookup" />
              <form className="search-form" onSubmit={handleSearch}>
                <label htmlFor="device-query">UDI barcode text, DI, brand name, or model/catalog number</label>
                <div className="search-row">
                  <input
                    id="device-query"
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    placeholder="Example: (01)00810000000018 or 1301-294"
                    disabled={busy}
                  />
                  <button type="submit" disabled={busy}>Search</button>
                </div>
              </form>
              <div className="search-notes">
                <div><strong>Accepted inputs</strong><p>UDI barcode text, Device Identifier, brand name, or model/catalog number.</p></div>
                <div><strong>Search behavior</strong><p>Ambiguous searches show a shortlist before details and chat load.</p></div>
              </div>
              {error && <Notice tone="error" label="Search update:">{error}</Notice>}
              {device && <Notice tone="success" label="Search ready:">FDA details and chat are ready for {device.brand_name}.</Notice>}
              {!device && notice && <Notice tone="info" label="Selection needed:">{notice}</Notice>}
            </section>

            <aside className="panel status-panel">
              <PanelHeading title="Search Status" badge={device ? "Loaded" : error ? "Attention" : "Idle"} />
              <dl className="status-list">
                <div><dt>Query</dt><dd>{query || "Waiting for input"}</dd></div>
                <div><dt>Selection</dt><dd>{device?.brand_name ?? "No device selected"}</dd></div>
                <div><dt>Data source</dt><dd>openFDA Device UDI</dd></div>
              </dl>
            </aside>
          </section>

          {matches.length > 1 && !device && (
            <section className="panel" id="match-panel">
              <PanelHeading title="Select A Device Match" badge={`${matches.length} matches`} />
              <p className="section-copy">Choose the exact FDA-listed device to load full details and enable the chatbot.</p>
              <div className="match-grid">
                {matches.map((match) => (
                  <button className="match-card" key={match.record_key} onClick={() => loadDevice(match.record_key)} disabled={busy}>
                    <span className="match-title">{match.brand_name}</span>
                    <span><strong>Device Identifier:</strong> {match.device_identifier}</span>
                    <span><strong>Company:</strong> {match.company_name}</span>
                    <span><strong>Model:</strong> {match.version_or_model_number}</span>
                    <span><strong>Catalog:</strong> {match.catalog_number}</span>
                  </button>
                ))}
              </div>
            </section>
          )}

          {device ? (
            <section className="result-section" id="details-panel" ref={detailsPanelRef}>
              <ResultTabs active={resultTab} onChange={setResultTab} label="Device result sections" />
              {resultTab === "fda" ? (
                <section className="panel" id="fda-results-panel" role="tabpanel">
                  <PanelHeading title="FDA Device Details" badge="Result loaded" />
                  <div className="result-banner">
                    <div><p className="result-kicker">Selected device</p><h2>{device.brand_name}</h2></div>
                    <div className="result-tags"><span>{device.device_identifier}</span><span>{device.version_or_model_number}</span></div>
                  </div>
                  <div className="detail-grid">
                    <article><h3>Identity</h3><p><strong>Device Identifier:</strong> {device.device_identifier}</p><p><strong>Brand name:</strong> {device.brand_name}</p><p><strong>Company:</strong> {device.company_name}</p></article>
                    <article><h3>Modeling</h3><p><strong>Version or model number:</strong> {device.version_or_model_number}</p><p><strong>Catalog number:</strong> {device.catalog_number}</p><p><strong>FDA product codes:</strong> {device.product_codes.join(", ") || "Not available"}</p></article>
                    <article><h3>Usage</h3><p><strong>Commercial distribution:</strong> {device.commercial_distribution_status}</p><p><strong>Prescription or OTC:</strong> {device.prescription_otc_status}</p><p><strong>Single-use indicator:</strong> {device.single_use_indicator}</p></article>
                    <article><h3>Safety</h3><p><strong>Sterility information:</strong> {device.sterility_information}</p><p><strong>MRI safety:</strong> {device.mri_safety_information}</p><p><strong>Implantable-device indicator:</strong> {device.implantable_device_indicator}</p><p><strong>Latex information:</strong> {device.latex_information}</p></article>
                    <article><h3>Description</h3><p>{device.device_description}</p></article>
                    <article><h3>Storage And Handling</h3>{device.storage_and_handling_conditions.length ? <ul>{device.storage_and_handling_conditions.map((item) => <li key={item}>{item}</li>)}</ul> : <p>Storage and handling details are not available.</p>}</article>
                  </div>
                  <article className="detail-card detail-wide"><h3>Packaging Configurations</h3>{device.packaging_configurations.length ? <ul>{device.packaging_configurations.map((item) => <li key={item}>{item}</li>)}</ul> : <p>Packaging configurations are not available.</p>}</article>
                </section>
              ) : <DeviceAdverseEventIntelligence key={device.record_key} device={device} />}
            </section>
          ) : (
            <section className="panel" id="details-panel" ref={detailsPanelRef}>
              <PanelHeading title="FDA Device Details" badge="Waiting for search" />
              <p className="empty-state">Device identity, modeling, usage, safety, storage, and packaging details will appear after a successful search.</p>
            </section>
          )}

          <ChatPanel
            title="Device Analyst Chatbot"
            summaryLabel="Device overview"
            summary={summary}
            selectedName={device?.brand_name ?? null}
            history={history}
            message={message}
            setMessage={setMessage}
            onSubmit={handleChat}
            busy={busy}
            notice={chatNotice}
            placeholder={device ? `Ask about ${device.brand_name}` : "Select a device first"}
            emptyMessage="Select a device first, then ask a medical-device question."
            disclaimer="AI responses are informational only and must not be used for device selection, patient care, procurement, or other important decisions."
          />
        </main>
      </div>
    </>
  );
}
