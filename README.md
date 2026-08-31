---
title: Pharmaceutical Product Search
emoji: "💊"
colorFrom: blue
colorTo: yellow
sdk: docker
app_port: 7860
header: default
fullWidth: true
short_description: Search FDA products and chat with a pharma analyst.
tags:
  - fastapi
  - docker
  - fda
  - healthcare
  - openrouter
---

# Pharmaceutical Product Search

Classic web app for FDA NDC lookup and a pharmaceutical product analyst chatbot.

## Local run

```bash
uv sync
./scripts/start-mac.sh
```

Linux:

```bash
uv sync
./scripts/start-linux.sh
```

Windows PowerShell:

```powershell
uv sync
./scripts/start-windows.ps1
```

Open `http://127.0.0.1:8000`.

## Environment

Required in `.env` for local use or Space secrets for deployment:

```bash
OPENFDA_API_KEY=...
OPENROUTER_API_KEY=...
```

## Hugging Face Spaces

This repo is prepared for a Docker Space. The app listens on port `7860` in the container and uses the same FastAPI app as local development.
