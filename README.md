# Agnes - AI-Powered Procurement Intelligence

**Q-Hack 2026 | Team Artificially Unintelligent**

Agnes is a modular decision-support system that transforms procurement from a logistical task into a data-driven intelligence workflow. It identifies consolidation opportunities and verifies technical raw materials using traceable, document-linked evidence.

## Architecture

Agnes runs a 4-step pipeline for any ingredient in the Spherecast database:

```
Layer 1: Requirements    Extract hard/soft quality constraints from regulatory standards (USP, FCC, EU)
       |
Layer 2: Suppliers       Find suppliers from internal DB + web search (DuckDuckGo)
       |
Layer 3: Verification    Fetch TDS/COA documents, extract values via Gemini, verify against requirements
       |
Layer 4: Ranking         Score suppliers by quality-of-pass with confidence and margin bonuses
```

Each layer is independently testable with published Pydantic I/O contracts.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.13, Pydantic v2 |
| AI/LLM | Google Gemini (gemini-2.5-flash / gemini-2.5-pro) via google-genai SDK |
| Search | DuckDuckGo (supplier discovery + evidence search) |
| Web Scraping | curl_cffi (Chrome TLS impersonation to bypass bot detection) |
| PDF Parsing | pdfplumber |
| Database | SQLite (Spherecast product/supplier data) |
| Streaming | Server-Sent Events (SSE) for real-time pipeline traces |

## Getting Started

### Prerequisites

- Python 3.13+ (install via `uv python install 3.13`)
- Node.js 18+ 
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

### Setup

```bash
# Clone the repo
git clone https://github.com/your-org/Q-Hack-2026-Team-Artificially-Unintelligent.git
cd Q-Hack-2026-Team-Artificially-Unintelligent

# Python environment
uv venv .venv --python 3.13
source .venv/bin/activate
pip install -r requirements.txt

# Node dependencies
npm install

# Environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

Also create `src/quality_verification_layer/.env`:
```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-pro
```

### Running

```bash
# Start both frontend and backend together
npm run dev

# Or separately:
# Terminal 1 - Backend (FastAPI)
.venv/bin/uvicorn api.index:app --reload --port 8000

# Terminal 2 - Frontend (Next.js)
npx next dev
```

Open [http://localhost:3000](http://localhost:3000) and select an ingredient to run the pipeline.

### CLI Demo

```bash
# Run the CLI demo directly
cd src/quality_verification_layer
python demo.py -i niacinamide

# With cached results (fast rerun)
python demo.py -i calcium-citrate --fast

# List all available ingredients
python demo.py --list

# Offline demo with sample TDS files
python demo.py --sample
```

## Project Structure

```
.
├── api/index.py                          # FastAPI backend (SSE pipeline, PDF proxy)
├── src/
│   ├── app/                              # Next.js frontend
│   │   ├── page.tsx                      # Pipeline orchestrator + tab UI
│   │   ├── components/
│   │   │   ├── RequirementsTab.tsx        # L1: Requirements table
│   │   │   ├── SuppliersTab.tsx           # L2: Supplier cards
│   │   │   ├── VerificationTab.tsx        # L3: Evidence + extraction + verification
│   │   │   ├── RankingTab.tsx             # L4: Score bars + ranking table
│   │   │   ├── AgentTrace.tsx             # Live trace sidebar
│   │   │   └── PdfPreview.tsx             # Source viewer modal
│   │   ├── hooks/usePipeline.ts           # SSE client for real-time streaming
│   │   └── types.ts                       # TypeScript interfaces (mirrors Pydantic)
│   │
│   ├── requirement_layer/                 # Layer 1: LLM-based requirements extraction
│   ├── competitor_layer/                  # Layer 2: Web search + candidate discovery
│   └── quality_verification_layer/        # Layer 3: Document retrieval + verification
│       ├── quality_verification_layer/    # Core package
│       │   ├── schemas.py                 # Pydantic I/O contracts
│       │   ├── runner.py                  # Pipeline orchestrator
│       │   ├── retrieval.py               # URL fetching (curl_cffi)
│       │   ├── extraction.py              # Gemini attribute extraction
│       │   ├── verification.py            # Requirement verification logic
│       │   ├── normalization.py           # Canonical field mapping (70+ fields)
│       │   └── evidence_search.py         # DuckDuckGo evidence search
│       ├── demo.py                        # CLI demo script
│       └── demo_ui.py                     # Rich terminal UI
│
├── data/
│   ├── db.sqlite                          # Spherecast product/supplier database
│   └── requirements/                      # Pre-generated requirement JSON files
│
└── specs/                                 # Architecture specifications
```

## Key Features

- **Real-time pipeline streaming** via SSE with live agent traces
- **Full traceability**: every extracted value links back to its source document
- **Source viewer**: preview PDFs and web pages inline with extracted field annotations
- **Requirements-driven scoring**: quality-of-pass considers confidence, margin to limits, and dynamic hard/soft weighting
- **400+ ingredients** available from the Spherecast database
- **Canonical field normalization**: 70+ field name variants mapped to standard names

## Recommended Ingredients for Demo

These ingredients have good public TDS/COA availability:

| Ingredient | Expected Score | Notes |
|-----------|---------------|-------|
| niacinamide | ~70-85% | Default, good USP/FCC data |
| calcium-citrate | ~86% | Best real-world results |
| citric-acid | ~80% | Widely published specs |
| ascorbic-acid | ~75% | Vitamin C, lots of suppliers |
| zinc-oxide | ~70% | Good pharmaceutical data |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/py/run?ingredient=X` | SSE stream — runs full L1-L4 pipeline |
| `GET /api/py/ingredients` | List all available ingredient slugs |
| `GET /api/py/pdf?url=X` | Proxy for in-browser source viewing |
| `GET /api/py/health` | Health check |

## Team

**Team Artificially Unintelligent** - Q-Hack 2026
