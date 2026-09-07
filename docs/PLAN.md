# Product Intelligence Platform Plan

## Purpose

This document is the implementation plan and completion record for the Product Intelligence Platform described in [AGENTS.md](/Users/yousufahmed/Projects/fdasearch/AGENTS.md).

The current application supports FDA-backed drug and medical-device search with AI analysis and chat. The next MVP will first separate the frontend and backend, then add Adverse Event Intelligence for selected drugs.

The platform is an evidence-first research aid. It must not present adverse-event reports as proof of causality, report counts as incidence, or AI interpretation as a confirmed safety finding.

## Current Baseline

The working FastAPI application must remain available until its replacement has verified feature parity.

### Existing Features

- Drug search by brand name, generic name, product NDC, or package NDC.
- Drug input normalization, ambiguous-match selection, FDA details, AI overview, and chat.
- Device search by UDI barcode text, Device Identifier, brand name, or model/catalog number.
- Device input normalization, ambiguous-match selection, FDA details, AI overview, and chat.
- Drug- and device-specific disclaimers and chatbot topic restrictions.
- Anthropic-primary and OpenAI-fallback AI calls through OpenRouter.

### Current Technology

- Python and FastAPI managed with `uv`.
- Server-rendered Jinja templates and shared CSS.
- openFDA NDC and Device UDI integrations.
- Docker packaging and local startup scripts.

## Confirmed MVP Decisions

- Complete the Next.js migration with full drug, device, analysis, and chat parity before adverse-event development.
- Preserve the server-rendered interface until replacement functionality is verified.
- Let users select the FAERS reporting date range.
- Use the selected drug's brand name as the initial FAERS matching criterion.
- Display the exact matching field, value, date range, and retrieved-report count.
- Do not silently combine alternative product identities.
- Initially expose calculated tables and matching criteria, not individual FAERS case details.
- Document both deployment targets before adverse-event development: Vercel for demos and AWS for production or enterprise use.
- Keep provider-specific deployment configuration outside the application package so the code remains provider-neutral.
- Do not create cloud resources or deploy the application until deployment is explicitly requested.

The initial default FAERS date range remains an implementation-time decision. It does not block the architecture migration.

## Target Architecture

### Frontend

Use Next.js, React, and TypeScript for page composition, navigation, UI state, charts, presentation, and calls to versioned FastAPI endpoints.

The frontend must not implement FDA query construction, product matching, safety calculations, or LLM orchestration.

### Backend

Continue using Python, FastAPI, and `uv` for:

- FDA integrations and data normalization.
- Drug and device matching.
- FAERS query construction and retrieval.
- Deterministic adverse-event analytics.
- AI evidence construction, orchestration, and provider fallback.
- Stable versioned APIs.

Keep route handlers thin and reuse working code. Do not reorganize the repository solely to match an example structure.

### API Direction

Expose frontend-independent routes under `/api/v1`. Prefer a small, coherent API surface covering:

- Drug search, details, AI summary, and chat.
- Device search, details, AI summary, and chat.
- One aggregate adverse-event analytics endpoint accepting a selected drug and date range.
- One adverse-event AI-analysis endpoint operating on calculated evidence.

Return stable application-domain responses, not raw openFDA JSON.

## Adverse Event Intelligence Scope

### Matching Contract

1. Start from an explicitly selected drug.
2. Query FAERS using that product's brand name.
3. Apply the user-selected reporting date range.
4. Return the matching field and exact value with the analytics.
5. Do not broaden the query or merge ambiguous identities silently.

Keep matching logic isolated so additional deliberate strategies can be added later.

### Deterministic Analytics

Calculate in FastAPI:

- Total retrieved reports.
- Serious and non-serious counts and serious percentage.
- Death, hospitalization, life-threatening, disability, congenital-anomaly, and other supported serious outcomes.
- Reporting period represented in the results.
- Total and serious reports by calendar quarter.
- Reaction frequency, percentage of retrieved reports, and serious-report count where practical.

Use FDA reaction terminology. Do not ask an LLM to calculate values or rename clinical terms.

### Evidence Presentation

The interface will present:

- Matching criteria and selected date range.
- Reporting overview and serious-outcome tables.
- Reaction tables.
- Quarterly trend data and visualization.
- FAERS limitations.
- AI interpretation grounded in the displayed calculations.

Individual FAERS case-detail views are excluded from this MVP.

