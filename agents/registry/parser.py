"""Parser for Agency Agent markdown files (.md with YAML frontmatter)."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from agents.registry.contracts import (
    AgentDefinition,
    AgentDivision,
    AgentProviderSource,
    AgentScore,
)

logger = logging.getLogger(__name__)

# Keyword sets for automatic division mapping
_DIVISION_PATTERNS: dict[AgentDivision, set[str]] = {
    AgentDivision.ENGINEERING: {
        "developer",
        "architect",
        "backend",
        "frontend",
        "api",
        "database",
        "devops",
        "sre",
        "rust",
        "godot",
        "unity",
        "unreal",
        "webassembly",
        "desktop",
        "mobile",
        "git",
        "lsp",
        "cms",
        "wordpress",
        "drupal",
        "firmware",
        "embedded",
        "realtime",
        "mcp",
        "solidity",
        "blockchain",
        "fullstack",
        "software",
        "infrastructure",
        "refactoring",
    },
    AgentDivision.FINANCE: {
        "finops",
        "finance",
        "financial",
        "cfo",
        "fp-a",
        "cost",
        "spend",
        "bookkeeper",
        "pricing",
        "tax",
        "accounts-payable",
        "billing",
        "payments",
        "investment",
        "loan",
    },
    AgentDivision.MARKETING: {
        "marketing",
        "growth",
        "creative",
        "ad",
        "ads",
        "seo",
        "social",
        "tiktok",
        "douyin",
        "instagram",
        "youtube",
        "xiaohongshu",
        "weibo",
        "bilibili",
        "kuaishou",
        "wechat",
        "ppc",
        "meta",
        "attribution",
        "copywriter",
        "content",
        "outbound",
        "carousel",
    },
    AgentDivision.SALES: {
        "sales",
        "deal",
        "pipeline",
        "outbound",
        "outreach",
        "discovery",
        "proposal",
        "salesforce",
        "coach",
        "meddpicc",
        "qualification",
        "lead",
        "account-strategist",
    },
    AgentDivision.OPERATIONS: {
        "orchestrator",
        "project-manager",
        "project",
        "sprint",
        "jira",
        "operations",
        "chief-of-staff",
        "workflow",
        "studio",
        "hr",
        "recruitment",
        "onboarding",
        "change-management",
    },
    AgentDivision.PRODUCT: {
        "product-manager",
        "product",
        "feedback",
        "experiment",
        "pricing",
        "persona",
        "trend",
        "app-store",
    },
    AgentDivision.SECURITY: {
        "security",
        "appsec",
        "threat",
        "penetration",
        "soc2",
        "compliance",
        "auditor",
        "incident",
        "secops",
        "secrets",
        "blockchain-security",
        "fedramp",
        "privacy",
        "qa",
        "reality-checker",
        "evidence-collector",
    },
    AgentDivision.DESIGN: {
        "ui-designer",
        "ux-architect",
        "ux-researcher",
        "cartography",
        "3d-scene",
        "technical-artist",
        "level-designer",
        "blender",
        "avatar",
        "shader",
        "visuals",
    },
    AgentDivision.RESEARCH: {
        "researcher",
        "analyst",
        "statistician",
        "data-engineer",
        "spatial",
        "geoai",
        "ai-engineer",
        "market-navigator",
        "anthropologist",
        "historian",
        "psychologist",
    },
    AgentDivision.COMMUNICATIONS: {
        "technical-writer",
        "content-creator",
        "translator",
        "pr",
        "customer-service",
        "customer-success",
        "support",
        "community",
    },
}

# Default tool mappings for divisions
_DIVISION_DEFAULT_TOOLS: dict[AgentDivision, list[str]] = {
    AgentDivision.ENGINEERING: [
        "files.read",
        "files.write",
        "tools.shell",
        "memory.recall",
        "memory.remember",
    ],
    AgentDivision.FINANCE: [
        "business.finance.overview",
        "business.finance.invoices",
        "production.cost.overview",
        "memory.recall",
    ],
    AgentDivision.MARKETING: [
        "meta.ads.create",
        "marketing.snapshot.get",
        "browser.read",
        "comms.email.send",
        "memory.recall",
    ],
    AgentDivision.SALES: [
        "business.sales.deals",
        "business.sales.pipeline",
        "comms.email.send",
        "memory.recall",
    ],
    AgentDivision.OPERATIONS: ["tasks.list", "agents.spawn", "memory.recall", "memory.remember"],
    AgentDivision.PRODUCT: ["browser.read", "data.read", "memory.recall", "memory.remember"],
    AgentDivision.SECURITY: [
        "production.security.audit",
        "production.resilience.health",
        "production.confidence.verify",
        "memory.recall",
    ],
    AgentDivision.DESIGN: ["files.read", "files.write", "browser.read", "memory.recall"],
    AgentDivision.RESEARCH: [
        "web.search",
        "browser.read",
        "data.read",
        "memory.recall",
        "memory.remember",
    ],
    AgentDivision.COMMUNICATIONS: [
        "comms.email.send",
        "files.read",
        "files.write",
        "memory.recall",
    ],
    AgentDivision.GENERAL: ["memory.recall", "memory.remember"],
}


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter delimited by ---."""
    meta: dict[str, str] = {}
    body = content

    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        body = fm_match.group(2)
        for line in fm_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip().strip("'\"")

    return meta, body


def classify_division(name: str, description: str, content: str) -> AgentDivision:
    """Classify agent text into an AgentDivision."""
    text = f"{name} {description} {content[:1000]}".lower()

    scores: dict[AgentDivision, int] = {d: 0 for d in AgentDivision if d != AgentDivision.GENERAL}
    for div, keywords in _DIVISION_PATTERNS.items():
        for kw in keywords:
            if kw in text:
                scores[div] += 2 if kw in name.lower() else 1

    best_div, max_score = max(scores.items(), key=lambda x: x[1])
    return best_div if max_score > 0 else AgentDivision.GENERAL


def parse_agent_file(
    file_path: Path, source: AgentProviderSource = AgentProviderSource.AGENCY
) -> AgentDefinition | None:
    """Parse an agent markdown file into an AgentDefinition."""
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("Error reading agent file %s: %s", file_path, exc)
        return None

    meta, body = parse_frontmatter(raw_text)
    raw_id = meta.get("name") or file_path.parent.name
    agent_id = raw_id.lower().replace(" ", "-")

    # Nicely formatted display name
    name_clean = raw_id.replace("agency-", "").replace("-", " ").title()

    description = meta.get("description", "")
    division = classify_division(raw_id, description, body)

    # Role
    role_match = re.search(r"#\s+([^#\n]+)\s+(Personality|Agent)", body, re.IGNORECASE)
    role = role_match.group(1).strip() if role_match else name_clean

    # Tags
    tag_set = {agent_id, division.value}
    for word in agent_id.split("-"):
        if word and len(word) > 2 and word != "agency":
            tag_set.add(word)
    tags = sorted(tag_set)

    default_tools = list(_DIVISION_DEFAULT_TOOLS.get(division, ["memory.recall"]))

    return AgentDefinition(
        id=agent_id,
        name=name_clean,
        division=division,
        role=role,
        description=description,
        instructions=body,
        source=source,
        tags=tags,
        default_tools=default_tools,
        allowed_capabilities=default_tools,
        model_class="coding" if division == AgentDivision.ENGINEERING else "medium_reasoning",
        file_path=str(file_path),
        score=AgentScore(),
    )
