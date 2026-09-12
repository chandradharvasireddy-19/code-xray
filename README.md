# CodeForensic Frontend

Frontend-only React + Vite application for the Software Forensics / Code-XRay investigation experience.

## IMPORTANT
This package contains **ONLY the frontend**. There is no `backend/`, FastAPI, Python environment, demo repository, or backend dependency in this ZIP.

Open this folder directly in VS Code. The `package.json` is at the project root, so run:

```bash
npm install
npm run dev
```

## Product flow

Home → Repository Type → Access Method → Repository Setup → Security Check → Scan → Forensic Report → Findings → Finding Details / WHY → Architecture Graph → Impact → Repair → Verification

## Visual direction

- Dark engineering / forensic visual language
- Atmospheric animated background only: grid, waves, scan beam, particles, data ribbons and abstract wireframe geometry
- Repository nodes/files do **not** appear in the global background
- Repository topology appears in the dedicated **Architecture Graph** report screen
- Expected vs Actual architecture toggle
- Animated dependency edges and violation highlighting
- Finding evidence chain and impact views
- Repair → Verify flow with red detected → green resolved state
- Mock data only for the frontend phase

## Main frontend areas

```text
src/
├── pages/          # Investigation and report screens
├── components/     # Reusable UI and forensic visualizations
├── data/            # Mock forensic repository/finding data
├── api/             # Isolated API client placeholders for later integration
├── styles/          # Global visual system
└── types/           # Shared frontend data shapes
```

## Team note

Keep the frontend working against mock data until the backend/API contract is agreed. Backend integration can be added later without changing the visual flow.