### AI Safety Analysis

The backend will send normalized, calculated evidence to the LLM. The response must summarize observable patterns, explain limitations, distinguish facts from interpretation, and avoid causal, diagnostic, incidence, prevalence, or confirmed-signal claims.

Use Anthropic first through OpenRouter and OpenAI as fallback.

## Implementation Sequence

### Phase 1: Architecture Foundation

Objective: introduce the separated architecture, reproduce the current user experience, and preserve the working UI until parity is verified.

Status: Complete.

- Inventory and verify existing drug, device, summary, and chat behavior.
- Define application-domain API schemas.
- Add versioned FastAPI APIs for existing features.
- Reuse current normalization, FDA clients, and AI behavior.
- Introduce the Next.js, React, and TypeScript frontend.
- Configure local frontend-to-backend communication without exposing secrets.
- Recreate drug and device search, selection, details, AI summaries, and chat.
- Preserve disclaimers, topic restrictions, and clear drug/device navigation.
- Verify responsive behavior, including mobile search inputs.

Outcome:

- Added domain response schemas and versioned drug, device, summary, chat, and health APIs.
- Added local CORS configuration through `FRONTEND_ORIGIN`.
- Added a Next.js 16, React 19, and TypeScript frontend foundation with a typed API client.
- Added complete Next.js drug and device search experiences using the versioned FastAPI APIs.
- Preserved automatic single-match loading and explicit selection for ambiguous results.
- Recreated FDA detail views, AI summaries, analyst chat history, provider-fallback notices, and safety disclaimers.
- Added frontend interaction tests and responsive layouts.
- Preserved all existing FastAPI-rendered routes as a controlled fallback.
- Completed backend tests, frontend tests, lint, type checking, and a production build.

Exit criteria:

- Existing backend tests pass.
- Versioned APIs cover the current user experience.
- Next.js runs locally and communicates with FastAPI.
- Drug and device flows have verified parity.
- AI primary/fallback behavior remains intact.

### Phase 2: Deployment Instructions

Objective: document executable Vercel and AWS deployment paths without adding provider-specific configuration to the application package or creating cloud resources.

Status: Complete.

- Create a Vercel runbook for the Next.js frontend and FastAPI backend.
- Create an AWS runbook using Amplify Hosting for Next.js and ECR plus ECS Express Mode/Fargate for FastAPI.
- Document prerequisites, environment variables, secrets, deployment order, verification, logging, rollback, and teardown.
- Keep provider-specific settings in cloud consoles, CI/CD, or a separate deployment workspace.
- Do not deploy infrastructure or change application code in this phase.

Outcome:

- Added `docs/DEPLOYMENT_VERCEL.md` for the demo architecture.
- Added `docs/DEPLOYMENT_AWS.md` for the production and enterprise architecture.
- Kept deployment execution outside the application package and deferred all cloud resource creation until explicitly requested.

Exit criteria:

- Both runbooks describe the complete deployment lifecycle and required configuration.
- The Vercel instructions retain the FastAPI responsibility boundary.
- The AWS instructions use the same Dockerized backend with ECR and ECS Express Mode/Fargate.
- No provider-specific application code or infrastructure resources are introduced.

### Phase 3: Adverse Event Intelligence

Objective: retrieve, calculate, and present deterministic adverse-event evidence for a selected drug.

Status: Not started.

- Add a dedicated openFDA drug adverse-event client.
- Implement explicit brand-name and user-selected date-range queries.
- Normalize representative FAERS responses into domain objects.
- Implement seriousness, outcome, reaction, percentage, and quarterly calculations.
- Return analytics and matching metadata through a versioned API.
- Handle empty results and external failures with useful application errors.
- Add the Next.js Adverse Events section with date selection, reporting overview, serious outcomes, reaction tables, quarterly trends, matching metadata, and FAERS limitations.

Exit criteria:

- Calculations are deterministic and tested.
- Responses identify exactly how and when data was matched.
- No LLM participates in numeric calculations.
- Users can inspect the calculated evidence and FAERS limitations.
- Existing drug and device workflows do not regress.

### Phase 4: AI Safety Analysis

Objective: provide evidence-grounded AI interpretation of the deterministic adverse-event analytics.

Status: Not started.

- Add evidence packaging and guarded adverse-event AI prompts.
- Summarize observable trends, serious outcomes, and reactions that may warrant review.
- Explain source limitations and distinguish retrieved facts from interpretation.
- Preserve Anthropic-first and OpenAI-fallback behavior.

