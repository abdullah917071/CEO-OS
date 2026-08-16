from __future__ import annotations

import builtins
import logging
import re
from pathlib import Path

from agency.contracts import AgencyDomain, AgencySkillPersona

logger = logging.getLogger(__name__)

# Domain keyword mappings for robust classification
_DOMAIN_KEYWORDS: dict[AgencyDomain, set[str]] = {
    AgencyDomain.ENGINEERING: {
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
    },
    AgencyDomain.FINOPS_FINANCE: {
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
    },
    AgencyDomain.MARKETING_GROWTH: {
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
        "content",
        "copywriting",
    },
    AgencyDomain.SALES_DEAL: {
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
    },
    AgencyDomain.OPERATIONS_PM: {
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
        "onboarding",
        "change-management",
    },
    AgencyDomain.SECURITY_QA: {
        "security",
        "secops",
        "appsec",
        "penetration",
        "compliance",
        "threat",
        "incident",
        "evidence",
        "reality-checker",
        "qa",
        "tester",
        "audit",
        "privacy",
        "fedramp",
        "soc",
    },
    AgencyDomain.GEOSPATIAL_3D: {
        "gis",
        "spatial",
        "3d",
        "drone",
        "cartography",
        "geoprocessing",
        "geoai",
        "geographer",
        "blender",
        "cesium",
        "arcgis",
        "reality-mapping",
        "bim",
        "visionos",
        "metal",
    },
    AgencyDomain.CREATIVE_CONTENT: {
        "writer",
        "storyteller",
        "narrative",
        "book",
        "author",
        "podcast",
        "whimsy",
        "visuals",
        "prompt",
        "video",
    },
}


