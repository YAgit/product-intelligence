# Pharmaceutical Product Search Web App Plan

## Purpose

This document is the implementation plan and completion record for the FDA product search web app described in [AGENTS.md](/Users/yousufahmed/Projects/fdasearch/AGENTS.md). It now tracks the shipped v1.1 drug workflow and the approved v2 device-search expansion.

## Current Product State

- The app runs locally with FastAPI and `uv`.
- The app is packaged for Docker and Hugging Face Spaces.
- FDA product data is fetched from the openFDA NDC directory endpoint.
- Ambiguous product-name searches show a shortlist of matches for explicit user selection.
- A single pharmaceutical product analyst chatbot is available after product selection.
- The chatbot uses Anthropic first through OpenRouter and falls back to OpenAI when needed.
- A clearly visible drug disclaimer is displayed near the top of the page and in the chatbot area.

## Current Scope

### Shipped In v1.1

- Search by product name, product NDC, or package NDC.
- Show FDA product details for the selected NDC product.
- When a product-name search yields multiple FDA matches, let the user choose the exact product before loading full details.
- Provide a chatbot focused on pharmaceutical product questions.
- Refuse non-pharmaceutical-product questions with a clear limitation response.

### Approved For v2

- Add a second top-level device search experience alongside the existing drug experience.
- Use simple tab navigation so users can switch between drug search and device search from either page.
- Keep the drug search flow intact while adding the device workflow.
- Accept a single smart search-box input for device lookup.
- Support these device input types in the smart box:
  - UDI barcode text
  - Device Identifier
  - Brand name
  - Model or catalog number
- Normalize device input and query the appropriate FDA or openFDA device endpoint.
- When a device search yields multiple matches, show a simple shortlist selector and require explicit selection before loading full details and chat.
- Show key FDA-backed device details for the selected device.
- Provide a single device analyst chatbot for the selected device.
- Refuse non-device or non-pharmaceutical questions in the device chatbot.
- Display a device-specific disclaimer in the device workflow.

## Assumptions To Use Unless Changed

- The app remains installable on Hugging Face Spaces through a Docker Space setup.
- The user experience should continue to feel like a classic web app rather than a notebook-style tool.
- openFDA remains the source for NDC product details.
- FDA or openFDA device endpoints will be used for the new device workflow, depending on which endpoint best matches each supported input type.
- OpenRouter remains the gateway for model access.
- Anthropic is the primary chatbot provider family, with OpenAI fallback when Anthropic is unavailable.
- The chatbot is grounded by the selected FDA product or device plus general pharma-product knowledge, without adding web search or crawling.

## Delivery Rules

- Keep the app simple. Avoid extra abstractions, features, or infrastructure unless they are required by the current scope.
- When issues appear, identify the root cause with evidence before changing code.
- Use current stable library versions and idiomatic patterns at implementation time.
- Keep documentation aligned with the shipped product behavior.

## Current Technical Direction

- Backend: Python FastAPI
- Frontend: server-rendered classic web UI served by FastAPI
- Packaging: `uv` for Python dependency management
- Deployment target: local run first, then Hugging Face Spaces via Docker
- API integration:
  - openFDA for NDC lookup
  - FDA or openFDA device data for device lookup
  - OpenRouter for chatbot model access
- Runtime secrets:
  - `OPENROUTER_API_KEY`
  - `OPENFDA_API_KEY`
- Operations:
  - Start and stop scripts for macOS, Linux, and Windows in `scripts/`

## Implementation Record

## Part 1: Planning

### Outcome

- The original plan was created for the initial FDA search MVP.
- The product later changed in v1.1 from four model-generated analysis cards to a single pharma chatbot with explicit match selection.

### Success Criteria Met

- The plan now reflects the actual shipped direction.

## Part 2: Scaffolding

### Outcome

- Created the FastAPI project structure, dependency management, templates, static assets, and startup scripts.
- Added a health route and environment loading.

### Success Criteria Met

- The app can be installed and started locally.

## Part 3: FDA Search Flow

### Outcome

- Implemented openFDA NDC search by product name and NDC.
- Added parsing, normalization, and error handling for FDA responses.
- Rendered FDA product details in the UI.

### Success Criteria Met

- Users can search and view FDA NDC product details without crashes on empty or invalid cases.

## Part 4: Initial AI Analysis

### Historical Note

- This phase originally implemented four provider-specific competitive-analysis cards through OpenRouter.
- That functionality has been retired in v1.1 and replaced by the chatbot flow below.

## Part 5: Frontend Integration And UX Polish

### Outcome

- Built the classic web app layout with search, detail, and AI interaction areas.
- Added clearer status messaging, result hierarchy, and mobile-friendly layout behavior.

### Success Criteria Met

