"""Semantic and keyword search engine for agent persona discovery."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence

from agents.registry.contracts import AgentDefinition, AgentDivision, CandidateMatch


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric tokens."""
    tokens = re.findall(r"[a-z0-9_\-]+", text.lower())
    return [t for t in tokens if len(t) > 2 and not t.isdigit()]


class AgentSearchEngine:
    """TF-IDF and semantic candidate search engine over agent definitions."""

    def __init__(self, agents: Sequence[AgentDefinition]) -> None:
        self.agents = list(agents)
        self._doc_freqs: Counter[str] = Counter()
        self._doc_tokens: dict[str, Counter[str]] = {}
        self._doc_lengths: dict[str, int] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Construct inverted index and token statistics."""
        for agent in self.agents:
            doc_text = f"{agent.name} {agent.role} {agent.division.value} {agent.description} {' '.join(agent.tags)} {agent.instructions[:1500]}"
            tokens = _tokenize(doc_text)
            counts = Counter(tokens)
            self._doc_tokens[agent.id] = counts
            self._doc_lengths[agent.id] = max(1, len(tokens))
            for t in counts:
                self._doc_freqs[t] += 1

    def search(
        self,
        query: str,
        division: AgentDivision | None = None,
        limit: int = 10,
    ) -> list[CandidateMatch]:
        """Rank and return top candidate agents matching query."""
        if not self.agents:
            return []

        q_tokens = _tokenize(query)
        if not q_tokens:
            # Return top agents by division or default list
            filtered = [a for a in self.agents if division is None or a.division == division]
            return [
                CandidateMatch(
                    agent=a,
                    relevance_score=0.70,
                    match_reasons=["Default list"],
                    suggested_tools=list(a.default_tools),
                )
                for a in filtered[:limit]
            ]

        n_docs = max(1, len(self.agents))
        scored: list[tuple[float, AgentDefinition, list[str]]] = []

        for agent in self.agents:
            if division is not None and agent.division != division:
                continue

            score = 0.0
            reasons: list[str] = []
            agent_counts = self._doc_tokens.get(agent.id, Counter())
            doc_len = self._doc_lengths.get(agent.id, 1)

            # Direct name/role phrase matching
            q_lower = query.lower()
            if agent.name.lower() in q_lower or agent.role.lower() in q_lower:
                score += 5.0
                reasons.append(f"Direct role match: {agent.role}")

            # TF-IDF scoring over query tokens
            for qt in q_tokens:
                if qt in agent_counts:
                    tf = agent_counts[qt] / doc_len
                    idf = math.log(1 + (n_docs / (1 + self._doc_freqs[qt])))
                    token_score = tf * idf * 10.0

                    # Boost if token appears in name or tags
                    if qt in agent.name.lower():
                        token_score *= 2.5
                    elif any(qt in tag for tag in agent.tags):
                        token_score *= 1.8

                    score += token_score
                    reasons.append(f"Matched keyword '{qt}'")

            if score > 0.0:
                scored.append((score, agent, reasons))

        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            # Fallback
            fallback = self.agents[0]
            return [
                CandidateMatch(
                    agent=fallback,
                    relevance_score=0.50,
                    match_reasons=["General fallback"],
                    suggested_tools=list(fallback.default_tools),
                )
            ]

        max_raw = max(scored[0][0], 1.0)
        results: list[CandidateMatch] = []

        for raw_score, agent, reasons in scored[:limit]:
            norm_score = min(0.99, round(0.50 + (raw_score / (max_raw * 2.0)), 2))
            unique_reasons = list(dict.fromkeys(reasons))[:4]
            results.append(
                CandidateMatch(
                    agent=agent,
                    relevance_score=norm_score,
                    match_reasons=unique_reasons,
                    suggested_tools=list(agent.default_tools),
                )
            )

        return results
