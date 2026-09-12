# CodeWitness Frontend

A hackathon-ready React/Vite frontend for the CodeWitness software-forensics concept.

## Run

```bash
npm install
npm run dev
```

Open the Vite URL shown in the terminal.

## Demo flow

1. Landing page → paste a GitHub URL
2. Investigate → simulated scan
3. Dashboard → scores, findings and risk forecast
4. Open the architecture violation
5. Inspect the evidence chain and architecture graph
6. Start repair workflow
7. Mark implemented → verification screen

## Backend integration

The frontend already includes `src/api/client.js` with:

- `POST /api/scans`
- `GET /api/scans/:scanId`

Set `VITE_API_URL` when connecting to FastAPI, for example:

```bash
VITE_API_URL=http://localhost:8000 npm run dev
```

The current pages intentionally use mock data so the frontend can be developed independently from the forensic engine.
