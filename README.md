# Product Intelligence Platform

FDA-backed drug and medical-device search with AI analysis and chat, plus deterministic FAERS adverse-event intelligence for selected drugs. The primary frontend is a responsive Next.js application backed by versioned FastAPI APIs.

## Local Development

Create `.env` from `.env.example`, then start FastAPI:

```bash
uv sync
./scripts/start-mac.sh
```

Use `start-linux.sh` on Linux or `start-windows.ps1` in Windows PowerShell. FastAPI runs at `http://localhost:8000`; the existing server-rendered interface remains available there during migration.

In another terminal, start Next.js:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

The Next.js frontend runs at `http://localhost:3000` and uses the FastAPI endpoints under `/api/v1`. Drug search and adverse-event intelligence are available at `/`; device search is available at `/devices`.

## Configuration

- `OPENFDA_API_KEY`: optional openFDA API key.
- `OPENROUTER_API_KEY`: required for AI summaries and chat.
- `FRONTEND_ORIGIN`: browser origin allowed by FastAPI; defaults to `http://localhost:3000`.
- `NEXT_PUBLIC_API_BASE_URL`: FastAPI origin used by Next.js; defaults to `http://localhost:8000`.

The application is currently configured for local development only. Provider-neutral deployment procedures are documented in `docs/DEPLOYMENT_VERCEL.md` and `docs/DEPLOYMENT_AWS.md`; no cloud resources or provider-specific application configuration are integrated.
