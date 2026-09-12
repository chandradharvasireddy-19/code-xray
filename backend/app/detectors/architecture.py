"""Detect architecture layer violations (e.g., controller -> repository bypassing service)."""
from typing import Any, Dict, List, Optional, Set, Tuple
from app.models.repository import Relationship, RepositoryModel
from app.models.finding import ForensicFinding, FindingType
from app.models.evidence import EvidenceItem, EvidenceType
from app.analyzer.docs import DocumentedRule
from app.evidence.confidence import ConfidenceEngine
import uuid


class ArchitectureDetector:
    """
    Enforces layered architecture rules by examining import relationships
    between files that belong to different architectural layers.

    Default rule: controller -> service -> repository
    Controllers must NOT directly import/call repositories.
    """

    # Default layer classification by directory/filename patterns
    LAYER_PATTERNS = {
        "controller": ["controller", "handler", "endpoint", "route", "view", "api"],
        "service": ["service", "manager", "usecase", "interactor", "logic"],
        "repository": ["repository", "repo", "dal", "dao", "store", "database", "db"],
        "model": ["model", "entity", "schema", "dto"],
        "util": ["util", "helper", "common", "shared", "lib"],
    }

    # Default allowed flows (index order matters)
    DEFAULT_LAYER_ORDER = ["controller", "service", "repository"]

    def __init__(self, repo: RepositoryModel, rules: List[DocumentedRule]):
        self.repo = repo
        self.rules = rules
        self.relationships = repo.relationships

    def detect(self) -> List[ForensicFinding]:
        findings: List[ForensicFinding] = []

        # Build file -> layer mapping
        file_layers: Dict[str, str] = {}
        for f in self.repo.files:
            layer = self._classify_layer(f)
            if layer:
                file_layers[f] = layer

        # Get allowed flows from rules
        allowed_flows = self._get_allowed_flows()

        # Check all import relationships for violations
        for rel in self.relationships:
            if rel.type != "imports":
                continue

            src_layer = file_layers.get(rel.source)
            tgt_layer = file_layers.get(rel.target)

            if not src_layer or not tgt_layer:
                continue
            if src_layer == tgt_layer:
                continue

            # Check if this is a violation
            if self._is_violation(src_layer, tgt_layer, allowed_flows):
                confidence = ConfidenceEngine.calculate_score(0.85)

                evidence_items = [
                    EvidenceItem(
                        type=EvidenceType.ARCHITECTURE.value,
                        source=rel.source,
                        location=rel.source,
                        line=rel.line,
                        description=f"'{rel.source}' ({src_layer} layer) imports '{rel.target}' ({tgt_layer} layer)",
                        confidence=0.90,
                        relationship="violates_layer_rule",
                        metadata={
                            "source_layer": src_layer,
                            "target_layer": tgt_layer,
                            "import_detail": rel.detail or "",
                        },
                    ),
                    EvidenceItem(
                        type=EvidenceType.ARCHITECTURE.value,
                        source="architecture_rule",
                        description=f"Expected flow: {' -> '.join(self.DEFAULT_LAYER_ORDER)}. "
                                    f"{src_layer} should not directly access {tgt_layer}.",
                        confidence=0.90,
                        relationship="expected_architecture",
                    ),
                ]

                # Add documentation evidence if rule came from docs
                for rule in self.rules:
                    if rule.source_doc != "default_architecture_policy":
                        evidence_items.append(EvidenceItem(
                            type=EvidenceType.DOCUMENTATION.value,
                            source=rule.source_doc,
                            location=rule.source_doc,
                            description=f"Documented rule: {rule.rule_text}",
                            confidence=0.90,
                            relationship="documented_constraint",
                        ))
                        break

                findings.append(ForensicFinding(
                    finding_id=f"arch-{uuid.uuid4().hex[:8]}",
                    repository_id=self.repo.repository_id,
                    finding_type=FindingType.ARCHITECTURE_DRIFT.value,
                    title=f"Architecture violation: {src_layer} -> {tgt_layer}",
                    affected_file=rel.source,
                    affected_symbol=None,
                    line_number=rel.line,
                    severity="medium",
                    confidence=confidence,
                    confidence_level=ConfidenceEngine.get_level(confidence),
                    description=(
                        f"File '{rel.source}' (classified as {src_layer}) directly imports "
                        f"'{rel.target}' (classified as {tgt_layer}), bypassing the expected "
                        f"service layer. Expected architecture: {' -> '.join(self.DEFAULT_LAYER_ORDER)}."
                    ),
                    evidence=f"{src_layer} -> {tgt_layer} violates expected {' -> '.join(self.DEFAULT_LAYER_ORDER)} flow",
                    evidence_chain=evidence_items,
                ))

        return findings

    def _classify_layer(self, file_path: str) -> Optional[str]:
        lower = file_path.lower().replace("\\", "/")
        parts = lower.split("/")

        for layer_name, patterns in self.LAYER_PATTERNS.items():
            for pattern in patterns:
                # Check directory names
                if any(pattern in part for part in parts[:-1]):
                    return layer_name
                # Check filename
                filename = parts[-1] if parts else ""
                if pattern in filename:
                    return layer_name
        return None

    def _get_allowed_flows(self) -> List[Tuple[str, str]]:
        """Return list of (source_layer, target_layer) tuples that are allowed."""
        allowed: List[Tuple[str, str]] = []

        for rule in self.rules:
            if rule.allowed_flow and len(rule.allowed_flow) >= 2:
                for i in range(len(rule.allowed_flow) - 1):
                    allowed.append((rule.allowed_flow[i], rule.allowed_flow[i + 1]))

        # Default fallback
        if not allowed:
            allowed = [
                ("controller", "service"),
                ("service", "repository"),
            ]

        return allowed

    def _is_violation(self, src_layer: str, tgt_layer: str, allowed_flows: List[Tuple[str, str]]) -> bool:
        # Any layer can import models and utils
        if tgt_layer in ("model", "util"):
            return False

        # Check if this specific flow is allowed
        if (src_layer, tgt_layer) in allowed_flows:
            return False

        # Check if src_layer is higher than tgt_layer in default ordering
        # and would skip an intermediate layer
        try:
            src_idx = self.DEFAULT_LAYER_ORDER.index(src_layer)
            tgt_idx = self.DEFAULT_LAYER_ORDER.index(tgt_layer)
        except ValueError:
            return False

        # Violation if skipping layers (e.g., controller -> repository)
        if tgt_idx - src_idx > 1:
            return True

        # Violation if going backwards (e.g., repository -> controller)
        if tgt_idx < src_idx:
            return True

        return False