Exit criteria:

- Users can inspect the calculated evidence used by the AI summary.
- AI output follows the pharmacovigilance guardrails.
- Existing drug and device workflows do not regress.

### Phase 5: UX Refinement

Objective: make the complete adverse-event MVP understandable, responsive, and demo-ready.

Status: Not started.

- Improve adverse-event page composition, charts, evidence drilldown, and limitations copy.
- Run backend and frontend tests, linting, and type checks.
- Verify drug, device, adverse-event, and chat flows on desktop and mobile.
- Verify loading, empty, ambiguous, and external-service error states.
- Confirm that no secrets are logged or committed.
- Update README and design documentation for the shipped architecture.
- Verify local runtime instructions and continued provider neutrality.

Exit criteria:

- The complete MVP satisfies the definition of done in `AGENTS.md`.
- Evidence remains readable and traceable on desktop and mobile.
- Relevant automated and manual checks pass.
- No secrets or provider-specific application dependencies are introduced.

## Testing Priorities

### Existing Behavior

- Drug and device normalization, matching, selection, details, AI, and chat.
- Provider fallback and chatbot topic restrictions.

### APIs and AI

- Stable schemas, validation, and application-level errors.
- Mocked FDA and AI-provider responses; routine tests must not require live services.
- AI evidence construction, response parsing, and fallback behavior.

### Adverse Events

- Brand-name query construction and escaping.
- User-selected date-range validation.
- FAERS parsing and empty results.
- Seriousness and serious-outcome extraction.
- Reaction de-duplication within a report and aggregation across reports.
- Quarterly aggregation, date handling, and percentages.
- Matching metadata returned with analytics.

### Frontend

- Parity-critical drug and device interactions.
- Date-range selection and validation.
- Analytics tables, trends, loading, empty, and error states.
- Responsive layouts and absence of backend secrets in browser configuration.

## Local Operation and Deployment Execution

- Use `docs/DEPLOYMENT_VERCEL.md` for a demo deployment.
- Use `docs/DEPLOYMENT_AWS.md` for an AWS production or enterprise deployment.
- Do not create cloud resources or execute either runbook until explicitly requested.
- Treat hosting as infrastructure, not an application dependency.
- Keep application code provider-neutral.
- Use environment variables for secrets and service configuration.
- Maintain useful local scripts for macOS, Windows, and Linux.

## Out of Scope

- Safety risk scores, ROR, PRR, Bayesian detection, or machine-learning safety models.
- Automated causality, confirmed-signal, regulatory, or label-change conclusions.
- Full FAERS case deduplication beyond straightforward justified handling.
- Individual FAERS case-detail presentation in this MVP.
- Medical-device post-market adverse-event analysis.
- Product comparisons, portfolios, watchlists, alerts, or enterprise dashboards.
- Accounts, SSO, RBAC, multi-tenancy, or customer-specific data.
- Complaints, CAPAs, deviations, manufacturing, supplier, or other internal data.
- Additional AWS infrastructure without a concrete requirement.

## Historical Implementation Record

### Version 1

- Created the FastAPI application, templates, assets, Docker packaging, and local scripts.
- Added openFDA NDC search, normalization, product details, and AI analysis.

### Version 1.1

- Added explicit ambiguous-product selection.
- Replaced multi-card analysis with a product chatbot.
- Added Anthropic-primary and OpenAI-fallback behavior.

### Version 2

- Added separate drug and device navigation.
- Added Device UDI search, normalization, selection, and details.
- Added device AI analysis, chat, and safety disclaimers.

Historical functionality remains subject to regression verification during migration.

## Definition of Done

- Next.js and FastAPI run as separate local applications.
- Existing drug and device experiences retain verified parity.
- Detailed Vercel and AWS deployment runbooks exist without embedding a hosting provider in application code.
- Users can select an adverse-event reporting range for a selected drug.
- The initial FAERS query uses and displays the selected product's brand name.
- The interface displays deterministic reporting, outcome, reaction, and quarterly analytics.
- Matching criteria and FAERS limitations are visible.
- AI analysis uses calculated evidence and follows all safety guardrails.
- Individual FAERS report details and other out-of-scope features are absent.
- Relevant tests and checks pass, and no secrets are committed or exposed.
