# Code Xray — Software Forensics & Change Impact Intelligence

**Code Xray** is an evidence-backed codebase intelligence and software forensics engine. Given any local repository or GitHub repository (public or private), Code Xray reconstructs AST representations, call graphs, dependency graphs, test relationships, and Git history to answer the critical developer question:

> **\"If I need to change X, where should I look, what will be affected, what is risky, what tests are relevant, and why?\"**

---

## The Problem: Why Code Search & LLMs Are Insufficient

When developers join a large codebase or refactor legacy systems:
- **Grep / Keyword Search**: Finds strings, but is blind to call hierarchies, indirect dependencies, architectural boundaries, or test coverage.
- **Pure LLM Prompts**: Hallucinate call graphs, miss transitive blast radiuses, cannot trace AST-level symbol bindings, and leak sensitive credentials.
- **Code Xray Solution**: Combines deterministic static analysis (AST, call graphs, import graphs, documentation rule extraction) with a multi-factor risk engine and evidence-backed explanations. Every finding and recommendation cites verified facts from the codebase.

---

## System Architecture

`
Repository Ingestion (Local / Public Git / Private Git)
   │
   ▼
Static Analysis & Classification
   ├─ AST Symbol Extractor (Classes, Functions, Methods)
   ├─ Dependency Analyzer (Internal imports vs External packages)
   ├─ Call Graph Builder (Direct & Transitive Invocations)
   ├─ Test Analyzer (Test-to-Implementation Mapping)
   ├─ Git History Analyzer (Churn, Bus Factor, Ownership)
   └─ Architecture Document Parser (Markdown Rules & Layer Directives)
   │
   ▼
Forensic Detectors
   ├─ Architecture Drift (e.g. Controller directly bypassing Service to Repository)
   ├─ Dead Features (Unreachable, uncalled, and untested legacy modules)
   ├─ Ghost Dependencies (Declared in requirements.txt but never imported)
   └─ Knowledge Concentration (High-churn files dominated by single authors)
   │
   ▼
Change Impact Engine (The Core MVP)
   ├─ Natural-Language Task Parser (Deterministic concept extraction)
   ├─ Bounded Multi-Hop Traversal (Upstream callers + Downstream callees)
   ├─ Test Suite Association
   ├─ Multi-Factor Risk Assessment (0-100 score + LOW/MEDIUM/HIGH/CRITICAL)
   ├─ Ordered Step-by-Step Investigation Path
   └─ AI / Deterministic Fact-and-Inference Explanation
`

---

## Core Features

### 1. Secure Repository Ingestion
- **Local Repositories**: Mount any local filesystem path.
- **Public GitHub Repositories**: Clone standard public repositories.
- **Private GitHub Repositories**: Authenticated cloning using non-interactive Git credential helpers (GIT_TERMINAL_PROMPT=0).
  - **Zero Credential Leakage**: Personal Access Tokens (PATs) are never printed in logs, never persisted to disk, never placed in repository URLs, and are automatically redacted from error traces.

### 2. Forensic Detectors
- **Architecture Drift**: Detects violations against documented rules (e.g., in rchitecture.md where Controller -> Service -> Repository is required, but a controller directly queries a repository).
- **Dead Features**: Pinpoints legacy files and functions that have no incoming calls, imports, or test invocations (e.g., src/legacy/old_hasher.py).
- **Ghost Dependencies**: Identifies dependencies declared in equirements.txt that are completely unused across the codebase (e.g., unused 
umpy).
- **Knowledge Concentration**: Quantifies bus-factor vulnerabilities where files are modified exclusively by a single contributor with high commit counts.