- The app is understandable and usable on desktop and smaller screens.

## Part 6: Deployment Readiness

### Outcome

- Added Docker packaging and Hugging Face Spaces Docker metadata.
- Verified local tests, Docker build, and container startup.

### Success Criteria Met

- The app is ready for straightforward local use and Hugging Face Spaces deployment.

## Part 7: Version 1.1 Update

### Goals

- Replace the four-analysis-card experience with a single pharmaceutical product analyst chatbot.
- Improve ambiguous product-name handling by showing a shortlist of FDA matches for user selection.
- Remove outdated header copy tied to the original four-analysis UI.

### Checklist

- Remove the two retired header chips.
- Change FDA name search behavior so multiple matches are shown explicitly.
- Add a selected-product flow before loading detailed results when ambiguity exists.
- Replace the four-card analysis service with a single chatbot service.
- Use Anthropic as the primary model and OpenAI as the fallback.
- Make the chatbot refuse non-pharmaceutical-product questions.
- Update tests and deployment-facing documentation.

### Tests

- Automated tests for shortlist rendering, selected product loading, chatbot replies, fallback messaging, and invalid search behavior.
- Live openFDA check confirming ambiguous queries such as `Tylenol` return multiple matches.
- Live OpenRouter check confirming Anthropic-first chatbot responses.

### Success Criteria

- Ambiguous searches no longer auto-pick a product silently.
- The chatbot appears only in the current single-assistant form.
- Non-pharma questions are explicitly refused by the assistant prompt contract.
- Documentation matches the shipped v1.1 app behavior.

## Part 8: Version 2 Device Search Expansion

### Goals

- Expand the app from a drug-only workflow into a two-mode drug-and-device workflow.
- Preserve the current drug search and chatbot experience while adding a device search path.
- Keep the device experience simple by starting with one smart search box rather than a multi-field advanced form.

### Checklist

- Add tab navigation for Drug Search and Device Search.
- Keep the existing drug tab behavior unchanged except where shared layout updates are required.
- Add a device smart search form that accepts:
  - UDI barcode text
  - Device Identifier
  - Brand name
  - Model or catalog number
- Add device input normalization and endpoint routing.
- Add device-match handling that supports:
  - direct load for a single match
  - explicit shortlist selection for multiple matches
- Add device detail rendering.
- Add a device analyst chatbot with Anthropic-first and OpenAI-fallback behavior.
- Make the device chatbot refuse non-device or non-pharma questions.
- Add a device-specific disclaimer.
- Update tests and deployment-facing documentation.

### Tests

- Automated tests for tab navigation, device search validation, multiple-match selection, selected device rendering, device chatbot replies, refusal behavior, and disclaimer visibility.
- Endpoint-level checks confirming that the chosen FDA or openFDA device search path supports the four approved smart-search inputs.
- Regression tests confirming the drug workflow still behaves as in v1.1.

### Success Criteria

- Users can switch between drug and device search without confusion.
- The drug workflow continues to work as before.
- A user can search for a device from the smart search box using any of the four approved input types.
- Multiple device matches do not auto-select silently.
- The device chatbot is available only after a device is selected.
- Device disclaimers are clearly visible and specific to device usage.
- Documentation matches the shipped v2 behavior.

## Out Of Scope

- User accounts or login
- Saved search history
- Background job queues
- Database storage
- Web crawling, news scraping, or custom RAG pipelines
- Returning to the old four-analysis-card UI
- Advanced multi-field device search forms beyond the approved single smart search box
- Device inputs beyond UDI barcode text, Device Identifier, Brand name, and Model or catalog number for the first v2 release

## Done Definition For The Current App

- The app runs locally through the provided scripts.
- The app builds and starts in Docker.
- A user can search by drug name or NDC code.
- The app fetches and displays FDA product details from openFDA.
- Ambiguous name searches show multiple FDA matches and allow explicit selection.
- A pharmaceutical product analyst chatbot is available for the selected product.
- Anthropic is used first for chat, with OpenAI fallback when needed.
- The UI looks and behaves like a classic web app.
- The project is ready for a straightforward Hugging Face Spaces Docker deployment.

## Done Definition For v2

- The drug workflow still runs locally through the provided scripts and behaves as before.
- The app builds and starts in Docker with both drug and device workflows available.
- A user can switch between Drug Search and Device Search with clear tab navigation.
- A user can search for a device through one smart search box using any approved v2 device input type.
- The app fetches and displays FDA-backed device details through the selected device search path.
- Ambiguous device searches show multiple matches and require explicit selection.
- A device analyst chatbot is available for the selected device.
- Anthropic is used first for device chat, with OpenAI fallback when needed.
- Device-specific disclaimers are clearly visible.
- The project remains ready for straightforward Hugging Face Spaces Docker deployment.
