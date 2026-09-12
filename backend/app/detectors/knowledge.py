"""Detect knowledge concentration risks from Git history."""
from typing import Any, Dict, List, Optional
from app.models.repository import RepositoryModel
from app.models.finding import ForensicFinding, FindingType
from app.models.evidence import EvidenceItem, EvidenceType
from app.evidence.confidence import ConfidenceEngine
import uuid


class KnowledgeConcentrationDetector:
    """
    Identifies components where knowledge is concentrated in very few contributors,
    creating a bus-factor risk. Uses Git history file statistics.
    """

    OWNERSHIP_THRESHOLD = 0.80  # Single contributor owns >= 80% of commits
    MIN_COMMITS_RELEVANCE = 3   # File must have at least 3 commits to be relevant

    def __init__(self, repo: RepositoryModel, git_file_stats: Dict[str, Dict[str, Any]]):
        self.repo = repo
        self.git_file_stats = git_file_stats

    def detect(self) -> List[ForensicFinding]:
        findings: List[ForensicFinding] = []

        for file_path, stats in self.git_file_stats.items():
            # Only check source files
            if file_path not in self.repo.source_files:
                continue

            total_commits = stats.get("total_commits", 0)
            if total_commits < self.MIN_COMMITS_RELEVANCE:
                continue

            contributor_count = stats.get("contributor_count", 0)
            primary = stats.get("primary_contributor", "unknown")
            ownership = stats.get("top_contributor_ownership", 0.0)

            if contributor_count <= 1 and total_commits >= 5:
                # Single contributor with many commits
                confidence = ConfidenceEngine.calculate_score(0.80)
                evidence_items = [
                    EvidenceItem(
                        type=EvidenceType.GIT.value,
                        source=file_path,
                        location=file_path,
                        description=(
                            f"File '{file_path}' has {total_commits} commits by a single contributor '{primary}'. "
                            f"No other contributor has ever modified this file."
                        ),
                        confidence=0.85,
                        relationship="git_ownership",
                        metadata={
                            "total_commits": total_commits,
                            "contributor_count": contributor_count,
                            "primary_contributor": primary,
                            "ownership_pct": ownership,
                        },
                    )
                ]

                findings.append(ForensicFinding(
                    finding_id=f"knowledge-{uuid.uuid4().hex[:8]}",
                    repository_id=self.repo.repository_id,
                    finding_type=FindingType.KNOWLEDGE_CONCENTRATION.value,
                    title=f"Knowledge concentration: {file_path}",
                    affected_file=file_path,
                    severity="medium",
                    confidence=confidence,
                    confidence_level=ConfidenceEngine.get_level(confidence),
                    description=(
                        f"File '{file_path}' has been modified {total_commits} times by only one contributor "
                        f"('{primary}'). This creates a single point of knowledge failure."
                    ),
                    evidence=f"Single contributor ({primary}) owns 100% of {total_commits} commits",
                    evidence_chain=evidence_items,
                ))

            elif ownership >= self.OWNERSHIP_THRESHOLD and contributor_count >= 2:
                # Dominant contributor
                confidence = ConfidenceEngine.calculate_score(0.70)
                evidence_items = [
                    EvidenceItem(
                        type=EvidenceType.GIT.value,
                        source=file_path,
                        location=file_path,
                        description=(
                            f"File '{file_path}' has {total_commits} commits across {contributor_count} contributors, "
                            f"but '{primary}' owns {int(ownership * 100)}% of changes."
                        ),
                        confidence=0.80,
                        relationship="git_ownership",
                        metadata={
                            "total_commits": total_commits,
                            "contributor_count": contributor_count,
                            "primary_contributor": primary,
                            "ownership_pct": ownership,
                        },
                    )
                ]

                findings.append(ForensicFinding(
                    finding_id=f"knowledge-{uuid.uuid4().hex[:8]}",
                    repository_id=self.repo.repository_id,
                    finding_type=FindingType.KNOWLEDGE_CONCENTRATION.value,
                    title=f"Dominant contributor: {file_path}",
                    affected_file=file_path,
                    severity="low",
                    confidence=confidence,
                    confidence_level=ConfidenceEngine.get_level(confidence),
                    description=(
                        f"File '{file_path}' has {contributor_count} contributors, but '{primary}' "
                        f"has authored {int(ownership * 100)}% of the {total_commits} commits. "
                        f"Knowledge may be concentrated."
                    ),
                    evidence=f"Dominant contributor '{primary}' owns {int(ownership * 100)}% of {total_commits} commits",
                    evidence_chain=evidence_items,
                ))

        return findings
