from __future__ import annotations

import logging
import re

from agency.catalog import AgencyCatalog
from agency.contracts import AgencyMatchResult, AgencySkillPersona, SkillMatchScore

logger = logging.getLogger(__name__)

# Specialized domain intent cues
_SPECIALTY_CUES: dict[str, list[str]] = {
    "agency-finops-engineer": [
        "aws",
        "cloud cost",
        "finops",
        "unit economics",
        "spend",
        "rightsizer",
        "tagging",
    ],
    "agency-ad-creative-strategist": [
        "ad",
        "creative",
        "rsa",
        "asset group",
        "meta ad",
        "copywriting",
        "cpa",
    ],
    "agency-deal-strategist": [
        "meddpicc",
        "deal",
        "pipeline",
        "qualification",
        "b2b sales",
        "forecast review",
    ],
    "agency-agents-orchestrator": [
        "orchestrate",
        "pipeline",
        "full workflow",
        "lead process",
        "dev-qa loop",
    ],
    "agency-application-security-engineer": [
        "appsec",
        "threat model",
        "secure code",
        "sast",
        "dast",
        "security audit",
    ],
    "agency-senior-developer": [
        "build feature",
        "implement",
        "coding",
        "css",
        "three.js",
        "laravel",
        "livewire",
    ],
    "agency-backend-architect": [
        "system design",
        "database schema",
        "api design",
        "microservices",
        "server architecture",
    ],
    "agency-frontend-developer": [
        "ui implementation",
        "react",
        "vue",
        "frontend",
        "responsive design",
    ],
    "agency-evidence-collector": [
        "qa validation",
        "evidence",
        "screenshot",
        "test proof",
        "find issues",
    ],
    "agency-reality-checker": [
        "reality check",
        "production readiness",
        "rigorous audit",
        "needs work",
    ],
    "agency-sales-coach": ["sales coaching", "rep development", "call coaching", "deal strategy"],
    "agency-growth-hacker": ["growth", "viral loop", "user acquisition", "conversion funnel"],
    "agency-seo-specialist": [
        "seo",
        "organic search",
        "technical seo",
        "backlinks",
        "keyword ranking",
    ],
}


def _tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase alphanumeric tokens."""
    tokens = re.findall(r"[a-z0-9_\-]+", text.lower())
    return {t for t in tokens if len(t) > 2 and not t.isdigit()}


class AgencySkillMatcher:
    """Intelligent matcher mapping task intent to the optimal Agency Agent persona."""

    def __init__(self, catalog: AgencyCatalog) -> None:
        self.catalog = catalog

    def match(self, query: str, top_k: int = 3) -> AgencyMatchResult:
        """Score and rank all indexed skills against query."""
        all_skills = self.catalog.list()
        if not all_skills:
            return AgencyMatchResult(
                query=query,
                matches=[],
                best_match=None,
                total_skills_evaluated=0,
            )

        q_lower = query.strip().lower()
        q_tokens = _tokenize(query)

        scored: list[tuple[float, AgencySkillPersona, list[str], str]] = []

        for skill in all_skills:
            score = 0.0
            matched_kws: list[str] = []

            # 1. Specialty cue direct boost
            if skill.name in _SPECIALTY_CUES:
                for cue in _SPECIALTY_CUES[skill.name]:
                    if cue in q_lower:
                        score += 5.0
                        matched_kws.append(cue)

            # 2. Skill Name tokens
            name_tokens = _tokenize(skill.name)
            name_overlap = q_tokens.intersection(name_tokens)
            if name_overlap:
                score += len(name_overlap) * 3.0
                matched_kws.extend(sorted(name_overlap))

            # 3. Role tokens
            role_tokens = _tokenize(skill.role)
            role_overlap = q_tokens.intersection(role_tokens)
            if role_overlap:
                score += len(role_overlap) * 2.0
                matched_kws.extend(sorted(role_overlap))

            # 4. Description tokens
            desc_tokens = _tokenize(skill.description)
            desc_overlap = q_tokens.intersection(desc_tokens)
            if desc_overlap:
                score += len(desc_overlap) * 1.5
                matched_kws.extend(sorted(desc_overlap))

            # 5. Tags overlap
            tag_overlap = q_tokens.intersection(set(skill.tags))
            if tag_overlap:
                score += len(tag_overlap) * 2.0
                matched_kws.extend(sorted(tag_overlap))

            if score > 0.0:
                # Deduplicate matched keywords
                unique_kws = list(dict.fromkeys(matched_kws))
                rationale = (
                    f"Matched {len(unique_kws)} signals ({', '.join(unique_kws[:3])}) "
                    f"aligned with {skill.role} in {skill.domain.value}."
                )
                scored.append((score, skill, unique_kws, rationale))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            # Fallback to general orchestrator
            default_skill = self.catalog.get("agency-agents-orchestrator") or all_skills[0]
            matches = [
                SkillMatchScore(
                    skill_name=default_skill.name,
                    domain=default_skill.domain,
                    relevance_score=0.50,
                    matched_keywords=["general_fallback"],
                    rationale=f"Default general delegation to {default_skill.role}.",
                )
            ]
        else:
            max_score = max(scored[0][0], 1.0)
            matches = []
            for raw_score, skill, kws, rationale in scored[:top_k]:
                # Normalized confidence score between 0.50 and 0.99
                norm_score = min(0.99, round(0.50 + (raw_score / (max_score * 2.0)), 2))
                matches.append(
                    SkillMatchScore(
                        skill_name=skill.name,
                        domain=skill.domain,
                        relevance_score=norm_score,
                        matched_keywords=kws,
                        rationale=rationale,
                    )
                )

        best_match = matches[0] if matches else None
        return AgencyMatchResult(
            query=query,
            matches=matches,
            best_match=best_match,
            total_skills_evaluated=len(all_skills),
        )
