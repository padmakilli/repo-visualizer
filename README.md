# Repository Structure Analysis & Visualisation System

Jumping into a large, unfamiliar codebase is hard: folder trees tell you *where*
files live but nothing about *how* they depend on each other or which ones are
quietly carrying all the complexity. This tool statically analyses a local Git
repository and renders it as an **interactive dependency graph** — an infinite,
draggable canvas where every file is a node, every import is an edge, and a
click gives you a plain‑English, AI‑generated summary of what a file actually
does.

The system is built around four design goals drawn straight from the problem
statement:

| Challenge | How this project solves it |
|-----------|----------------------------|
| **Hidden relationships** — explorers show folders, not interactions | A static analyser extracts imports/includes (Python `import`, JS/TS `import`/`require`, C/C++ `#include`, Java, Go) **without ever executing the code**, and resolves them to intra‑repo edges. |
| **Clunky visualisation** — static diagrams don't scale | A **React Flow** canvas with draggable nodes, zoom/pan, a minimap, and directory‑grouped auto‑layout. |
| **Slow onboarding** — reading code takes time | Clicking a node calls an AI provider (Anthropic / OpenAI / Gemini) with *"Explain what this code does in 3 simple sentences"* and shows the result in a side panel. |
| **Missing context** — bloated files are hard to spot | Every node displays **Lines of Code, source lines, and an approximate cyclomatic‑complexity heat bar**. |

To keep AI costs down, summaries are **cached locally by content hash** — a file
is only re‑analysed when its contents (or the chosen model) change.

---

## Architecture

```
┌──────────────────────────┐         POST /api/analyze          ┌───────────────────────────┐
│   React + React Flow      │  ───────────────────────────────► │   FastAPI backend          │
│   (Vite dev server)       │         nodes + edges JSON         │                            │
│                           │  ◄───────────────────────────────  │  ┌──────────────────────┐ │
│  • draggable canvas       │                                    │  │ analyzer             │ │
│  • metrics on each node   │         POST /api/file             │  │  traverse → metrics  │ │
│  • AI side panel          │  ───────────────────────────────► │  │  → parse → resolve   │ │
│                           │         POST /api/explain          │  └──────────────────────┘ │
│                           │  ◄───────────────────────────────  │  ┌──────────────────────┐ │
└──────────────────────────┘        summary (+ cached flag)      │  │ AI: provider + cache │ │
                                                                 │  └──────────────────────┘ │
                                                                 └───────────────────────────┘
```

The frontend talks to the backend over plain REST. In development the Vite
server proxies `/api/*` to `http://localhost:8000`, so the two run side‑by‑side
with no CORS friction.

### Repository layout

```
repo-visualizer/
├── backend/                     # Python + FastAPI analysis engine
│   ├── app/
│   │   ├── analyzer/            # the static-analysis core (no code execution)
│   │   │   ├── traverser.py         # walk the tree, skip junk dirs
│   │   │   ├── languages.py         # extension → language, comment syntax
│   │   │   ├── dependency_parser.py # regex import/include extractors
│   │   │   ├── resolver.py          # map raw imports → intra-repo edges
│   │   │   ├── metrics.py           # LoC / SLoC / cyclomatic complexity
│   │   │   └── graph_builder.py     # orchestrates the above → graph
│   │   ├── ai/
│   │   │   ├── providers.py         # Anthropic / OpenAI / Gemini / Null
│   │   │   ├── cache.py             # SQLite cache keyed by content hash
│   │   │   └── summarizer.py        # cache-then-provider explain flow
│   │   ├── api/routes.py        # /analyze, /file, /explain, /health
│   │   ├── paths.py             # path-traversal confinement
│   │   ├── models.py            # Pydantic request/response schemas
│   │   ├── config.py           # env-driven settings
│   │   └── main.py             # app factory
│   ├── tests/test_analyzer.py  # analyzer unit tests
│   ├── requirements.txt
│   └── .env.example
└── frontend/                    # React + React Flow client
    ├── src/
    │   ├── components/         # Toolbar, GraphCanvas, FileNode, SidePanel, Legend
    │   ├── utils/              # colour + layout helpers
    │   ├── api/client.js       # REST client
    │   └── App.jsx
    ├── package.json
    └── vite.config.js
```

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- *(optional)* an API key for Anthropic, OpenAI, or Google Gemini — without one
  the app still runs and shows metrics + graph; the AI panel just returns a
  friendly "configure a provider" message.

