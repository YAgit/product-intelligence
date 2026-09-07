# Product Intelligence Platform

## Product Purpose

This project is evolving from a pharmaceutical drug and medical device search demo into a product intelligence application for life sciences.

The current application provides:
- Drug search by product name or NDC
- Medical device search by supported device identifiers
- FDA/openFDA data retrieval
- AI-generated product analysis
- Conversational AI for follow-up questions

The next MVP extends the application with **Adverse Event Intelligence for pharmaceutical drugs**, using FDA adverse-event data to help users explore post-market safety information.

The product should remain evidence-first. AI should help users understand, summarize, compare, and investigate authoritative source data. AI must not independently determine clinical causality or present unvalidated conclusions as established safety findings.

---

## Current Application Baseline

The current implemented application is the working baseline and must continue to function during the next phase of development.

Existing capabilities include:

### Drug Search
- Search by product name or NDC
- Normalize entered NDC values
- Query the appropriate openFDA NDC endpoint
- When a product-name search matches multiple FDA-listed products, show the possible matches and allow the user to select the correct product
- Retrieve and display key pharmaceutical product information
- Provide AI analysis of the retrieved product information

### Medical Device Search
Provide a separate device-search experience.

Supported device search inputs include:
- UDI barcode text
- Device Identifier
- Brand name
- Model or catalog number

The application should normalize the entered value and query the appropriate FDA/openFDA device endpoint.

### AI Chat
- Provide a conversational AI capability for pharmaceutical and medical-device product questions
- The assistant should act as a life-sciences product analyst
- Answers should use retrieved product information when available
- The assistant should not answer unrelated general-purpose questions
- AI responses should clearly distinguish retrieved facts from interpretation

Existing drug and device functionality must not regress while implementing the new MVP.

---

## Current MVP Objective: Adverse Event Intelligence

The primary product feature for this development phase is **Adverse Event Intelligence for pharmaceutical drugs**.

The purpose is to help users investigate FDA post-market adverse-event information for a selected drug.

This is an intelligence and investigation capability, not an automated clinical decision system.

The MVP should answer questions such as:
- How many adverse-event reports are associated with this product?
- How has reporting changed over time?
- What reactions are reported most frequently?
- What percentage of retrieved reports are classified as serious?
- What serious outcomes are represented?
- Are particular reaction categories increasing?
- What notable patterns are present in the retrieved data?
- How should a user interpret the observed data given the limitations of FAERS?

The MVP should expose the supporting evidence behind all summaries and analytics.

---

## MVP Functional Requirements

For a selected pharmaceutical product, add an **Adverse Events** section or tab.

The first version should include:

### 1. Reporting Overview

Show useful summary metrics such as:
- Total retrieved reports
- Serious reports
- Non-serious reports
- Percentage of reports classified as serious
- Death outcomes when present
- Hospitalization outcomes when present
- Life-threatening outcomes when present
- Disability outcomes when present
- Other serious outcomes where supported by the source data
- Reporting period represented in the retrieved dataset

Do not imply that raw report counts represent incidence.

### 2. Time Trends

Aggregate reports over time.

Preferred initial interval:
- Quarter

Allow the implementation to support alternative intervals later if useful.

Display:
- Total reports by period
- Serious reports by period

The frontend should visualize these trends clearly.

Trend calculations must be deterministic and implemented in the backend rather than delegated to an LLM.

### 3. Reaction Analysis

Extract reported reaction terms and show:
- Most frequently reported reactions
- Number of reports associated with each reaction
- Percentage of retrieved reports containing each reaction where meaningful
- Serious-report counts for the reaction where practical

Reaction terms should be based on the terminology provided in the FDA data.

Do not use an LLM to rename or normalize clinical terminology unless explicitly implemented as a separate, traceable presentation layer.

### 4. Serious Outcome Analysis

Provide structured analysis of serious outcomes represented in the retrieved reports.

Examples include:
- Death
- Hospitalization
- Life-threatening event
- Disability
- Congenital anomaly where available
- Other serious outcomes supported by FAERS

These values must come from source fields and deterministic backend calculations.

### 5. AI Safety Analysis

Provide an AI-generated summary of the retrieved adverse-event data.

