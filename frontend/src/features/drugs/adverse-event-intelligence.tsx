"use client";

import type { FormEvent } from "react";
import { useState } from "react";

import { Notice, PanelHeading } from "@/components/page-chrome";
import { errorMessage, getDrugAdverseEvents } from "@/lib/api";
import type { AdverseEventAnalytics, Drug } from "@/types/api";

const numberFormatter = new Intl.NumberFormat("en-US");

function defaultDateRange() {
  const end = new Date();
  const start = new Date(end);
  start.setUTCFullYear(start.getUTCFullYear() - 1);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
}

function formatDate(value: string | null) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function count(value: number) {
  return numberFormatter.format(value);
}

type Props = {
  drug: Drug;
};

export function AdverseEventIntelligence({ drug }: Props) {
  const initialRange = defaultDateRange();
  const [startDate, setStartDate] = useState(initialRange.start);
  const [endDate, setEndDate] = useState(initialRange.end);
  const [analytics, setAnalytics] = useState<AdverseEventAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setAnalytics(null);

    if (!startDate || !endDate) {
      setError("Choose both a start date and an end date.");
      return;
    }
    if (startDate > endDate) {
      setError("The start date must be on or before the end date.");
      return;
    }

    setLoading(true);
    try {
      setAnalytics(await getDrugAdverseEvents(drug.product_ndc, startDate, endDate));
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  const maximumTrendCount = Math.max(
    1,
    ...(analytics?.trends.map((trend) => trend.total_reports) ?? []),
  );

  return (
    <section className="panel" id="adverse-events-panel">
      <PanelHeading
        title="Adverse Event Intelligence"
        badge={analytics ? `${count(analytics.retrieval.retrieved_reports)} reports retrieved` : "FAERS evidence"}
      />
      <p className="section-copy">
        Explore FDA adverse-event reports associated with the selected brand. These reports describe observed reporting patterns; they do not establish causality, incidence, prevalence, or comparative product risk.
      </p>

      <form className="date-range-form" onSubmit={handleSubmit}>
        <label>
          Start date
          <input
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            disabled={loading}
          />
        </label>
        <label>
          End date
          <input
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
            disabled={loading}
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Retrieving reports" : "Load adverse events"}
        </button>
      </form>

      {error && <Notice tone="error" label="Adverse-event update:">{error}</Notice>}
      {!analytics && !error && (
        <p className="empty-state">
          Choose a reporting range to retrieve deterministic FAERS analytics for {drug.brand_name}.
        </p>
      )}

      {analytics && (
        <div className="adverse-event-results">
          <section className="evidence-callout" aria-label="FAERS matching criteria">
            <h3>Evidence and matching criteria</h3>
            <dl className="evidence-grid">
              <div><dt>Matching field</dt><dd>{analytics.matching.field}</dd></div>
              <div><dt>Exact value</dt><dd>{analytics.matching.value}</dd></div>
              <div><dt>Selected range</dt><dd>{formatDate(analytics.matching.start_date)}–{formatDate(analytics.matching.end_date)}</dd></div>
              <div><dt>Source</dt><dd>{analytics.source}</dd></div>
            </dl>
          </section>

          {analytics.retrieval.truncated && (
            <Notice tone="info" label="Retrieval limit:">
              openFDA reported {count(analytics.retrieval.available_reports)} matching reports. The calculations below use the {count(analytics.retrieval.retrieved_reports)} most recently received reports returned under the {count(analytics.retrieval.retrieval_limit)}-report retrieval limit.
            </Notice>
          )}

          {analytics.overview.total_reports === 0 ? (
            <Notice tone="info" label="No reports retrieved:">
              No matching reports were returned for this exact brand name and date range. This does not establish product safety or the absence of adverse events.
            </Notice>
          ) : (
            <>
              <section aria-labelledby="reporting-overview-heading">
                <h3 className="subsection-heading" id="reporting-overview-heading">Reporting overview</h3>
                <div className="metric-grid">
                  <article><span>Total retrieved</span><strong>{count(analytics.overview.total_reports)}</strong></article>
                  <article><span>Serious reports</span><strong>{count(analytics.overview.serious_reports)}</strong></article>
                  <article><span>Non-serious reports</span><strong>{count(analytics.overview.non_serious_reports)}</strong></article>
                  <article><span>Classified serious</span><strong>{analytics.overview.serious_percentage.toFixed(1)}%</strong></article>
                </div>
                <p className="reporting-period">
                  Reporting period represented in the retrieved records: {formatDate(analytics.overview.reporting_period_start)}–{formatDate(analytics.overview.reporting_period_end)}.
                </p>
              </section>

              <section aria-labelledby="serious-outcomes-heading">
                <h3 className="subsection-heading" id="serious-outcomes-heading">Serious outcomes represented</h3>
                <div className="outcome-grid">
                  {analytics.outcomes.map((outcome) => (
                    <article key={outcome.outcome}>
                      <span>{outcome.label}</span>
                      <strong>{count(outcome.report_count)}</strong>
                    </article>
                  ))}
                </div>
              </section>

              <section aria-labelledby="quarterly-trends-heading">
                <h3 className="subsection-heading" id="quarterly-trends-heading">Quarterly reporting trend</h3>
                <div className="trend-legend"><span>Total reports</span><span>Serious reports</span></div>
                <div className="trend-chart">
                  {analytics.trends.map((trend) => (
                    <div className="trend-row" key={trend.period}>
                      <strong>{trend.period}</strong>
                      <div className="trend-bars">
                        <div className="trend-bar trend-bar-total" style={{ width: `${(trend.total_reports / maximumTrendCount) * 100}%` }} />
                        <div className="trend-bar trend-bar-serious" style={{ width: `${(trend.serious_reports / maximumTrendCount) * 100}%` }} />
                      </div>
                      <span>{count(trend.total_reports)} / {count(trend.serious_reports)}</span>
                    </div>
                  ))}
                </div>
              </section>

              <section aria-labelledby="reaction-analysis-heading">
                <h3 className="subsection-heading" id="reaction-analysis-heading">Most frequently reported reactions</h3>
                {analytics.reactions.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead><tr><th>FDA reaction term</th><th>Reports</th><th>% of retrieved reports</th><th>Serious reports</th></tr></thead>
                      <tbody>
                        {analytics.reactions.map((reaction) => (
                          <tr key={reaction.term}>
                            <th scope="row">{reaction.term}</th>
                            <td>{count(reaction.report_count)}</td>
                            <td>{reaction.report_percentage.toFixed(1)}%</td>
                            <td>{count(reaction.serious_report_count)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : <p className="empty-state">The retrieved reports did not contain reaction terms.</p>}
              </section>
            </>
          )}

          <section className="limitations-panel" aria-labelledby="faers-limitations-heading">
            <h3 id="faers-limitations-heading">How to interpret FAERS data</h3>
            <ul>{analytics.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
            <p>This application is a research aid and does not replace pharmacovigilance review, medical judgment, or regulatory assessment.</p>
          </section>
        </div>
      )}
    </section>
  );
}
