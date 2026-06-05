# AI App Compiler

> A compiler-like pipeline that converts natural language into structured, validated, executable application configurations.

```
Natural Language → Structured Config → Validated → Executable → Working Application
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│   LEXER     │────▶│   PARSER     │────▶│   IR GENERATOR  │────▶│  OPTIMIZER   │
│ (Intent     │     │ (System      │     │ (Schema         │     │ (Refinement  │
│  Extraction)│     │  Design)     │     │  Generation)    │     │  Layer)      │
└──────┬──────┘     └──────┬───────┘     └───────┬─────────┘     └──────┬───────┘
       │ IntentIR          │ DesignIR            │ SchemaIR            │ AppSpec
       ▼                   ▼                     ▼                     ▼
  [GATE 1]            [GATE 2]              [GATE 3]              [GATE 4]
  Validate            Validate              Validate              Validate
       │                   │                     │                     │
       ▼                   ▼                     ▼                     ▼
  [REPAIR]            [REPAIR]              [REPAIR]              [REPAIR]
  if needed           if needed             if needed             if needed
```

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Pipeline model | Compiler (Lexer→Parser→IR→Optimizer) | Matches the assignment framing; provides clean stage boundaries with typed IRs |
| Validation | 3-layer (structural→semantic→cross-layer) | Catches errors at increasing depth; enables targeted repair |
| Repair | Deterministic fixes first, then LLM-targeted | Saves cost on fixable issues; LLM only for complex repairs |
| Schemas | Pydantic models as schema registry | Python-native type safety; automatic validation; clean serialization |
| Runtime proof | HTML/CSS/JS code generation from AppSpec | Proves output is executable without building a full framework |
| Determinism | temperature=0, seed=42, JSON mode | Maximizes consistency across runs |
| Cost control | Token tracking per stage, fast model for simple tasks | Transparency on cost; cheaper calls where quality allows |

## Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key

### Setup

```bash
# Clone the repo
git clone <repo-url>
cd ai-app-compiler

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run

```bash
# Start the server
python -m uvicorn backend.main:app --reload --port 8000

# Open http://localhost:8000
```

### Run Evaluation Suite

```bash
python -m backend.evaluation.runner
```

## Project Structure

```
├── backend/
│   ├── main.py                    # FastAPI app + routes
│   ├── config.py                  # Environment + constants
│   ├── pipeline/                  # Compiler stages
│   │   ├── orchestrator.py        # Pipeline runner with gates
│   │   ├── stage_1_lexer.py       # Intent extraction
│   │   ├── stage_2_parser.py      # System design
│   │   ├── stage_3_ir_generator.py # Schema generation
│   │   └── stage_4_optimizer.py   # Refinement
│   ├── schemas/                   # Pydantic schema registry
│   │   ├── common.py              # Shared types
│   │   ├── intent_ir.py           # Stage 1 output
│   │   ├── design_ir.py           # Stage 2 output
│   │   ├── schema_ir.py           # Stage 3 output
│   │   └── app_spec.py            # Stage 4 output (final)
│   ├── validation/                # Validation engine
│   │   ├── validator.py           # Main orchestrator
│   │   ├── structural_checks.py   # JSON + schema checks
│   │   ├── semantic_checks.py     # Logic checks
│   │   └── cross_layer_checks.py  # UI↔API↔DB↔Auth consistency
│   ├── repair/                    # Repair engine
│   │   ├── repair_engine.py       # Repair orchestrator
│   │   ├── strategies.py          # Fix strategies
│   │   └── retry_policy.py        # Budget + convergence
│   ├── runtime/                   # Execution proof
│   │   ├── simulator.py           # Simulation orchestrator
│   │   └── code_generator.py      # AppSpec → HTML/JS
│   ├── llm/                       # LLM client
│   │   ├── client.py              # OpenAI wrapper
│   │   ├── prompts.py             # All stage prompts
│   │   └── cost_tracker.py        # Token + cost tracking
│   └── evaluation/                # Evaluation framework
│       ├── runner.py              # Test suite runner
│       ├── metrics.py             # Metrics models
│       └── test_prompts.py        # 20 test prompts
├── frontend/
│   ├── index.html                 # Main UI
│   ├── css/styles.css             # Dark theme
│   └── js/                        # App logic
├── generated_apps/                # Runtime output
├── Dockerfile
└── README.md
```

## Key Components

### Multi-Stage Pipeline
Each stage has typed input/output (Pydantic models), runs independently, and passes through a validation gate before the next stage.

### Validation Engine (3 Layers)
1. **Structural**: Valid JSON? Required fields? Correct types?
2. **Semantic**: Duplicate entities? Valid FK references? Logical field types?
3. **Cross-Layer**: UI→API endpoint exists? API→DB column exists? Auth roles consistent?

### Repair Engine
- Tries **deterministic fixes first** (add missing timestamps, fix PKs) — free, no LLM cost
- Falls back to **targeted LLM repair** — sends only the errors + current schema
- **Convergence detection** — if same errors repeat, abort early
- **Budget** — max 3 retries per stage

### Runtime Simulator
- Generates a complete single-page HTML application from AppSpec
- Includes navigation, forms, tables, mock API (localStorage), and auth simulation
- Runs 6 structural validity checks on the generated code

## Tradeoffs

| Tradeoff | Choice | Why |
|----------|--------|-----|
| Quality vs Cost | GPT-4o for complex stages, could use mini for S1 | S1 is simpler extraction; S3/S4 need full power |
| Latency vs Accuracy | 4 sequential LLM calls | Can't parallelize — each stage depends on previous |
| Repair depth vs Budget | Max 3 retries with convergence detection | Diminishing returns after 2-3 attempts |
| Runtime fidelity vs Scope | Static HTML with mock API | Full runtime (like base44) would take weeks |

## Limitations

1. **Token limits** — Very complex apps with many entities may exceed context windows
2. **Runtime fidelity** — Generated apps use localStorage mocks, not real backends
3. **Determinism** — Despite temperature=0 and seed, minor variations can occur across runs
4. **Business logic depth** — Complex conditional logic is captured but simplified
5. **Cost** — Full pipeline costs ~$0.05-0.15 per compilation depending on prompt complexity

## API

### `POST /api/compile`
Compiles a natural language prompt into an AppSpec.

**Request:**
```json
{ "prompt": "Build a CRM with login, contacts, dashboard..." }
```

**Response:**
```json
{
  "success": true,
  "app_spec": { "metadata": {}, "ui": {}, "api": {}, "db": {}, "auth": {}, "business_logic": [] },
  "pipeline": { "stages": [...], "total_latency_ms": 12000 },
  "cost": { "total_calls": 4, "total_cost_usd": 0.08, "total_tokens": 15000 },
  "runtime": { "is_executable": true, "checks": [...] }
}
```

### `GET /api/preview/{app_name}`
Serves the generated HTML app for preview.

### `GET /health`
Health check endpoint.
