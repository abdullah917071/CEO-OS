<div align="center">

# 🧠 CEO OS — Autonomous Enterprise AI Operating System

<img src="https://img.shields.io/badge/Gemini%20Live-Realtime%20API-4285F4?style=for-the-badge&logo=google&logoColor=white" />
<img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" />
<img src="https://img.shields.io/badge/macOS-Apple%20Silicon-000000?style=for-the-badge&logo=apple&logoColor=white" />
<img src="https://img.shields.io/badge/Tests-189%20Passing-22C55E?style=for-the-badge&logo=pytest&logoColor=white" />
<img src="https://img.shields.io/badge/Agents-270+-8B5CF6?style=for-the-badge&logo=openai&logoColor=white" />

**One intelligent CEO agent that turns owner goals into auditable, evidence-backed work — delegated across a modular fleet of 270+ specialist agents, with a production-ready macOS voice assistant powered by Google Gemini Live API.**

[Live Dashboard →](#dashboard) · [Jarvis Voice Studio →](#jarvis-voice-assistant) · [Architecture →](#architecture) · [Quick Start →](#quick-start)

</div>

---

## ✨ What Is CEO OS?

CEO OS is a **local-first, production-grade personal AI operating system** designed for founders, executives, and power users who want a unified AI layer over their entire digital life.

It's not a chatbot. It's not a wrapper around OpenAI. It's an **autonomous enterprise system** with:

- 🧠 **CEO ReAct Agent** — multi-turn reasoning with XML thought scratchpads, tool dispatch, and reflection
- 🎙️ **Jarvis** — production-ready macOS voice assistant with local wake-word, zero idle costs, and Gemini Live bidirectional streaming
- 🖥️ **CUA Desktop Automation** — macOS Computer Use Agent that sees, clicks, and types
- 🌐 **Hermes Multi-Agent Framework** — orchestrates 270+ specialist agents from the Agency roster
- 🔌 **gstack Integration** — full software development workflow: Plan → Implement → Review → QA → Security → Release
- 📊 **Cybernetic Dashboard** — live chat interface with real-time task monitoring, voice control, and tool execution telemetry

---

## 🎙️ Jarvis Voice Assistant

> "Jarvis, open YouTube" → *Jarvis says "Opened sir, YouTube is now loading"* → YouTube opens in Safari

Jarvis is a **production macOS desktop voice assistant** that runs 24/7 with **zero idle API costs**:

| Feature | Detail |
|---------|--------|
| **Wake Word** | Local `openWakeWord` ONNX inference — "Jarvis", "Computer", "Friday", "Hey Nova" |
| **Connection Model** | Gemini Live WebSocket opened **only after wake word** — $0 idle cost |
| **Audio** | Bidirectional PCM16 at 16kHz via `sounddevice`, native macOS Core Audio |
| **Auth** | Google Cloud Service Account JSON → Vertex AI OAuth2 (never exposed to frontend) |
| **Voice** | 5 Gemini prebuilt voices: Puck, Charon, Kore, Fenrir, Aoede |
| **Barge-In** | Instant cancellation — speaking interrupts playback via generation ID |
| **macOS Tools** | AppleScript automation: open URLs, launch apps, control Spotify, check system stats |
| **Timeout** | Configurable inactivity disconnect (15s–120s) |
| **Configuration** | All settings editable via the web dashboard |

```
┌─────────────────────────────────────────────────────────┐
│                    JARVIS FLOW                          │
│                                                         │
│  Mic → openWakeWord ──► "Jarvis" detected               │
│                              │                          │
│                    Connect Gemini Live WebSocket        │
│                              │                          │
│              Bidirectional PCM Audio Streaming          │
│                    ┌─────────┴──────────┐               │
│                 Speak                Execute Tool       │
│                    │                   │                │
│            SpeechSynthesis      AppleScript/           │
│             (Jarvis replies)    osascript              │
│                              │                          │
│              Inactivity Timer → Disconnect              │
└─────────────────────────────────────────────────────────┘
```

---

## 🧠 CEO Agent — ReAct Reasoning Engine

The CEO agent uses a **multi-turn ReAct loop** with:

- **XML Thought Scratchpad** — `<thought>`, `<tool_call>`, `<observation>`, `<reflection>`, `<final_answer>`
- **Capability Router** — matches natural language to the best specialist agent or tool
- **ReAct Reflection** — validates outputs before surfacing to the user
- **Streaming Responses** — typed progressively in the dashboard chat interface

```python
# CEO ReAct Loop (simplified)
while not done:
    thought = llm.think(context, tools)
    if thought.has_tool_call:
        output = tool_registry.execute(thought.tool_call)
        context.add_observation(output)
    elif thought.has_final_answer:
        return thought.final_answer
```

---

## 🌐 Hermes — Multi-Agent Orchestration

Hermes manages a lazy-loaded roster of **270+ specialist Agency agents**:

| Tool | Description |
|------|-------------|
| `agency_agents_search` | Semantic search across the full agent roster |
| `agency_agents_inspect` | Load and inspect a specific agent's skills |
| `agency_agents_load` | Activate selected agents for a task |
| `agency_agents_delegate` | Delegate work to the loaded agent fleet |

**The CEO never loads all 270 agents at once.** It searches, selects, and loads only what's needed — keeping context windows tight and costs minimal.

---

## 🖥️ CUA Desktop Automation

The Computer Use Agent (CUA) enables autonomous macOS control:

- **Screenshot + Vision** — captures and interprets the screen
- **AppleScript/osascript** — safe macOS automation with typed permissions
- **App Control** — launch, focus, type, click, scroll
- **Browser Automation** — Playwright-based web control
- **Permission Matrix** — every tool has ALLOW / ASK / DENY policy

---

## 🔧 gstack Software Development Integration

CEO OS integrates gstack as a first-class development workflow provider:

```
CEO Agent
    └── Development Director
            └── gstack Skills Router
                    ├── Planning
                    ├── Implementation
                    ├── Code Review
                    ├── QA & Testing
                    ├── Security Audit
                    └── Release Management
                            └── Coding Agent / Codex
                                    └── Repository
```

---

## 📊 Dashboard

The **Cybernetic Dashboard** at `http://localhost:3000` provides:

- **Executive Chat Deck** — full chat-like interface with ReAct thought traces
- **Voice Control** — click mic or say "Jarvis" to send voice commands
- **Live Task Feed** — real-time WebSocket task cards with step-by-step execution
- **Jarvis Voice Studio** — configure wake word, model, voice, tools, and auth
- **CUA Desktop Host** — visual computer use sessions
- **Agent Workforce** — browse and inspect the 270+ specialist roster
- **Memory Vault** — persistent context and knowledge management
- **System Health** — infrastructure metrics and connection status

---

## 🏗️ Architecture

```
CEO-OS/
├── apps/
│   ├── api/          # FastAPI backend
│   └── dashboard/    # Next.js 14 frontend
│
├── core/             # CEO contracts, routing, orchestration
├── ceo_agent/        # ReAct reasoning engine
├── jarvis/           # Voice assistant (Gemini Live API)
├── hermes/           # Multi-agent orchestration framework
├── gstack/           # Software development workflow
│
├── agents/           # Domain agent implementations
├── tools/            # Capability implementations
├── integrations/     # External system connectors
│
├── memory/           # Persistent context and knowledge
├── computer/         # CUA desktop automation
├── browser/          # Playwright browser control
├── voice/            # TTS/STT providers
├── communications/   # Email, calendar, messaging
│
├── skills/           # Versioned reusable procedures
├── infrastructure/   # Docker, deployment configs
└── tests/            # 189 passing tests
```

### Architecture Guardrails

- ✅ CEO kernel depends on **contracts and registries**, never provider SDKs directly
- ✅ External effects pass through **typed capabilities, permissions, and audit events**
- ✅ Model, vector, telephony, browser, storage providers are **replaceable**
- ✅ Untrusted external content is **data, never instructions or authority**
- ✅ Secrets referenced by **credential identifiers** — never in prompts or logs
- ✅ Default to **workspace-scoped access** and least privilege
- ✅ R2–R4 actions require **policy evaluation**; irreversible actions require approval

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- `uv` (Python package manager)
- Node.js 20+
- Docker + Docker Compose
- macOS (for Jarvis voice features)
- Google Cloud project with Vertex AI enabled (for Jarvis)

### 1. Clone & Configure

```bash
git clone https://github.com/abdullah917071/CEO-OS.git
cd CEO-OS
cp .env.example .env
# Edit .env with your API keys
```

### 2. Install Dependencies

```bash
make install
```

### 3. Start Infrastructure

```bash
make infra-up
```

### 4. Run the Stack

```bash
# Option A: All services
make dev

# Option B: Individual services
make api        # FastAPI backend at http://localhost:8000
make dashboard  # Next.js dashboard at http://localhost:3000
```

### 5. Configure Jarvis Voice Assistant

1. Navigate to `http://localhost:3000/jarvis`
2. Go to **Google Cloud & Auth** tab
3. Paste your Google Cloud Service Account JSON
4. Click **Save & Store Securely**
5. Go to **Overview** and click **Activate Gemini Live**
6. Say "Jarvis" — it will detect locally and connect

### 6. Verify Installation

```bash
make check   # Runs all 189 tests + lint + type checks
```

---

## ⚙️ Configuration

All configuration is available via the web dashboard at `http://localhost:3000/jarvis` or directly in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | LLM provider for CEO agent | Required |
| `OPENROUTER_MODEL` | Model for reasoning | `anthropic/claude-3.5-sonnet` |
| `JARVIS_WAKE_WORD` | Wake word to activate Jarvis | `jarvis` |
| `JARVIS_INACTIVITY_TIMEOUT` | Seconds before auto-disconnect | `60` |
| `JARVIS_GEMINI_VOICE` | Prebuilt voice name | `Puck` |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID for Vertex AI | From service account |
| `HERMES_AGENTS_PATH` | Path to Agency agent roster | `./agency` |

---

## 🔒 Security

- **Service Account JSON** stored with `0600` filesystem permissions — never exposed to JavaScript
- **Private keys** never placed in prompts, logs, or environment variables
- **Tool permissions** enforced at runtime: ALLOW / ASK / DENY per tool
- **Audit trail** — every tool execution logged with actor, arguments, and output
- **Workspace-scoped access** — default least privilege model

---

## 🧪 Testing

```bash
# Run full test suite
uv run pytest

# Run specific suites
uv run pytest tests/test_jarvis.py           # Voice assistant tests
uv run pytest tests/test_ceo_agent.py        # ReAct reasoning tests
uv run pytest tests/test_hermes_agent.py     # Multi-agent tests
uv run pytest tests/test_gstack.py           # Dev workflow tests

# Run checks
make check  # lint + type check + tests + dashboard build
```

**Current Status: 189 tests passing** ✅

---

## 🗺️ Roadmap

### Milestone 1 ✅ CEO Text Prototype
- CEO ReAct agent with XML thought traces
- Basic tool dispatch and task management
- Dashboard with chat interface

### Milestone 2 ✅ Jarvis Voice Assistant  
- Local wake-word detection (zero idle cost)
- Gemini Live bidirectional WebSocket
- Safe macOS tool execution
- Web-based configuration dashboard

### Milestone 3 ✅ Hermes Multi-Agent
- 270+ specialist agent roster
- Lazy loading and semantic search
- Agent delegation and orchestration

### Milestone 4 ✅ gstack Integration
- Development workflow provider
- Plan → Implement → Review → QA → Release pipeline
- Modular, replaceable architecture

### Milestone 5 🔄 Production Hardening
- Proactive CEO intelligence
- Multi-model routing
- Advanced memory and context management
- Mobile companion app

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, asyncio |
| **Package Management** | `uv` |
| **Frontend** | Next.js 14, React 18, TypeScript |
| **Styling** | CSS Modules (no Tailwind dependencies) |
| **LLM Providers** | OpenRouter (CEO), Google Vertex AI (Jarvis) |
| **Voice** | Google Gemini Live API, openWakeWord ONNX, sounddevice |
| **Database** | SQLite (local), PostgreSQL (production) |
| **Cache** | Redis |
| **Search** | Qdrant (vector) |
| **Infrastructure** | Docker Compose |
| **Testing** | pytest, Playwright |
| **Linting** | Ruff, mypy, ESLint |

---

## 📁 Repository Map

```
apps/          Deployable API and dashboard
core/          CEO contracts, routing, orchestration
ceo_agent/     ReAct reasoning engine with XML scratchpad
jarvis/        Production macOS voice assistant (Gemini Live)
hermes/        Multi-agent orchestration framework
gstack/        Software development workflow integration
agents/        Domain agent implementations
tools/         Typed capability implementations
integrations/  External system connectors (Google, Meta, etc.)
memory/        Persistent context and knowledge management
computer/      CUA desktop automation (macOS)
browser/       Playwright browser automation
voice/         TTS/STT provider abstractions
communications/ Email, calendar, Slack, messaging
skills/        Versioned reusable procedures
infrastructure/ Docker, nginx, deployment configs
plans/         Architecture decision records
docs/          Numbered architecture source of truth
tests/         Unit, integration, contract, and evaluation suites
```

---

## 🤝 Contributing

See [`AGENTS.md`](AGENTS.md) for the engineering rules and architecture guardrails. Read [`CURRENT_STATE.md`](CURRENT_STATE.md) for verified capabilities and [`PLANS.md`](PLANS.md) for the roadmap.

Before contributing:
1. Read `AGENTS.md`, `CURRENT_STATE.md`, `PLANS.md`, and relevant `docs/` documents
2. Inspect the current implementation
3. Work on one roadmap milestone at a time
4. Add/update tests, run `make check`, fix failures
5. Update `CURRENT_STATE.md` only with behavior that was verified

---

## 📄 License

MIT License — see [`LICENSE`](LICENSE) for details.

---

<div align="center">
  <strong>Built with ❤️ for the AI-native founder</strong><br>
  <sub>CEO OS · Autonomous Enterprise AI · Powered by Gemini Live + OpenRouter</sub>
</div>
