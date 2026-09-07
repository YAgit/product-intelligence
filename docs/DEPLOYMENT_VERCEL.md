# Vercel Deployment Runbook

## Purpose

This runbook describes how to deploy the Product Intelligence Platform to Vercel for demos and product validation. It is an operational document, not application implementation. Do not add Vercel-specific business logic, API routes, adapters, or committed deployment output to the application package.

The deployed system remains two independently deployable applications:

- Next.js frontend from `frontend/`.
- FastAPI backend using the repository's Python application and Docker dependency contract.

The browser communicates directly with the FastAPI HTTPS origin. FDA access, normalization, matching, analytics, and AI orchestration remain in FastAPI.

## Provider-Neutrality Rules

- Keep `NEXT_PUBLIC_API_BASE_URL` as the frontend's only backend-location setting.
- Keep `FRONTEND_ORIGIN`, `OPENFDA_API_KEY`, and `OPENROUTER_API_KEY` in the backend environment.
- Do not expose FDA or OpenRouter credentials through `NEXT_PUBLIC_*` variables.
- Do not commit `vercel.json`, `.vercel/`, `Dockerfile.vercel`, or generated Vercel output solely for deployment.
- If Vercel-specific packaging is needed, create it in a temporary deployment workspace or an independently managed deployment pipeline.
- Treat Vercel Functions and container functions as stateless. Do not rely on a writable local filesystem or in-memory state surviving requests.

## Target Architecture

```text
Browser
  -> Vercel project: Next.js frontend
  -> HTTPS
  -> Vercel project: FastAPI container function
       -> openFDA
       -> OpenRouter
```

Use two Vercel projects so frontend and backend deployments, environment variables, logs, and rollbacks remain independent.

## Prerequisites

- A Vercel account and team with permission to create projects and environment variables.
- Access to the source repository or an approved deployment artifact.
- Vercel CLI for the operator-run backend deployment.
- Docker available locally if validating the container before deployment.
- `OPENROUTER_API_KEY`; `OPENFDA_API_KEY` is optional but recommended for FDA rate limits.
- A decided frontend production origin. A custom domain avoids the initial two-deployment configuration loop, but it is not required.

Before deployment, verify the application locally:

```bash
.venv/bin/pytest
cd frontend
npm ci
npm test
npm run lint
npm run typecheck
npm run build
```

Also build and test the unchanged backend image:

```bash
docker build -t fdasearch-backend:verify .
docker run --rm -p 8000:8000 \
  -e OPENFDA_API_KEY \
  -e OPENROUTER_API_KEY \
  -e FRONTEND_ORIGIN=http://localhost:3000 \
  fdasearch-backend:verify
```

In another terminal, confirm `http://localhost:8000/api/v1/health` returns `{"status":"ok"}`. Never place literal secrets in shell history; load them from the operator's approved secret mechanism.

## 1. Deploy the FastAPI Backend

Vercel supports FastAPI through its Python runtime and supports OCI-compatible images through container functions. Use the container-function route for this project so deployment exercises the same Dockerized backend contract intended for AWS.

Vercel detects a root-level `Dockerfile.vercel`. To keep that provider-specific filename out of the application package, prepare an external staging directory:

```bash
DEPLOY_DIR="$(mktemp -d)"
cp pyproject.toml uv.lock README.md "$DEPLOY_DIR/"
cp -R app "$DEPLOY_DIR/app"
```

In that temporary directory, create `Dockerfile.vercel` with the following deployment-only definition:

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY app ./app

RUN pip install --no-cache-dir uv
RUN uv sync --frozen --no-dev

