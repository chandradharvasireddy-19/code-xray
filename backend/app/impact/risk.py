"""Deterministic and transparent heuristic risk engine for change impact analysis."""
from typing import Any, Dict, List, Optional, Set
from app.models.impact import AffectedEntity, RiskFactor, RiskReport, RiskLevel
from app.models.repository import RepositoryModel


class RiskEngine:
    """
    Computes a deterministic, explainable risk score (0-100) and risk level
    (LOW, MEDIUM, HIGH, CRITICAL) for a set of proposed code changes based on:
    - Scope of affected entities
    - Call graph depth and dependency fan-in / fan-out
    - Test coverage weakness
    - Architecture drift / layer violations
    - Git churn and recent modification frequency
    - Knowledge concentration (bus-factor risk)
    """

    def __init__(
        self,
        affected_entities: List[AffectedEntity],
        relationships: List[Dict[str, Any]],
        tests: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        historical: List[Dict[str, Any]],
        repo: Optional[RepositoryModel] = None,
    ):
        self.affected_entities = affected_entities
        self.relationships = relationships
        self.tests = tests
        self.findings = findings
        self.historical = historical
        self.repo = repo

    def calculate(self) -> RiskReport:
        factors: List[RiskFactor] = []
        raw_score = 15  # Baseline minimal change risk
        factors.append(RiskFactor(
            name="Baseline Modification Risk",
            score=15,
            explanation="Inherent baseline risk associated with modifying production code paths.",
        ))

        # 1. Affected Entity Count Factor
        count = len(self.affected_entities)
        if count >= 10:
            score = 25
            factors.append(RiskFactor(
                name="Broad Scope",
                score=score,
                explanation=f"Modifying this flow touches {count} distinct code entities across multiple modules.",
            ))
            raw_score += score
        elif count >= 4:
            score = 15
            factors.append(RiskFactor(
                name="Multi-Component Scope",
                score=score,
                explanation=f"Change impacts {count} code entities across dependent modules.",
            ))
            raw_score += score

        # 2. Call Graph Depth & Upstream Fan-In
        max_depth = max([ae.depth for ae in self.affected_entities], default=0)
        upstream_count = sum(1 for r in self.relationships if r.get("type") in ["CALLS", "IMPORTS"])
        if max_depth >= 2 or upstream_count >= 5:
            score = 18
            factors.append(RiskFactor(
                name="Deep Dependency Chain",
                score=score,
                explanation=(
                    f"Impact traverses {max_depth} levels deep with {upstream_count} dependent caller/callee relationships."
                ),
            ))
            raw_score += score

        # 3. Test Coverage Weakness
        tested_sources = set(t.get("tests_for") for t in self.tests if t.get("tests_for"))
        affected_files = set(ae.file for ae in self.affected_entities)
        untested_affected = [f for f in affected_files if f not in tested_sources]

        if untested_affected:
            score = 20 if len(untested_affected) > 2 else 12
            factors.append(RiskFactor(
                name="Test Coverage Gap",
                score=score,
                explanation=(
                    f"{len(untested_affected)} affected file(s) lack detected unit tests: "
                    f"{', '.join(untested_affected[:3])}{'...' if len(untested_affected) > 3 else ''}."
                ),
            ))
            raw_score += score

        # 4. Architecture Drift / Violations
        arch_findings = [f for f in self.findings if "architecture" in str(f.get("type", "")).lower()]
        if arch_findings:
            score = 20
            factors.append(RiskFactor(
                name="Architectural Drift",
                score=score,
                explanation=(
                    f"Impacted path contains {len(arch_findings)} architectural layer violation(s), "
                    f"increasing coupling and regression hazards."
                ),
            ))
            raw_score += score

        # 5. Git Churn & Volatility
        high_churn_files = [h for h in self.historical if h.get("total_commits", 0) >= 8 or h.get("recent_commits", 0) >= 3]
        if high_churn_files:
            score = 12
            factors.append(RiskFactor(
                name="High Historical Churn",
                score=score,
                explanation=(
                    f"{len(high_churn_files)} affected file(s) have experienced frequent modifications and high churn."
                ),
            ))
            raw_score += score

        # 6. Knowledge Concentration
        single_author_files = [
            h for h in self.historical
            if h.get("contributor_count", 0) == 1 and h.get("total_commits", 0) >= 3
        ]
        if single_author_files:
            score = 12
            primary = single_author_files[0].get("primary_contributor", "unknown")
            factors.append(RiskFactor(
                name="Knowledge Concentration",
                score=score,
                explanation=(
                    f"Core affected components rely heavily on a single primary author ('{primary}')."
                ),
            ))
            raw_score += score

        # Clamp score between 0 and 100
        final_score = max(5, min(100, raw_score))

        # Determine level
        if final_score >= 75:
            level = RiskLevel.CRITICAL.value
        elif final_score >= 50:
            level = RiskLevel.HIGH.value
        elif final_score >= 25:
            level = RiskLevel.MEDIUM.value
        else:
            level = RiskLevel.LOW.value

        summary = (
            f"Risk is {level} ({final_score}/100) driven by {len(factors)} identified factor(s) "
            f"across {len(self.affected_entities)} affected entities."
        )

        return RiskReport(
            risk_score=final_score,
            risk_level=level,
            factors=factors,
            summary=summary,
        )
