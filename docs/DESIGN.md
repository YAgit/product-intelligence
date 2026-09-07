# Application Design

## Overview

The Product Intelligence Platform uses an independent Next.js frontend and FastAPI backend. The Next.js drug and device experiences have feature parity with the original interface; the FastAPI-rendered pages remain temporarily available as a fallback. Business logic, FDA access, and AI orchestration stay in the backend.

## Major Components

```mermaid
flowchart LR
    User[Web browser]

    subgraph Frontend[Next.js frontend]
        Pages[Pages and navigation]
        Features[Drug and device features]
        Charts[Future safety visualizations]
        Client[Typed API client]

        Pages --> Features
        Features --> Client
        Charts --> Client
    end

    subgraph Backend[FastAPI container]
        API[Versioned application APIs]
        Services[Product workflows and matching]
        FDAClient[FDA clients and normalization]
        AI[AI evidence and orchestration]

        API --> Services
        Services --> FDAClient
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