The AI analysis should:
- Summarize the most important observable patterns
- Explain reporting trends
- Highlight notable serious-outcome patterns
- Identify reactions that may warrant user attention
- Explain important limitations of the source data
- Reference the retrieved evidence and calculated analytics
- Avoid claims of causality
- Avoid diagnosing patients
- Avoid stating that a confirmed safety signal exists unless supported by an authoritative source
- Avoid interpreting FAERS reporting frequency as incidence or prevalence

The LLM should explain evidence, not create the evidence.

---

## FDA Adverse Event Data

Use FDA FAERS data through an appropriate openFDA drug adverse-event endpoint.

Keep FDA access logic isolated behind a dedicated backend client/service.

Do not couple frontend components directly to openFDA response structures.

The backend should:
1. Build FDA queries
2. Retrieve FDA responses
3. Validate basic response structure
4. Normalize relevant fields
5. Produce application-domain objects
6. Perform deterministic analytics
7. Return stable application API responses to the frontend

This separation is important because FDA schemas, APIs, and application requirements may evolve independently.

---

## Product Matching for Adverse Events

Product matching is a significant concern and must be handled explicitly.

The application may need to search adverse-event reports using information such as:
- Brand name
- Generic name
- Active ingredient
- Manufacturer/product identifiers where supported

Do not assume NDC alone will produce complete FAERS coverage.

Reuse existing drug normalization and product-selection logic where appropriate.

Do not silently combine ambiguous products.

If multiple candidate products or names could materially affect the search result, make the matching strategy explicit in the backend and UI.

Keep matching logic modular so it can be improved later.

---

## Safety and Pharmacovigilance Guardrails

These rules are mandatory.

### FAERS Limitations

The application must not imply that:
- An adverse-event report proves the drug caused the event
- Report counts represent incidence
- Higher raw report volume automatically means higher product risk
- Absence of reports proves safety
- A statistical association proves causality

Where adverse-event analytics are shown, provide appropriate context explaining that spontaneous-reporting systems have limitations such as:
- Duplicate reporting
- Incomplete reports
- Variable reporting quality
- Reporting bias
- Lack of denominator/exposure data
- Lack of confirmed causality

### Terminology

Prefer:
- "Reported adverse events"
- "Reports associated with"
- "Observed reporting pattern"
- "Reporting trend"
- "Potential area for review"
- "May warrant investigation"

Avoid unsupported language such as:
- "The drug caused"
- "Confirmed signal"
- "Incidence increased"
- "Risk increased by X%" when the metric is actually report volume
- "Unsafe"

### Human Review

The application should be positioned as a research and investigation aid.

Do not describe the output as replacing pharmacovigilance review, medical judgment, regulatory assessment, or established safety-signal processes.

---

## Explicitly Out of Scope for This MVP

Do not implement the following unless specifically requested in a later task:

- Overall Product Safety Risk Score
- Cross-product enterprise risk scoring
- Automated regulatory conclusions
- Automated causality assessment
- Automated safety-signal confirmation
- ROR
- PRR
- Bayesian signal detection
- Machine-learning safety models
- Automated label-change detection
- Full FAERS case deduplication beyond what is straightforward and justified
- Portfolio watchlists
- Alerts and notifications
- User accounts
- SSO
- RBAC
- Customer-specific data
- Internal complaints
- CAPA data
- Deviations
- Manufacturing quality data
- Supplier-risk data
- Medical-device post-market adverse-event intelligence
- Enterprise dashboards
- Multi-tenant SaaS functionality

These are roadmap items, not permission to expand current scope.

---

## Future Product Direction

The architecture should make future expansion possible without building future features now.

Potential future capabilities include:

### Product Safety Intelligence
- ROR
- PRR
- Signal prioritization
- Label comparison
- Safety communications
- Recall correlation
- Risk scoring

### Medical Device Safety Intelligence
- MAUDE analysis
- Device adverse-event trends
- Device recalls
- Post-market surveillance

### Portfolio Monitoring
- Saved products
- Watchlists
- Material-change detection
- Alerts
- Portfolio risk dashboards

### Enterprise Product Risk 360
Potential future integration with internal enterprise data such as:
- Complaints
- CAPAs
- Deviations
- Manufacturing events
- Batch failures
- Supplier quality
- Stability data

Do not prematurely implement these roadmap capabilities.

---

## Target Application Architecture

The application is moving from a FastAPI-served classic web UI to a separated frontend/backend architecture.

### Frontend

Use:
- Next.js
- React
- TypeScript

The frontend owns:
- Page composition
- Navigation
- UI state
- User interaction
- Charts and visualization
- Presentation formatting

