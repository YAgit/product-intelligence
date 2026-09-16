# Application Design

## Overview

The Product Intelligence Platform uses an independent Next.js frontend and FastAPI backend. The Next.js drug and device experiences have feature parity with the original interface, and the drug experience includes deterministic FAERS adverse-event analytics. The FastAPI-rendered pages remain temporarily available as a fallback. Business logic, FDA access, safety analytics, and AI orchestration stay in the backend.

## Major Components

```mermaid
flowchart LR
    User[Web browser]

    subgraph Frontend[Next.js frontend]
        Pages[Pages and navigation]
        Features[Drug and device features]
        Charts[Adverse-event evidence and trends]
        Client[Typed API client]

        Pages --> Features
        Features --> Client
        Charts --> Client
    end

    subgraph Backend[FastAPI container]
        API[Versioned application APIs]
        Services[Product and adverse-event workflows]
        FDAClient[FDA clients and normalization]
        Analytics[Deterministic safety analytics]
        AI[AI evidence and orchestration]

        API --> Services
        Services --> FDAClient
        Services --> Analytics
        Services --> AI
    end

    subgraph External[External services]
        FDA[openFDA]
        Router[OpenRouter]
        Anthropic[Anthropic primary]
        OpenAI[OpenAI fallback]

        Router --> Anthropic
        Router -. fallback .-> OpenAI
    end

    User --> Frontend
    Client -->|JSON over /api/v1| API
    FDAClient --> FDA
    AI --> Router
```

No hosting provider is integrated at this stage. Provider-neutral deployment procedures are documented separately in `docs/DEPLOYMENT_VERCEL.md` and `docs/DEPLOYMENT_AWS.md`.
- Only FastAPI receives FDA and OpenRouter credentials.
- The adverse-event API returns application-domain analytics and matching metadata rather than raw FAERS payloads.
- AI does not participate in adverse-event calculations; evidence-grounded AI safety interpretation belongs to Phase 4.
