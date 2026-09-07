"use client";

import type { FormEvent } from "react";

import type { AnalysisResponse, ChatMessage } from "@/types/api";
import { Notice, PanelHeading } from "@/components/page-chrome";

type ChatPanelProps = {
  title: string;
  summaryLabel: string;
  summary: AnalysisResponse | null;
  selectedName: string | null;
  history: ChatMessage[];
  message: string;
  setMessage: (message: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  busy: boolean;
  notice: string | null;
  placeholder: string;
  emptyMessage: string;
  disclaimer: string;
};

export function ChatPanel({
  title,
  summaryLabel,
  summary,
  selectedName,
  history,
  message,
  setMessage,
  onSubmit,
  busy,
  notice,
  placeholder,
  emptyMessage,
  disclaimer,
}: ChatPanelProps) {
  return (
    <section className="panel chat-panel" id="chat-panel">
      <PanelHeading title={title} badge={selectedName ? "Ready" : "Select a result first"} />

      {summary && (
        <div className="summary-strip">
          <div>
            <p className="summary-label">{summaryLabel}</p>
            <p>{summary.content}</p>
          </div>
          {summary.model_id && <span className="model-label">{summary.model_id}</span>}
        </div>
      )}

      <div className="chat-disclaimer" role="note">
        <strong>Reminder:</strong>
        <span>{disclaimer}</span>
      </div>

      {notice && (
        <Notice tone="info" label="Chat update:">
          {notice}
        </Notice>
      )}

      <div className="chat-shell">
        <div className="chat-history" aria-live="polite">
          {history.length > 0 ? (
            history.map((item, index) => (
              <article className={`chat-bubble chat-bubble-${item.role}`} key={`${item.role}-${index}`}>
                <h3>{item.role === "user" ? "You" : "Analyst"}</h3>
                <p>{item.content}</p>
              </article>
            ))
          ) : (
            <article className="chat-bubble chat-bubble-assistant">
              <h3>Analyst</h3>
              <p>{selectedName ? `Ask about ${selectedName}.` : emptyMessage}</p>
            </article>
          )}
        </div>

        <form className="chat-form" onSubmit={onSubmit}>
          <label htmlFor="chat-message">Ask the analyst</label>
          <textarea
            id="chat-message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder={placeholder}
            disabled={!selectedName || busy}
            rows={3}
          />
          <button type="submit" disabled={!selectedName || busy || !message.trim()}>
            {busy ? "Analyst is responding…" : "Send question"}
          </button>
        </form>
      </div>
    </section>
  );
}