The frontend must not contain core FDA query logic, safety analytics, or LLM orchestration.

### Backend

Continue using:
- Python
- FastAPI
- `uv`

FastAPI owns:
- FDA/openFDA integrations
- DailyMed integrations
- Data normalization
- Product matching
- Adverse-event retrieval
- Safety analytics
- Domain logic
- AI orchestration
- Stable application APIs

### Architectural Rule

**Do not duplicate business logic in Next.js.**

If a capability involves:
- FDA data interpretation
- Product normalization
- Safety analytics
- Product matching
- LLM orchestration

implement it in FastAPI and expose it through an API.

---

## Backend API Design

Expose frontend-independent APIs.

Use versioned routes.

Example organization:

```text
/api/v1/drugs/search
/api/v1/drugs/{product_id}

/api/v1/devices/search
/api/v1/devices/{device_id}

/api/v1/drugs/{product_id}/adverse-events
/api/v1/drugs/{product_id}/adverse-events/summary
/api/v1/drugs/{product_id}/adverse-events/trends
/api/v1/drugs/{product_id}/adverse-events/reactions
/api/v1/drugs/{product_id}/adverse-events/seriousness

/api/v1/analysis/product
/api/v1/analysis/adverse-events
```

These are architectural examples, not mandatory route names.

Prefer coherent resource-oriented APIs over unnecessary endpoint proliferation.

Return stable application-domain responses rather than passing raw FDA JSON directly to the frontend.

---

## Backend Organization

Prefer clear separation of responsibilities.

A reasonable structure is:

```text
backend/
  app/
    api/
    clients/
    models/
    schemas/
    services/
    analytics/
    ai/
```

Use the existing project structure where it is already clean.

Do not reorganize the repository simply to match this example.

Expected responsibility boundaries:

### clients
External API access:
- openFDA
- DailyMed
- OpenRouter

### services
Application workflows:
- drug search
- device search
- adverse-event retrieval
- product matching

### analytics
Deterministic calculations:
- summary counts
- serious-event classification
- reaction aggregation
- time-series aggregation
- trend calculations

### ai
- Prompt construction
- Model calls
- Provider fallback
- Evidence packaging
- AI response parsing

### api
FastAPI routes and request/response handling.

Keep route handlers thin.

---

## Frontend Organization

Prefer reusable components.

A possible structure is:

```text
frontend/
  app/
  components/
  features/
  lib/
  types/
```

Do not force a repository restructure when the existing organization is already reasonable.

Potential drug page composition:

```text
DrugProductPage
  ProductHeader
  ProductOverview
  ProductAIAnalysis
  AdverseEventIntelligence
    ReportingOverview
    TrendChart
    SeriousEvents
    ReactionTable
    AIInterpretation
```

Prefer reusable feature components over one large page component.

---

## UI and Navigation

Provide a professional life-sciences product-intelligence experience.

The application should clearly distinguish:
- Drugs
- Devices

The current navigation concept should remain intuitive while introducing adverse-event intelligence.

For drugs, the product detail experience may include sections or tabs such as:
- Product Details
- Label
- AI Analysis
- Adverse Events

Do not add unnecessary navigation or dashboard features.

Adverse-event visualizations should emphasize readability and evidence rather than decorative complexity.

No emojis in the application UI unless explicitly requested.

---

## AI Architecture

Use OpenRouter for AI calls.

Environment:
- `OPENROUTER_API_KEY` is supplied through environment configuration
- Never hardcode credentials

Provider preference:
1. Anthropic
2. OpenAI fallback

Retain or improve the existing fallback approach without adding unnecessary abstraction.

### Evidence-First AI

All product-specific AI analysis should receive relevant structured evidence from backend services.

For adverse-event analysis, provide the model with calculated analytics rather than asking the model to calculate values from large raw datasets.

Preferred flow:

```text
FDA data
  ->
Normalization
  ->
Deterministic analytics
  ->
Structured evidence
  ->
LLM explanation
```

Avoid:

```text
Raw FDA data
  ->
LLM invents analysis and calculations
```

The AI layer is for synthesis and explanation, not authoritative statistical computation.

---

## Deployment Strategy

The application should no longer depend on Hugging Face Spaces.

Use a Vercel-first, AWS-ready deployment strategy while keeping provider-specific configuration outside the application package.

Phase 2 creates two runbooks and does not create cloud resources or change application code:

- `docs/DEPLOYMENT_VERCEL.md` for the Vercel demo architecture.
- `docs/DEPLOYMENT_AWS.md` for AWS Amplify Hosting, ECR, ECS Express Mode, and Fargate.

Actual deployment requires a separate explicit request. Do not use AWS App Runner for new deployment work in this project.

---

## Environment Configuration

Local development may continue using `.env`.

Production secrets must not be stored in source control.

Expected secret/configuration values include:
- `OPENROUTER_API_KEY`
- `OPENFDA_API_KEY`

Use environment variables for service configuration.

Never expose backend secrets to the Next.js browser bundle.

Only variables explicitly intended for public browser use may use Next.js public environment-variable conventions.

---

## Docker

The FastAPI backend must remain containerized.

Keep Docker configuration simple and production-compatible.

Use `uv` for Python dependency management.

Do not introduce an additional Python package manager.

The frontend does not need to share the backend container.

Frontend and backend must be independently deployable.

---

## Scripts

Maintain useful developer scripts under `scripts/`.

Support practical local startup for:
- macOS
- Windows
- Linux

Do not create redundant scripts when one cross-platform approach is sufficient.

---

## Logging

Use application logging that works both locally and in CloudWatch.

Log:
- External API failures
- Unexpected response conditions
- AI provider failures
- Provider fallback usage
- Application errors

Do not log:
- API keys
- Secrets
- Sensitive authorization values

Avoid excessive logging of raw external API payloads.

---

## Error Handling

Keep error handling simple and useful.

Follow this rule from the current project:

**When hitting issues, identify root cause before trying a fix. Do not guess. Prove with evidence, then fix the root cause.**

Do not add speculative defensive code for situations that have not occurred and are not reasonably expected.

External API errors should be translated into useful application-level errors.

The frontend should receive enough information to provide a helpful user message without exposing internal stack traces.

---

## Testing Requirements

Add tests for business-critical deterministic behavior.

Priority test areas:

### Drug/Product Matching
- NDC normalization
- Product-name matching
- Ambiguous matches

### Device Search
Preserve existing tests and behavior.

### Adverse Event Data
- Parsing representative FAERS responses
- Empty result handling
- Serious/non-serious classification
- Serious-outcome extraction
- Reaction aggregation
- Quarterly aggregation
- Date handling
- Percentage calculations

### AI
Do not make routine automated tests depend on live LLM calls.

Mock AI provider responses where practical.

Test:
- Prompt/evidence construction
- Provider fallback behavior
- Response parsing

### APIs
Test important FastAPI routes using representative mocked external responses.

Do not attempt exhaustive testing of openFDA itself.

---

## Coding Standards

1. Use current stable library versions and idiomatic approaches.
2. Keep the implementation simple.
3. NEVER over-engineer.
4. ALWAYS prefer the simplest design that cleanly supports the current requirement.
5. Do not add speculative abstractions for hypothetical future features.
6. No extra features outside the defined task.
7. Keep README documentation concise.
8. No emojis in code, documentation, README, or application copy unless explicitly requested.
9. Prefer small, understandable modules over large frameworks or complex design patterns.
10. Reuse working code before replacing it.
11. Preserve backward-compatible behavior unless a requested change explicitly replaces it.
12. Avoid broad refactors while implementing a feature unless the existing design blocks the feature.
13. Identify root cause before fixing bugs. Do not guess.
14. Use evidence to validate a suspected cause before changing code.
15. Do not hardcode secrets.
16. Keep frontend and backend responsibilities clearly separated.

---

## Agent Development Workflow

Codex or any coding agent working in this repository must follow this process.

### Before Making Changes

1. Read this `AGENTS.md`.
2. Read `docs/PLAN.md`.
3. Inspect the existing repository structure.
4. Understand the current implementation before proposing architectural changes.
5. Identify existing utilities, services, clients, and components that can be reused.
6. Run relevant existing tests where practical.
7. Confirm the current behavior of the area being modified.

Do not assume the repository matches examples in this document.

The repository is the source of truth for existing implementation.

### During Implementation

Work incrementally.

Prefer:
1. Small coherent change
2. Validate
3. Test
4. Continue

Do not attempt a large rewrite when an incremental migration is possible.

When adding a new capability:
- Implement backend/domain behavior first where appropriate
- Add or update tests
- Expose the API
- Implement the frontend against the API
- Verify existing features still function

