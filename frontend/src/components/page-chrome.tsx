import Link from "next/link";
import type { ReactNode } from "react";

type Mode = "drug" | "device";

export function ModeTabs({ active }: { active: Mode }) {
  return (
    <nav className="mode-tabs" aria-label="Search modes">
      <Link className={`mode-tab ${active === "drug" ? "is-active" : ""}`} href="/">
        Drug Search
      </Link>
      <Link
        className={`mode-tab ${active === "device" ? "is-active" : ""}`}
        href="/devices"
      >
        Device Search
      </Link>
    </nav>
  );
}

type HeroProps = {
  eyebrow: string;
  title: string;
  description: string;
  source: string;
  analyst: string;
  query: string;
  status: string;
};

export function PageHero({
  eyebrow,
  title,
  description,
  source,
  analyst,
  query,
  status,
}: HeroProps) {
  return (
    <header className="hero">
      <p className="eyebrow">{eyebrow}</p>
      <div className="hero-grid">
        <div>
          <h1>{title}</h1>
          <p className="hero-copy">{description}</p>
        </div>
        <aside className="hero-summary">
          <h2>Session Snapshot</h2>
          <dl className="summary-grid">
            <div>
              <dt>FDA source</dt>
              <dd>{source}</dd>
            </div>
            <div>
              <dt>AI mode</dt>
              <dd>{analyst}</dd>
            </div>
            <div>
              <dt>Current query</dt>
              <dd>{query || "None yet"}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{status}</dd>
            </div>
          </dl>
        </aside>
      </div>
    </header>
  );
}

export function Disclaimer({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="panel disclaimer-panel" aria-labelledby="disclaimer-title">
      <div className="panel-heading">
        <h2 id="disclaimer-title">{title}</h2>
        <span className="badge">Read before use</span>
      </div>
      {children}
    </section>
  );
}

export function PanelHeading({
  title,
  badge,
}: {
  title: string;
  badge?: string;
}) {
  return (
    <div className="panel-heading">
      <h2>{title}</h2>
      {badge && <span className="badge">{badge}</span>}
    </div>
  );
}

export function Notice({
  tone,
  label,
  children,
}: {
  tone: "error" | "success" | "info";
  label: string;
  children: ReactNode;
}) {
  return (
    <div className={`message-banner message-${tone}`} role={tone === "error" ? "alert" : "status"}>
      <strong>{label}</strong>
      <span>{children}</span>
    </div>
  );
}

export function BusyOverlay({ message }: { message: string | null }) {
  if (!message) return null;

  return (
    <div className="loading-shell" role="status" aria-live="polite">
      <div className="loading-card">
        <span className="loading-spinner" aria-hidden="true" />
        <p className="loading-title">Working on your request</p>
        <p className="loading-copy">{message}</p>
      </div>
    </div>
  );
}