### 3. Change Impact Intelligence (MVP)
Given a natural language task (e.g., \"I need to modify the payment authentication flow\"), Code Xray outputs:
- **Directly Matched Entities & Files**: Entry points relevant to the request.
- **Affected Entity Graph**: All upstream callers and downstream dependencies traversed up to 3 hops deep.
- **Associated Tests**: Exact test suites covering the impacted modules.
- **Known Forensic Findings**: Flags if the proposed change path contains architectural violations or dead code.
- **Multi-Factor Risk Scoring**: Deterministic 0–100 score with granular risk factors:
  - *Baseline Modification Risk*
  - *Broad Scope / Multi-Component Scope*
  - *Deep Dependency Chain*
  - *Test Coverage Gap*
  - *Architectural Drift*
  - *High Historical Churn / Knowledge Concentration*
- **Recommended Investigation Path**: Ordered sequence of code entities with assigned roles (entry_point, usiness_logic, data_access, alidation, dependency).
- **Evidence-Backed Explanation**: Dual-mode explanation ([FACT] direct code facts vs. [INFERENCE] architectural blast radius) with deterministic fallback if no LLM API key is present.

---

## Project Structure

`
code-xray/
├── backend/
│   ├── app/
│   │   ├── ai/               # ForensicExplainer and prompt templates
│   │   ├── analyzer/         # AST parser, call graph, dependencies, git, tests, docs
│   │   ├── api/              # FastAPI route controllers
│   │   │   ├── routes_repository.py
│   │   │   ├── routes_github.py
│   │   │   ├── routes_scan.py
│   │   │   ├── routes_findings.py
│   │   │   └── routes_impact.py
│   │   ├── classification/   # Language, framework, and project type detection
│   │   ├── detectors/        # Architecture drift, dead features, ghost dependencies, knowledge
│   │   ├── evidence/         # Evidence chain engine and confidence scoring
│   │   ├── impact/           # ImpactAnalyzer, TaskParser, and RiskEngine
│   │   ├── ingestion/        # LocalRepoLoader, PublicRepoLoader, PrivateRepoLoader
│   │   ├── models/           # Pydantic data models
│   │   ├── privacy/          # Secret scanning and token redactor
│   │   ├── services/         # RepositoryService, GitHubService, ScanService
│   │   ├── storage/          # In-memory store
│   │   ├── config.py         # App configuration
│   │   └── main.py           # FastAPI application entry point
│   │
│   ├── tests/                # Comprehensive backend pytest suite (30 unit & e2e tests)
│   └── requirements.txt      # Backend dependencies
│
├── demo-repository/          # Target demonstration codebase
│   ├── architecture.md       # Target architecture guidelines
│   ├── requirements.txt      # Dependencies including ghost dependency (numpy)
│   ├── src/
│   │   ├── auth/             # Token validation
│   │   ├── controllers/      # Payment controller (contains architectural drift)
│   │   ├── legacy/           # Old hasher (dead feature)
│   │   ├── models/           # Data models
│   │   ├── repositories/     # Payment repository
│   │   └── services/         # Payment and Auth services
│   └── tests/                # Unit test suites
│
├── .gitignore
└── README.md
`

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | / | API metadata and endpoint index |
| GET | /health | Service health status check |
| GET | /repositories | List all scanned/registered repositories |
| GET | /repository/{id} | Get repository details and metadata |
| POST | /repository/local | Ingest and register a local repository directory |
| POST | /github/public | Clone and ingest a public GitHub repository |
| POST | /github/private | Clone and ingest a private GitHub repository securely |
| POST | /repository/scan | Trigger full static and forensic scan |
| GET | /repository/scan/{id} | Retrieve scan progress and status |
| GET | /analysis/{repo_id} | Retrieve full AST, dependency, and call graph analysis |
| GET | /findings/{repo_id} | List forensic findings (drift, dead code, ghost deps) |
| GET | /findings/{repo_id}/{finding_id} | Get specific finding with full evidence chain |
| POST | /impact/{repo_id} | Run Change Impact Intelligence for a natural-language task |
| GET | /impact/{repo_id} | List historical impact analyses for a repository |
| GET | /impact/{repo_id}/{analysis_id} | Retrieve specific impact analysis result |

Interactive OpenAPI / Swagger docs are available at http://127.0.0.1:8000/docs.

---

## Quickstart: Running Locally

### 1. Prerequisites
- Python 3.10+
- Git installed on system PATH

### 2. Setup Environment & Install Dependencies
`ash
cd backend
pip install -r requirements.txt
`

### 3. Start the Backend Server
`ash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
`

---

## Running the Automated Test Suites

### Backend Test Suite (30 Tests)
Run explicitly from the ackend/ directory:
`ash
cd backend
python -m pytest tests -v
`

### Demo Repository Test Suite (4 Tests)
Run from the demo-repository/ directory:
`ash
cd demo-repository
python -m pytest tests -v
`

---

## End-to-End Demo Walkthrough

### Step 1: Ingest Local Repository
`ash
curl -X POST http://127.0.0.1:8000/repository/local \
  -H \"Content-Type: application/json\" \
  -d '{\"path\": \"D:/CodeForensic/demo-repository\", \"name\": \"DemoRepo\"}'
`

### Step 2: Trigger Forensic Scan
`ash
curl -X POST http://127.0.0.1:8000/repository/scan \
  -H \"Content-Type: application/json\" \
  -d '{\"path\": \"D:/CodeForensic/demo-repository\", \"name\": \"DemoRepo\"}'
`

### Step 3: Inspect Architectural & Forensic Findings
`ash
curl http://127.0.0.1:8000/findings/<repository_id>
`
*Identifies*:
- rchitecture_drift: Controller imports repository directly, bypassing service layer.
- dead_feature: src/legacy/old_hasher.py has no callers or references.
- ghost_dependency: 
umpy declared in equirements.txt but never imported.

### Step 4: Run Change Impact Analysis
`ash
curl -X POST http://127.0.0.1:8000/impact/<repository_id> \
  -H \"Content-Type: application/json\" \
  -d '{\"task\": \"I need to modify the payment authentication flow\"}'
`
*Returns*:
- **Impact Level**: CRITICAL (Risk Score: 78/100)
- **Affected Entities**: 20 entities mapped across controllers, services, repositories, and auth modules
- **Related Tests**: 	ests/test_payment.py, 	ests/test_auth.py
- **Ordered Investigation Path**:
  1. get_payment (src/repositories/payment_repository.py) [data_access]
  2. handle_payment (src/controllers/payment_controller.py) [entry_point]
  3. payment_model.py (src/models/payment_model.py) [dependency]
  4. payment_service.py (src/services/payment_service.py) [business_logic]
  5. uthenticate_transaction (src/services/auth_service.py) [business_logic]
- **AI Explanation**: Evidence-backed summary detailing why the change carries risk and exact steps to take.
