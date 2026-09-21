"use client";

import type { FormEvent } from "react";
import { useState } from "react";

import { Notice, PanelHeading } from "@/components/page-chrome";
import { errorMessage, getDeviceAdverseEvents } from "@/lib/api";
import type { Device, DeviceAdverseEventAnalytics } from "@/types/api";

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

type ProblemTableProps = {
  heading: string;
  headingId: string;
  emptyMessage: string;
  problems: DeviceAdverseEventAnalytics["device_problems"];
};

function ProblemTable({ heading, headingId, emptyMessage, problems }: ProblemTableProps) {
  return (
    <section aria-labelledby={headingId}>
      <h3 className="subsection-heading" id={headingId}>{heading}</h3>
      {problems.length ? (
        <div className="table-scroll">
          <table>
            <thead><tr><th>FDA coded term</th><th>Reports</th><th>% of retrieved reports</th></tr></thead>
            <tbody>
              {problems.map((problem) => (
                <tr key={problem.term}>
                  <th scope="row">{problem.term}</th>
                  <td>{count(problem.report_count)}</td>
                  <td>{problem.report_percentage.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="empty-state">{emptyMessage}</p>}
    </section>
  );
}

export function DeviceAdverseEventIntelligence({ device }: { device: Device }) {
  const initialRange = defaultDateRange();
  const [startDate, setStartDate] = useState(initialRange.start);
  const [endDate, setEndDate] = useState(initialRange.end);
  const [analytics, setAnalytics] = useState<DeviceAdverseEventAnalytics | null>(null);
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
      setAnalytics(await getDeviceAdverseEvents(device.record_key, startDate, endDate));
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
    <section className="panel" id="adverse-events-panel" role="tabpanel">
      <PanelHeading
        title="Device Adverse Event Intelligence"
        badge={analytics ? `${count(analytics.retrieval.retrieved_reports)} reports retrieved` : "MAUDE evidence"}
      />
      <p className="section-copy">
        Explore FDA medical-device reports associated with the selected device identity. These reports describe observed reporting patterns; they do not establish causality, incidence, or comparative device risk.
      </p>

      <form className="date-range-form" onSubmit={handleSubmit}>
        <label>
          Start date
          <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} disabled={loading} />
        </label>
        <label>
          End date
          <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} disabled={loading} />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Retrieving reports" : "Load adverse events"}
        </button>
      </form>

      {error && <Notice tone="error" label="Adverse-event update:">{error}</Notice>}
      {!analytics && !error && (
        <p className="empty-state">
          Choose a reporting range to retrieve deterministic MAUDE analytics for {device.brand_name}.
        </p>
      )}

      {analytics && (
        <div className="adverse-event-results">
          <section className="evidence-callout" aria-label="MAUDE matching criteria">
            <h3>Evidence and matching criteria</h3>
            <dl className="evidence-grid">
              <div><dt>Selected strategy</dt><dd>{analytics.matching.strategy}</dd></div>
              <div><dt>Matching field</dt><dd>{analytics.matching.field ?? "No query returned reports"}</dd></div>
              <div><dt>Exact value</dt><dd>{analytics.matching.value ?? "No matching value selected"}</dd></div>
              <div><dt>Selected range</dt><dd>{formatDate(analytics.matching.start_date)}–{formatDate(analytics.matching.end_date)}</dd></div>
              <div><dt>Source</dt><dd>{analytics.source}</dd></div>
              <div><dt>Queries attempted</dt><dd>{analytics.matching.attempted.map((match) => match.strategy).join(" → ")}</dd></div>
            </dl>
          </section>

          {analytics.retrieval.truncated && (
            <Notice tone="info" label="Retrieval limit:">
              openFDA reported {count(analytics.retrieval.available_reports)} matching reports. The calculations below use the {count(analytics.retrieval.retrieved_reports)} most recently received reports returned under the {count(analytics.retrieval.retrieval_limit)}-report retrieval limit.
            </Notice>
          )}

          {analytics.overview.total_reports === 0 ? (
            <Notice tone="info" label="No reports retrieved:">
              No reports were returned after trying the disclosed exact-match hierarchy for this date range. This does not establish device safety or the absence of adverse events.
            </Notice>
          ) : (
            <>
              <section aria-labelledby="device-reporting-overview-heading">
                <h3 className="subsection-heading" id="device-reporting-overview-heading">Reporting overview</h3>
                <div className="metric-grid device-metric-grid">
                  <article><span>Total retrieved</span><strong>{count(analytics.overview.total_reports)}</strong></article>
                  {analytics.event_types.map((eventType) => (
                    <article key={eventType.event_type}>
                      <span>{eventType.label}</span>
                      <strong>{count(eventType.report_count)}</strong>
                      <small>{eventType.report_percentage.toFixed(1)}% of retrieved</small>
                    </article>
                  ))}
                </div>
                <p className="reporting-period">
                  Reporting period represented in the retrieved records: {formatDate(analytics.overview.reporting_period_start)}–{formatDate(analytics.overview.reporting_period_end)}.
                </p>
              </section>

              <section aria-labelledby="device-quarterly-trends-heading">
                <h3 className="subsection-heading" id="device-quarterly-trends-heading">Quarterly reporting trend</h3>
                <div className="trend-legend"><span>Total reports</span></div>
                <div className="trend-chart">
                  {analytics.trends.map((trend) => (
                    <div className="trend-row device-trend-row" key={trend.period}>
                      <strong>{trend.period}</strong>
                      <div className="trend-bars">
                        <div className="trend-bar trend-bar-total" style={{ width: `${(trend.total_reports / maximumTrendCount) * 100}%` }} />
                      </div>
                      <span>{count(trend.total_reports)} total · D {count(trend.death_reports)} · I {count(trend.injury_reports)} · M {count(trend.malfunction_reports)}</span>
                    </div>
                  ))}
                </div>
              </section>

              <ProblemTable
                heading="Most frequently reported device problems"
                headingId="device-problems-heading"
                emptyMessage="The retrieved reports did not contain FDA device-problem terms."
                problems={analytics.device_problems}
              />
              <ProblemTable
                heading="Most frequently reported patient problems"
                headingId="patient-problems-heading"
                emptyMessage="The retrieved reports did not contain FDA patient-problem terms."
                problems={analytics.patient_problems}
              />
            </>
          )}

          <section className="limitations-panel" aria-labelledby="maude-limitations-heading">
            <h3 id="maude-limitations-heading">How to interpret MAUDE data</h3>
            <ul>{analytics.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
            <p>This application is a research aid and does not replace medical-device vigilance review, clinical judgment, or regulatory assessment.</p>
          </section>
        </div>
      )}
    </section>
  );
}
