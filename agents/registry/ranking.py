"""Multi-factor ranking and candidate scoring model for agent selection."""

from __future__ import annotations

from agents.registry.contracts import CandidateMatch


class AgentRanker:
    """Combines semantic match with historical performance and cost to produce final candidate rankings."""

    def __init__(
        self,
        weight_relevance: float = 0.55,
        weight_historical_success: float = 0.20,
        weight_confidence: float = 0.10,
        weight_owner_rating: float = 0.10,
        weight_cost_efficiency: float = 0.05,
    ) -> None:
        self.w_rel = weight_relevance
        self.w_succ = weight_historical_success
        self.w_conf = weight_confidence
        self.w_rate = weight_owner_rating
        self.w_cost = weight_cost_efficiency

    def rank(self, candidates: list[CandidateMatch], limit: int = 5) -> list[CandidateMatch]:
        """Apply multi-factor scoring formula to candidate list."""
        if not candidates:
            return []

        scored_candidates: list[tuple[float, CandidateMatch]] = []

        for c in candidates:
            agent = c.agent
            score_meta = agent.score

            # 1. Semantic relevance (0.50 to 0.99)
            rel_factor = c.relevance_score

            # 2. Historical success rate (0.0 to 1.0)
            succ_factor = score_meta.success_rate

            # 3. Average confidence (0.0 to 1.0)
            conf_factor = score_meta.average_confidence

            # 4. Owner rating (1.0 to 5.0 normalized to 0.2 to 1.0)
            rate_factor = min(1.0, max(0.2, score_meta.owner_rating / 5.0))

            # 5. Cost efficiency (lower cost -> higher score)
            cost_factor = 1.0 / (1.0 + (score_meta.average_cost / 10.0))

            composite = (
                (self.w_rel * rel_factor)
                + (self.w_succ * succ_factor)
                + (self.w_conf * conf_factor)
                + (self.w_rate * rate_factor)
                + (self.w_cost * cost_factor)
            )

            # Round composite score
            final_score = min(0.99, round(composite, 3))
            c.relevance_score = final_score
            scored_candidates.append((final_score, c))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_candidates[:limit]]
