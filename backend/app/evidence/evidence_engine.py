from typing import Any, Dict, List, Optional
from app.models.evidence import EvidenceItem, EvidenceType, ConfidenceLevel
from app.evidence.confidence import ConfidenceEngine


class EvidenceEngine:
    """
    Constructs, normalizes, and aggregates multi-source evidence items
    (AST, dependencies, call graph, architecture rules, Git history, documentation).
    """

    @staticmethod
    def create_ast_evidence(
        file: str,
        line: Optional[int],
        detail: str,
        confidence: float = 0.90,
        relationship: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceItem:
        return EvidenceItem(
            type=EvidenceType.AST.value,
            source=file,
            location=file,
            line=line,
            description=detail,
            confidence=confidence,
            relationship=relationship,
            metadata=metadata or {},
        )

    @staticmethod
    def create_dependency_evidence(
        source_file: str,
        target: str,
        line: Optional[int],
        detail: str,
        confidence: float = 0.90,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceItem:
        return EvidenceItem(
            type=EvidenceType.DEPENDENCY.value,
            source=source_file,
            location=source_file,
            line=line,
            description=detail,
            confidence=confidence,
            relationship=f"imports {target}",
            metadata=metadata or {},
        )

    @staticmethod
    def create_call_graph_evidence(
        caller: str,
        callee: str,
        line: Optional[int],
        detail: str,
        confidence: float = 0.85,
    ) -> EvidenceItem:
        return EvidenceItem(
            type=EvidenceType.CALL_GRAPH.value,
            source=caller,
            location=caller,
            line=line,
            description=detail,
            confidence=confidence,
            relationship=f"invokes {callee}",
        )

    @staticmethod
    def create_architecture_evidence(
        rule_name: str,
        source_layer: str,
        target_layer: str,
        detail: str,
        confidence: float = 0.95,
    ) -> EvidenceItem:
        return EvidenceItem(
            type=EvidenceType.ARCHITECTURE.value,
            source=rule_name,
            location=f"{source_layer} -> {target_layer}",
            description=detail,
            confidence=confidence,
            relationship="violates_layer_rule",
            metadata={"source_layer": source_layer, "target_layer": target_layer},
        )

    @staticmethod
    def create_git_evidence(
        file: str,
        commit_count: int,
        primary_contributor: Optional[str],
        ownership_pct: float,
        detail: str,
        confidence: float = 0.85,
    ) -> EvidenceItem:
        return EvidenceItem(
            type=EvidenceType.GIT.value,
            source=file,
            location=file,
            description=detail,
            confidence=confidence,
            relationship="git_ownership",
            metadata={
                "commit_count": commit_count,
                "primary_contributor": primary_contributor,
                "ownership_percentage": ownership_pct,
            },
        )

    @staticmethod
    def create_doc_evidence(
        doc_file: str,
        quote_or_rule: str,
        detail: str,
        confidence: float = 0.90,
    ) -> EvidenceItem:
        return EvidenceItem(
            type=EvidenceType.DOCUMENTATION.value,
            source=doc_file,
            location=doc_file,
            description=detail,
            confidence=confidence,
            relationship="contradicts_documented_rule",
            metadata={"rule": quote_or_rule},
        )

    @staticmethod
    def create_test_evidence(
        test_file: str,
        target_file: str,
        detail: str,
        confidence: float = 0.90,
    ) -> EvidenceItem:
        return EvidenceItem(
            type=EvidenceType.TEST.value,
            source=test_file,
            location=test_file,
            description=detail,
            confidence=confidence,
            relationship="exercises_component",
        )
