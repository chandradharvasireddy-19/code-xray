"""Detect potentially unused functions, classes, modules, and legacy code."""
from typing import Any, Dict, List, Set
from app.models.repository import CodeEntity, Relationship, RepositoryModel
from app.models.finding import ForensicFinding, FindingType
from app.models.evidence import EvidenceItem, EvidenceType
from app.evidence.confidence import ConfidenceEngine
import uuid


class DeadFeatureDetector:
    """
    Identifies code entities that appear unused based on:
    - No callers in the call graph
    - No imports referencing the module/file
    - No references from test files
    - Location in legacy/deprecated directories
    """

    LEGACY_MARKERS = {"legacy", "deprecated", "old", "archive", "obsolete", "unused"}

    def __init__(self, repo: RepositoryModel):
        self.repo = repo
        self.entities = repo.entities
        self.relationships = repo.relationships

    def detect(self) -> List[ForensicFinding]:
        findings: List[ForensicFinding] = []

        # Build sets of referenced entities
        called_targets: Set[str] = set()
        imported_targets: Set[str] = set()
        tested_targets: Set[str] = set()

        for rel in self.relationships:
            if rel.type == "calls":
                called_targets.add(rel.target)
            elif rel.type == "imports":
                imported_targets.add(rel.target)
            elif rel.type == "tests":
                tested_targets.add(rel.target)

        # Build set of files that are imported by anything
        imported_files: Set[str] = set()
        for rel in self.relationships:
            if rel.type == "imports":
                imported_files.add(rel.target)

        for entity_id, entity in self.entities.items():
            if entity.is_test:
                continue
            if entity.type == "file":
                # Check if file is imported by any other file
                if entity.file not in imported_files and not entity.file.endswith("__init__.py"):
                    # Check if it's a test or config file
                    if entity.file in self.repo.source_files:
                        is_legacy = self._in_legacy_dir(entity.file)
                        base_conf = 0.60 if not is_legacy else 0.75

                        evidence_items = []
                        reasons = []

                        evidence_items.append(EvidenceItem(
                            type=EvidenceType.DEPENDENCY.value,
                            source=entity.file,
                            location=entity.file,
                            description=f"No other source file imports '{entity.file}'",
                            confidence=0.85,
                            relationship="no_importers",
                        ))
                        reasons.append("No detected importers in codebase")

                        if is_legacy:
                            evidence_items.append(EvidenceItem(
                                type=EvidenceType.AST.value,
                                source=entity.file,
                                location=entity.file,
                                description=f"File located in legacy/deprecated directory",
                                confidence=0.80,
                            ))
                            reasons.append("Located in legacy/deprecated directory")
                            base_conf += 0.10

                        if entity.file not in tested_targets:
                            reasons.append("No associated tests detected")

                        confidence = ConfidenceEngine.calculate_score(base_conf)
                        findings.append(ForensicFinding(
                            finding_id=f"dead-{uuid.uuid4().hex[:8]}",
                            repository_id=self.repo.repository_id,
                            finding_type=FindingType.DEAD_FEATURE.value,
                            title=f"Potentially unused module: {entity.name}",
                            affected_file=entity.file,
                            severity="low",
                            confidence=confidence,
                            confidence_level=ConfidenceEngine.get_level(confidence),
                            description=f"Module '{entity.file}' has no detected importers and may be unused. " + "; ".join(reasons),
                            evidence="; ".join(reasons),
                            evidence_chain=evidence_items,
                        ))
                continue

            # Check functions and classes
            if entity.type in ("function", "method", "class"):
                if entity.name.startswith("_") and entity.type != "class":
                    continue  # Skip private helpers

                is_referenced = (
                    entity_id in called_targets or
                    entity_id in imported_targets or
                    entity_id in tested_targets
                )

                if not is_referenced:
                    # Check if any entity calls this by name (loose match)
                    name_called = any(
                        entity.name in (e.calls if hasattr(e, 'calls') else [])
                        for e in self.entities.values()
                        if e.id != entity_id and not e.is_test
                    )
                    if name_called:
                        continue

                    is_legacy = self._in_legacy_dir(entity.file)
                    base_conf = 0.55 if not is_legacy else 0.70

                    evidence_items = [
                        EvidenceItem(
                            type=EvidenceType.CALL_GRAPH.value,
                            source=entity.file,
                            location=entity.file,
                            line=entity.line_start,
                            description=f"No callers detected for {entity.type} '{entity.name}'",
                            confidence=0.80,
                            relationship="no_callers",
                        )
                    ]

                    if is_legacy:
                        evidence_items.append(EvidenceItem(
                            type=EvidenceType.AST.value,
                            source=entity.file,
                            location=entity.file,
                            description="Located in legacy/deprecated directory",
                            confidence=0.80,
                        ))
                        base_conf += 0.10

                    confidence = ConfidenceEngine.calculate_score(base_conf)
                    findings.append(ForensicFinding(
                        finding_id=f"dead-{uuid.uuid4().hex[:8]}",
                        repository_id=self.repo.repository_id,
                        finding_type=FindingType.DEAD_FEATURE.value,
                        title=f"Potentially unused {entity.type}: {entity.name}",
                        affected_file=entity.file,
                        affected_symbol=entity.name,
                        line_number=entity.line_start,
                        severity="low",
                        confidence=confidence,
                        confidence_level=ConfidenceEngine.get_level(confidence),
                        description=f"{entity.type.capitalize()} '{entity.name}' in '{entity.file}' has no detected callers or references.",
                        evidence=f"No callers in call graph; no import references" + ("; in legacy directory" if is_legacy else ""),
                        evidence_chain=evidence_items,
                    ))

        return findings

    def _in_legacy_dir(self, file_path: str) -> bool:
        parts = set(file_path.lower().replace("\\", "/").split("/"))
        return bool(parts & self.LEGACY_MARKERS)