CMD ["/bin/sh", "-c", "exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

This wrapper changes packaging only: it imports the same `app.main:app` and honors the runtime-assigned port. It must remain outside the application repository.

From the deployment workspace:

1. Run `vercel login` if the CLI is not authenticated.
2. Run `vercel --cwd "$DEPLOY_DIR"` to create a preview deployment and backend project.
3. Give the project a backend-specific name such as `fdasearch-api`.
4. In Vercel project settings, add these backend variables separately for Preview and Production as required:
   - `OPENROUTER_API_KEY`: secret.
   - `OPENFDA_API_KEY`: secret or omit when intentionally unused.
   - `FRONTEND_ORIGIN`: exact frontend origin, without a trailing slash.
5. Redeploy after adding or changing environment variables.
6. Promote only after the preview health and API checks pass, using the Vercel dashboard or `vercel --cwd "$DEPLOY_DIR" --prod`.

Record the stable backend production URL in the deployment inventory. Do not write it into application source.

If no frontend domain is known yet, set a temporary expected origin, deploy the frontend, then update `FRONTEND_ORIGIN` to the assigned frontend URL and redeploy the backend.

## 2. Deploy the Next.js Frontend

Create a second Vercel project from the repository:

1. Import the repository in Vercel.
2. Set the project root directory to `frontend` in the Vercel dashboard.
3. Confirm Vercel detects Next.js.
4. Use `npm ci` as the install command and `npm run build` as the build command if automatic detection does not select them.
5. Set `NEXT_PUBLIC_API_BASE_URL` to the backend HTTPS origin, without a trailing slash.
6. Deploy a preview and verify it before promoting to production.

`NEXT_PUBLIC_API_BASE_URL` is embedded in the browser build. Any change requires a new frontend deployment.

After Vercel assigns the frontend production URL, confirm that the backend's `FRONTEND_ORIGIN` is exactly that origin. Redeploy the backend if it was initially configured with a placeholder.

## 3. Configure Domains and CORS

For default Vercel domains:

- Frontend example: `https://fdasearch.vercel.app`
- Backend example: `https://fdasearch-api.vercel.app`

Set:

```text
Frontend NEXT_PUBLIC_API_BASE_URL=https://fdasearch-api.vercel.app
Backend FRONTEND_ORIGIN=https://fdasearch.vercel.app
```

If custom domains are used, update both values to the custom HTTPS origins and redeploy both projects. The current backend allows one exact browser origin, so preview frontend deployments will not have browser access to the production backend unless their specific origin is deliberately configured in a separate backend environment.

## 4. Verification Checklist

Verify from a clean browser session:

- Backend `/api/v1/health` returns HTTP 200 and `{"status":"ok"}`.
- Frontend `/` loads the drug experience.
- Frontend `/devices` loads the device experience.
- Drug name and NDC searches work.
- Ambiguous drug results require explicit selection.
- Device DI, UDI text, brand, and model/catalog searches work.
- Drug and device summaries load.
- Drug and device chat work.
- Browser developer tools show no CORS failures.
- An intentionally invalid search produces a useful application error without a stack trace.
- No API key appears in page source, browser network request headers, or the generated frontend bundle.

Use representative live checks sparingly and respect FDA and AI-provider usage limits.

## 5. Observability and Operations

- Use the backend project's Vercel logs for request failures, external API failures, and model fallback behavior.
- Use the frontend project's build and runtime logs for Next.js failures.
- Never enable logging that emits request authorization headers, environment variables, or complete external payloads.
- Review function duration and memory use after representative searches and AI calls.
- Treat container instances as ephemeral and stateless.

## 6. Release and Rollback

For each release:

1. Run the local verification suite.
2. Deploy backend and frontend previews from the same application revision.
3. Complete the verification checklist against previews.
4. Promote the backend, then the frontend.
5. Record application revision, backend deployment, frontend deployment, environment, and verification result outside the application repository.

To roll back, promote the last verified backend deployment and the matching frontend deployment in their respective Vercel projects. Roll back both when an API contract changed.

## 7. Teardown

For a temporary demo environment:

1. Confirm the environment is no longer referenced by a domain or stakeholder.
2. Remove custom-domain mappings.
3. Delete the frontend and backend Vercel projects.
4. Revoke or rotate secrets that were dedicated to the environment.
5. Remove the temporary deployment workspace locally.

Do not delete shared accounts, domains, or secrets without confirming their exact scope.

## Official References

- [Vercel FastAPI deployment](https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel)
- [Vercel container deployments](https://vercel.com/kb/guide/does-vercel-support-docker-deployments)
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Vercel CLI deployment](https://vercel.com/docs/cli/deploy)