---

## Running the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then edit if you want AI summaries
uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

Run the analyzer test suite with:

```bash
pytest
```

## Running the frontend

```bash
cd frontend
npm install
npm run dev
```

Open the printed URL (default `http://localhost:5173`), paste the **absolute
path** to any local repository into the bar, and hit **Analyze**.

> **Quick demo:** point the tool at this project's own `backend` folder — you'll
> see the analyzer modules light up with their real import edges.

---

## AI configuration

Configure everything through `backend/.env` (see `.env.example`):

```ini
# Choose one: anthropic | openai | gemini | null
AI_PROVIDER=anthropic

ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# GEMINI_API_KEY=...

# Optional model overrides (sensible defaults are built in)
# ANTHROPIC_MODEL=claude-haiku-4-5
# OPENAI_MODEL=gpt-4o-mini
# GEMINI_MODEL=gemini-1.5-flash
```

The default Anthropic model is **`claude-haiku-4-5`** — fast and inexpensive,
which suits short per‑file summaries. Providers are implemented over plain HTTP
(`httpx`), so no vendor SDK is required.

### The summary cache

Summaries are stored in a small SQLite database (`CACHE_DB`, default
`./.cache/summaries.db`). The cache key is a hash of **(file contents + provider
+ model)**. Consequences:

- Re‑clicking an unchanged file is **free** — it's served from cache and the
  panel shows a `cached` badge.
- Editing the file changes its hash, so it's automatically re‑summarised.
- Switching provider or model re‑summarises (the old entry stays cached too).
- Hit **Re‑run** in the panel to force a fresh summary (`force: true`).

---

## API reference

| Method | Endpoint | Body | Returns |
|--------|----------|------|---------|
| `GET`  | `/api/health` | — | provider + sandbox status |
| `POST` | `/api/analyze` | `{ "path": "/abs/repo" }` | `{ root, nodes[], edges[], stats }` |
| `POST` | `/api/file` | `{ "root", "path" }` | file content + metrics + imports |
| `POST` | `/api/explain` | `{ "root", "path", "force"? }` | `{ summary, cached, provider, model }` |

A **node** carries `id`, `label`, `path`, `language`, `loc`, `sloc`,
`complexity`, `size_bytes`, and `in_degree`/`out_degree`. An **edge** is a
directed `source → target` dependency.

---

## How the static analysis works

1. **Traverse** — `os.walk` over the repo, pruning noise (`.git`,
   `node_modules`, `__pycache__`, `venv`, `dist`, `build`, …).
2. **Measure** — for each supported file, count total lines, source lines
   (blanks and comments stripped), and an approximate **cyclomatic complexity**
   by counting decision keywords (after removing strings/comments so keywords
   inside literals don't inflate the score).
3. **Parse** — language‑specific regexes pull out import/include/require
   statements. **Nothing is imported, compiled, or executed.**
4. **Resolve** — raw import targets are matched back to actual files in the repo
   (Python relative + absolute packages, JS/TS relative paths with extension and
   `index` resolution, C/C++ local headers, Java package paths, Go module
   paths). Only edges that point *inside* the repo are emitted.

This keeps analysis safe to run on untrusted code and fast even on large trees.

### Safety

All `/file` and `/explain` reads are confined to roots that have been analysed
in the current session (or to an optional `REPO_ROOT` sandbox), and every path
is resolved and checked so `../` traversal outside the root is rejected.

---

## Limitations & ideas for extension

- Import **resolution is heuristic**, not a full compiler front‑end; dynamic
  imports and unusual build setups may be missed.
- Complexity is an **approximation** (decision‑keyword count), not a full AST
  metric — good for spotting hotspots at a glance.
- Natural extensions: dependency‑cruiser‑style cycle detection, persisting
  node layouts, more languages, and clustering by package.

---

## License

MIT — see [LICENSE](./LICENSE).