### After Implementation

Before declaring work complete:
1. Run relevant automated tests
2. Run lint/type checks where configured
3. Verify the changed user flow
4. Check for regressions in drug search
5. Check for regressions in device search
6. Confirm no secrets were added to source control
7. Update planning documentation when required

---

## Implementation Sequence

The preferred development sequence for this version is:

### Phase 1 - Architecture Foundation

Objective:
Separate frontend presentation from backend domain logic while preserving current behavior.

Tasks:
- Introduce the Next.js frontend
- Expose existing FastAPI functionality through application APIs
- Recreate existing drug-search experience
- Recreate existing device-search experience
- Preserve AI analysis/chat behavior
- Remove frontend dependence on FastAPI-rendered pages only after replacement functionality is verified

Do not rewrite working backend services unnecessarily.

### Phase 2 - Deployment Instructions

Objective:
Create detailed deployment guidance for Vercel and AWS while keeping application code provider-neutral.

Tasks:
- Create `docs/DEPLOYMENT_VERCEL.md` for the Next.js frontend and FastAPI backend.
- Create `docs/DEPLOYMENT_AWS.md` for Amplify Hosting, ECR, ECS Express Mode, and Fargate.
- Document prerequisites, environment variables, secrets, deployment order, verification, observability, rollback, and teardown.
- Keep provider-specific configuration outside the application package.
- Do not create cloud resources, deploy the application, or add provider-specific code/configuration during this phase.

### Phase 3 - Adverse Event Intelligence

Objective:
Add deterministic FAERS exploration for drugs.

Tasks:
- Implement FAERS/openFDA client functionality
- Implement product matching strategy
- Normalize adverse-event data
- Build reporting overview
- Build serious-outcome analysis
- Build reaction aggregation
- Build quarterly time trends
- Expose stable FastAPI endpoints
- Add Next.js adverse-event UI

### Phase 4 - AI Safety Analysis

Objective:
Provide evidence-grounded AI interpretation.

Tasks:
- Build structured adverse-event evidence payload
- Add safety-focused AI prompt
- Summarize observed trends and important patterns
- Explain data limitations
- Provide evidence/source references where supported
- Preserve provider fallback behavior

### Phase 5 - UX Refinement

Objective:
Make the MVP understandable and demo-ready.

Tasks:
- Improve adverse-event page composition
- Refine charts
- Improve evidence drilldown
- Clearly surface FAERS limitations
- Verify responsive behavior
- Remove unnecessary visual complexity

---

## Definition of Done for the Adverse Event Intelligence MVP

The MVP is complete when:

1. A user can search for and select a pharmaceutical drug using the existing drug-search experience.

2. The user can open an Adverse Events view for that product.

3. The backend retrieves relevant FAERS/openFDA adverse-event data using an explicit product-matching strategy.

4. The application displays:
   - Total retrieved reports
   - Serious-report counts
   - Serious-outcome details
   - Top reported reactions
   - Time-based reporting trends

5. Calculations shown in the UI are deterministic and implemented in backend code.

6. The user can see an AI-generated analysis explaining important observed patterns.

7. The AI analysis includes appropriate FAERS limitations and does not imply causality or incidence.

8. Existing drug-search functionality continues to work.

9. Existing medical-device search functionality continues to work.

10. Existing product AI analysis/chat functionality continues to work or has an equivalent replacement in the new frontend.

11. Next.js and FastAPI are independently deployable.

12. Detailed Vercel and AWS deployment runbooks exist and preserve application-code neutrality.

13. Production secrets are not stored in the repository.

14. Relevant automated tests pass.

---

## Limitations

For this MVP:
- No user login is required
- No customer-specific data is required
- No portfolio management is required
- No persistent user preferences are required
- No formal product safety score is required

---

## Working Documentation

All planning and execution documentation belongs in the `docs/` directory.

Before beginning implementation, review:

`docs/PLAN.md`

Update `docs/PLAN.md` when implementation sequencing, major architecture decisions, or MVP scope materially changes.

Keep planning documents aligned with this `AGENTS.md`.

---

## Guiding Principle

Build the smallest credible Product Safety Intelligence MVP that demonstrates real user value while creating a clean foundation for future expansion.

Preserve working functionality.

Keep the architecture understandable.

Use authoritative data for evidence.

Use deterministic code for analytics.

Use AI for explanation and investigation.
