# Milestone 22: Agency Agents Ecosystem Deep Integration

## Acceptance Criteria

1. **270+ Agency Agent Skills Discovery & Parsing**:
   - Dynamic discovery, parsing, indexing, and domain classification of all 270 installed Agency Agent skills from `/Users/abdullahansari07/.gemini/config/skills/` (and `.agents/skills/`).
   - Deep structured extraction of persona identity, domain classification (`AgencyDomain`), core missions, critical rules, workflow phases, and allowed capabilities.

2. **Automatic Skill Matching (`AgencySkillMatcher`)**:
   - Semantic and keyword matching of user intent, tasks, and prompts against all 270 agency agent personas.
   - High-precision scoring ($0.0 \dots 1.0$) with domain and specialty cue boosting to match tasks to optimal specialist personas (e.g., FinOps, AppSec, Meta Ads, B2B MEDDPICC Deal Strategy, etc.).

3. **Dynamic Agent Template Synthesis & Registration**:
   - `AgencyAgentsEngine.register_all_templates` dynamically synthesizes and registers all 270 agency agent templates into `AgentTemplateRegistry` and `AgentRuntime` with appropriate capabilities, model classes, and execution budgets.

4. **Agency Capability Tools**:
   - Register 5 typed capability tools:
     - `agency.skills.list`: List available Agency Agent skills with domain and tag filters.
     - `agency.skills.get`: Retrieve complete persona instructions, critical rules, and workflow phases.
     - `agency.skills.match`: Match tasks/prompts to optimal agency agent personas with relevance rankings.
     - `agency.agent.spawn`: Synthesize and register an agent template configured with an agency persona.
     - `agency.task.execute`: Execute tasks guided by matched agency persona rules, workflow phases, and quality gates.

5. **REST API Endpoints**:
   - `GET /api/v1/agency/skills`: List skills with domain and tag filtering.
   - `GET /api/v1/agency/skills/{skill_name}`: Retrieve skill persona details.
   - `POST /api/v1/agency/match`: Match task query to agency agents.
   - `POST /api/v1/agency/spawn`: Dynamically instantiate and register an agent template.
   - `POST /api/v1/agency/execute`: Execute a task with matched agency persona guidance.

6. **Planner & Execution Acceptance**:
   - CEO OS planner automatically recognizes agency intent, binds matched agency agent personas into execution plans, enforces quality gates, collects evidence, and executes successfully.

## Verification Evidence

- `uv run pytest -v tests/test_agency_agents.py`: 8 / 8 passed.
- `uv run pytest -v`: 165 / 165 passed across the entire suite.
- `uv run ruff check .`: 0 errors.
- `uv run mypy agency apps/api/src/ceo_os_api/schemas.py apps/api/src/ceo_os_api/planner.py`: 0 errors across 9 source files.
- `npm --prefix apps/dashboard run test && npm --prefix apps/dashboard run lint && npm --prefix apps/dashboard run build`: All passed.
- `make check`: 100% passed.
