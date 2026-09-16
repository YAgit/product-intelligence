"use client";

import type { FormEvent } from "react";
import { useState } from "react";

import { ChatPanel } from "@/components/chat-panel";
import {
  BusyOverlay,
  Disclaimer,
  ModeTabs,
  Notice,
  PageHero,
  PanelHeading,
} from "@/components/page-chrome";
import { AdverseEventIntelligence } from "@/features/drugs/adverse-event-intelligence";
import {
  chatAboutDrug,
  errorMessage,
  getDrug,
  searchDrugs,
  summarizeDrug,
} from "@/lib/api";
import type { AnalysisResponse, ChatMessage, Drug, DrugMatch } from "@/types/api";

function valueList(values: string[]) {
  return values.length > 0 ? values.join(", ") : "Not available";
}

function scrollToPanel(id: string) {
  window.setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }), 0);
}

export function DrugExperience() {
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<DrugMatch[]>([]);
  const [drug, setDrug] = useState<Drug | null>(null);
  const [summary, setSummary] = useState<AnalysisResponse | null>(null);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [chatNotice, setChatNotice] = useState<string | null>(null);
  const [busyMessage, setBusyMessage] = useState<string | null>(null);

  const busy = busyMessage !== null;
  const status = drug ? "Result loaded" : error ? "Needs attention" : matches.length > 1 ? "Selection needed" : "Ready to search";

  function resetResult() {
    setDrug(null);
    setSummary(null);
    setHistory([]);
    setMessage("");
    setChatNotice(null);
  }

  async function loadProduct(productNdc: string) {
    setBusyMessage("Loading FDA product details and AI overview.");
    setError(null);
    setNotice(null);
    resetResult();

    try {
      const [selectedDrug, productSummary] = await Promise.all([
        getDrug(productNdc),
        summarizeDrug(productNdc),
      ]);
      setDrug(selectedDrug);
      setSummary(productSummary);
      if (productSummary.used_fallback) {
        setChatNotice("Anthropic was unavailable, so OpenAI produced the product overview.");
      } else if (productSummary.error) {
        setChatNotice(productSummary.error);
      }
      scrollToPanel("details-panel");
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
      setError("Enter a product name or NDC code.");
      return;
    }

    setBusyMessage("Searching the live FDA NDC directory.");
    try {
      const response = await searchDrugs(normalizedQuery);
      setMatches(response.matches);
      if (response.matches.length === 0) {
        setError("No FDA NDC matches were found for that search.");
      } else if (response.matches.length === 1) {
        setBusyMessage(null);
        await loadProduct(response.matches[0].product_ndc);
      } else {
        setNotice("Multiple products matched. Select the exact FDA product to continue.");
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
    if (!drug || !question) return;

    setBusyMessage("The pharmaceutical analyst is preparing a response.");
    setChatNotice(null);
    try {
      const response = await chatAboutDrug(drug.product_ndc, question, history);
      setHistory((current) => [
        ...current,
        { role: "user", content: question },
        { role: "assistant", content: response.content },
      ]);
      setMessage("");
      if (response.used_fallback) {
        setChatNotice("Anthropic was unavailable, so the chatbot used OpenAI for this reply.");
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
        <ModeTabs active="drug" />
        <PageHero
          eyebrow="Pharmaceutical Product Intelligence"
          title="Drug Search"
          description="Search a drug by product name or NDC code, review FDA directory details, then ask a pharmaceutical product analyst about the selected product."
          source="Live NDC directory"
          analyst="Pharma analyst chatbot"
          query={query}
          status={status}
        />

        <Disclaimer title="Important Drug Disclaimer">
          <p>
            This application provides FDA directory data and AI-generated responses for general informational purposes only. It is not medical advice, diagnosis, treatment, pharmacy, emergency, legal, regulatory, or compliance guidance.
          </p>
          <p>
            Verify product information with official FDA labeling and consult an appropriate qualified professional before acting. If this is an emergency, contact emergency services immediately.
          </p>
        </Disclaimer>

        <main className="content-stack">
          <section className="top-grid">
            <section className="panel">
              <PanelHeading title="Search" badge="Live FDA lookup" />
              <form className="search-form" onSubmit={handleSearch}>
                <label htmlFor="drug-query">Product name or NDC code</label>
                <div className="search-row">
                  <input
                    id="drug-query"
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    placeholder="Example: Eliquis or 00074-4331"
                    disabled={busy}
                  />
                  <button type="submit" disabled={busy}>Search</button>
                </div>
              </form>
              <div className="search-notes">
                <div><strong>Accepted inputs</strong><p>Brand name, generic name, product NDC, or package NDC.</p></div>
                <div><strong>Search behavior</strong><p>Ambiguous names show a shortlist before details and chat load.</p></div>
              </div>
              {error && <Notice tone="error" label="Search update:">{error}</Notice>}
              {drug && <Notice tone="success" label="Search ready:">FDA details and chat are ready for {drug.brand_name}.</Notice>}
              {!drug && notice && <Notice tone="info" label="Selection needed:">{notice}</Notice>}
            </section>

            <aside className="panel status-panel">
              <PanelHeading title="Search Status" badge={drug ? "Loaded" : error ? "Attention" : "Idle"} />
              <dl className="status-list">
                <div><dt>Query</dt><dd>{query || "Waiting for input"}</dd></div>
                <div><dt>Selection</dt><dd>{drug?.brand_name ?? "No product selected"}</dd></div>
                <div><dt>Data source</dt><dd>openFDA NDC</dd></div>
              </dl>
            </aside>
          </section>

          {matches.length > 1 && !drug && (
            <section className="panel" id="match-panel">
              <PanelHeading title="Select A Product Match" badge={`${matches.length} matches`} />
              <p className="section-copy">Choose the exact FDA-listed product to load full details and enable the chatbot.</p>
              <div className="match-grid">
                {matches.map((match) => (
                  <button className="match-card" key={match.product_ndc} onClick={() => loadProduct(match.product_ndc)} disabled={busy}>
                    <span className="match-title">{match.brand_name}</span>
                    <span><strong>Generic:</strong> {match.generic_name}</span>
                    <span><strong>Labeler:</strong> {match.labeler_name}</span>
                    <span><strong>Product NDC:</strong> {match.product_ndc}</span>
                    <span><strong>Dosage:</strong> {match.dosage_form}</span>
                  </button>
                ))}
              </div>
            </section>
          )}

          <section className="panel" id="details-panel">
            <PanelHeading title="FDA Product Details" badge={drug ? "Result loaded" : "Waiting for search"} />
            {drug ? (
              <>
                <div className="result-banner">
                  <div><p className="result-kicker">Selected product</p><h2>{drug.brand_name}</h2></div>
                  <div className="result-tags"><span>{drug.product_ndc}</span><span>{drug.dosage_form}</span></div>
                </div>
                <div className="detail-grid">
                  <article><h3>Product</h3><p><strong>Brand:</strong> {drug.brand_name}</p><p><strong>Generic:</strong> {drug.generic_name}</p><p><strong>Product NDC:</strong> {drug.product_ndc}</p></article>
                  <article><h3>Labeler</h3><p><strong>Company:</strong> {drug.labeler_name}</p><p><strong>Package NDCs:</strong> {valueList(drug.package_ndcs)}</p></article>
                  <article><h3>Route</h3><p><strong>Dosage:</strong> {drug.dosage_form}</p><p><strong>Route:</strong> {valueList(drug.route)}</p><p><strong>Ingredients:</strong> {valueList(drug.active_ingredients)}</p></article>
                  <article><h3>Status</h3><p><strong>Category:</strong> {drug.marketing_category}</p><p><strong>Type:</strong> {drug.product_type}</p><p><strong>Application:</strong> {drug.application_number}</p><p><strong>Listed through:</strong> {drug.listing_expiration_date}</p><p><strong>Marketed since:</strong> {drug.marketing_start_date}</p></article>
                </div>
                <article className="detail-card detail-wide"><h3>Packaging</h3>{drug.package_descriptions.length ? <ul>{drug.package_descriptions.map((item) => <li key={item}>{item}</li>)}</ul> : <p>Package descriptions are not available.</p>}</article>
              </>
            ) : <p className="empty-state">Product identity, labeling, route, status, and packaging details will appear after a successful search.</p>}
          </section>

          {drug && <AdverseEventIntelligence key={drug.product_ndc} drug={drug} />}

          <ChatPanel
            title="Pharma Analyst Chatbot"
            summaryLabel="Product overview"
            summary={summary}
            selectedName={drug?.brand_name ?? null}
            history={history}
            message={message}
            setMessage={setMessage}
            onSubmit={handleChat}
            busy={busy}
            notice={chatNotice}
            placeholder={drug ? `Ask about ${drug.brand_name}` : "Select a product first"}
            emptyMessage="Select a product first, then ask a pharmaceutical product question."
            disclaimer="AI responses are informational only and must not be used for diagnosis, treatment, prescribing, dispensing, or other important decisions."
          />
        </main>
      </div>
    </>
  );
}
