# Product Intelligence Frontend

Responsive drug and medical-device search frontend for the Product Intelligence Platform. FastAPI remains the source of FDA domain logic and AI orchestration.

## Local Development

```bash
cp .env.example .env.local
npm install
npm run dev
```

Run FastAPI on `http://localhost:8000` and open the frontend on `http://localhost:3000`.

## Checks

```bash
npm run test
npm run lint
npm run typecheck
npm run build
```