def _classify_domain(name: str, description: str, content: str) -> AgencyDomain:
    """Classify an agency skill into a canonical AgencyDomain."""
    text = f"{name} {description} {content[:1000]}".lower()

    scores: dict[AgencyDomain, int] = {d: 0 for d in AgencyDomain if d != AgencyDomain.GENERAL}
    for domain, kws in _DOMAIN_KEYWORDS.items():
        for kw in kws:
            if kw in text:
                scores[domain] += 2 if kw in name else 1

    best_domain = max(scores.items(), key=lambda x: x[1])
    if best_domain[1] > 0:
        return best_domain[0]
    return AgencyDomain.GENERAL


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML-style frontmatter delimited by ---."""
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


def _extract_bullets_under_heading(content: str, heading_pattern: str) -> list[str]:
    """Extract bullet points under a specific markdown heading."""
    bullets: list[str] = []
    lines = content.splitlines()
    in_section = False

    for line in lines:
        line_clean = line.strip()
        if re.match(rf"^#+\s+.*{heading_pattern}.*", line_clean, re.IGNORECASE):
            in_section = True
            continue
        elif in_section and re.match(r"^#+\s+", line_clean):
            # Next heading reached
            break

        if in_section:
            bullet_match = re.match(r"^[-*•]\s+(.*)$", line_clean)
            if bullet_match:
                bullets.append(bullet_match.group(1).strip())
            elif line_clean and not line_clean.startswith("#"):
                # Non-empty plain line in section
                if len(bullets) < 5 and len(line_clean) > 5:
                    bullets.append(line_clean)

    return bullets


def parse_skill_markdown(file_path: Path) -> AgencySkillPersona | None:
    """Parse an agency SKILL.md file into an AgencySkillPersona."""
    try:
        raw = file_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to read skill file %s: %exc", file_path, exc)
        return None

    meta, body = _parse_frontmatter(raw)
    skill_name = meta.get("name", file_path.parent.name)
    description = meta.get("description", "")

    # Role extraction
    role_match = re.search(r"#\s+([^#\n]+)\s+Personality", body, re.IGNORECASE)
    if role_match:
        role = role_match.group(1).strip()
    else:
        role = skill_name.replace("agency-", "").replace("-", " ").title()

    domain = _classify_domain(skill_name, description, body)

    # Extract tags
    tag_set = {
        skill_name.replace("agency-", "").lower(),
        domain.value,
    }
    for word in skill_name.split("-"):
        if word and word != "agency" and len(word) > 2:
            tag_set.add(word)
    tags = sorted(tag_set)

    # Extract sections
    mission_bullets = _extract_bullets_under_heading(
        body, r"(Mission|Core Mission|Responsibilities)"
    )
    rules_bullets = _extract_bullets_under_heading(
        body, r"(Rules|Critical Rules|Guardrails|Standards)"
    )
    phases_bullets = _extract_bullets_under_heading(body, r"(Phases|Workflow|Steps)")

    # Allowed capability inference based on domain
    caps = ["files.read", "memory.recall"]
    if domain in {AgencyDomain.ENGINEERING, AgencyDomain.OPERATIONS_PM}:
        caps.extend(["files.write", "tools.shell", "memory.remember"])
    elif domain == AgencyDomain.MARKETING_GROWTH:
        caps.extend(["meta.ads.create", "marketing.snapshot.get", "comms.email.send"])
    elif domain == AgencyDomain.FINOPS_FINANCE:
        caps.extend(
            ["business.finance.invoices", "business.finance.overview", "production.cost.overview"]
        )
    elif domain == AgencyDomain.SALES_DEAL:
        caps.extend(["business.sales.deals", "business.sales.pipeline", "comms.email.send"])
    elif domain == AgencyDomain.SECURITY_QA:
        caps.extend(
            [
                "production.security.audit",
                "production.resilience.health",
                "production.confidence.verify",
            ]
        )

    return AgencySkillPersona(
        name=skill_name,
        description=description,
        role=role,
        domain=domain,
        tags=tags,
        personality=f"Autonomous specialist in {role}",
        core_mission=mission_bullets[:10],
        critical_rules=rules_bullets[:10],
        workflow_phases=phases_bullets[:10],
        allowed_capabilities=caps,
        raw_content=raw,
        file_path=str(file_path),
    )


class AgencyCatalog:
    """High-performance catalog and indexer of Agency Agent skills."""

    def __init__(self, search_paths: list[str | Path] | None = None) -> None:
        self._search_paths: list[Path] = []
        if search_paths:
            self._search_paths.extend([Path(p).expanduser().resolve() for p in search_paths])
        else:
            # Default lookup paths
            p1 = Path("~/.gemini/config/skills").expanduser().resolve()
            p2 = Path(".agents/skills").resolve()
            if p1.exists():
                self._search_paths.append(p1)
            if p2.exists():
                self._search_paths.append(p2)

        self._skills: dict[str, AgencySkillPersona] = {}
        self.reload()

    def reload(self) -> int:
        """Scan directories and load all available agency skills."""
        self._skills.clear()
        found_count = 0

        for base_dir in self._search_paths:
            if not base_dir.exists() or not base_dir.is_dir():
                continue

            for skill_dir in base_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    persona = parse_skill_markdown(skill_file)
                    if persona:
                        self._skills[persona.name] = persona
                        found_count += 1

        logger.info("AgencyCatalog loaded %d skills from %s", found_count, self._search_paths)
        return found_count

    def get(self, name: str) -> AgencySkillPersona | None:
        """Retrieve a specific agency skill persona by name."""
        clean_name = name.strip().lower()
        if not clean_name.startswith("agency-") and f"agency-{clean_name}" in self._skills:
            return self._skills[f"agency-{clean_name}"]
        return self._skills.get(clean_name)

    def list(
        self,
        domain: AgencyDomain | str | None = None,
        tag: str | None = None,
    ) -> builtins.list[AgencySkillPersona]:
        """List skills matching domain or tag criteria."""
        results: builtins.list[AgencySkillPersona] = [s for s in self._skills.values()]
        if domain:
            dom_val = domain.value if isinstance(domain, AgencyDomain) else str(domain).lower()
            results = [s for s in results if s.domain.value == dom_val]
        if tag:
            tag_clean = tag.strip().lower()
            results = [s for s in results if tag_clean in s.tags]
        return sorted(results, key=lambda s: s.name)

    list_skills = list

    def search(self, query: str) -> builtins.list[AgencySkillPersona]:
        """Simple substring search across names, roles, and descriptions."""
        q = query.strip().lower()
        if not q:
            return self.list()
        return [
            s
            for s in self._skills.values()
            if q in s.name.lower() or q in s.description.lower() or q in s.role.lower()
        ]

    def count(self) -> int:
        """Return total number of indexed skills."""
        return len(self._skills)
