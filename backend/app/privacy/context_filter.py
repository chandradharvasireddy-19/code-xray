from typing import Any, Dict, List, Optional
from app.privacy.redactor import SecretRedactor
from app.privacy.secret_scanner import DetectedSecret


class ContextFilter:
    """
    Ensures that AI and external consumers receive only minimal, structured,
    and sanitized context necessary to explain a finding or change impact.
    Prevents passing entire raw files or unauthorized private repository data.
    """

    def __init__(self, redactor: Optional[SecretRedactor] = None):
        self.redactor = redactor or SecretRedactor()

    def filter_finding_context(
        self,
        finding_dict: Dict[str, Any],
        max_evidence_items: int = 5,
    ) -> Dict[str, Any]:
        """
        Produce a sanitized, minimal representation of a forensic finding for AI explanation.
        """
        evidence_chain = finding_dict.get("evidence_chain", [])
        trimmed_evidence = evidence_chain[:max_evidence_items]

        clean_data = {
            "title": finding_dict.get("title"),
            "finding_type": finding_dict.get("finding_type"),
            "affected_file": finding_dict.get("affected_file"),
            "affected_symbol": finding_dict.get("affected_symbol"),
            "severity": finding_dict.get("severity"),
            "confidence": finding_dict.get("confidence"),
            "description": finding_dict.get("description"),
            "evidence": finding_dict.get("evidence"),
            "evidence_items": [
                {
                    "type": e.get("type"),
                    "location": e.get("location"),
                    "description": e.get("description"),
                }
                for e in trimmed_evidence
            ],
        }
        return self.redactor.redact_structure(clean_data)

    def filter_impact_context(
        self,
        impact_dict: Dict[str, Any],
        max_entities: int = 10,
    ) -> Dict[str, Any]:
        """
        Produce a sanitized, bounded representation of impact analysis for AI explanation.
        """
        all_affected = impact_dict.get("affected_entities", [])
        all_tests = impact_dict.get("tests", [])
        affected_sample = all_affected[:max_entities]
        risk = impact_dict.get("risk", {})

        # Deduplicate test file names
        unique_tests = []
        for t in all_tests:
            tf = t.get("test_file") if isinstance(t, dict) else str(t)
            if tf and tf not in unique_tests:
                unique_tests.append(tf)

        clean_data = {
            "task": impact_dict.get("task"),
            "matched_concepts": impact_dict.get("matched_concepts"),
            "total_affected_count": len(all_affected),
            "total_tests_count": len(all_tests),
            "risk_score": risk.get("risk_score") if isinstance(risk, dict) else None,
            "risk_level": risk.get("risk_level") if isinstance(risk, dict) else None,
            "risk_factors": [
                f.get("name") for f in risk.get("factors", [])
            ] if isinstance(risk, dict) else [],
            "affected_entities": [
                {
                    "name": a.get("name"),
                    "file": a.get("file"),
                    "impact_score": a.get("impact_score"),
                    "impact_level": a.get("impact_level"),
                    "reasons": a.get("reasons"),
                }
                for a in affected_sample
            ],
            "related_tests": unique_tests,
        }
        return self.redactor.redact_structure(clean_data)
