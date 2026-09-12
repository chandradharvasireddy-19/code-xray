"""Change impact analyzer: the core feature of the system."""
import uuid
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple
from app.models.repository import CodeEntity, Relationship, RepositoryModel
from app.models.finding import ForensicFinding
from app.models.impact import (
    AffectedEntity, ImpactAnalysisResponse, PathStep, RiskReport,
)
from app.impact.task_parser import TaskParser
from app.impact.risk import RiskEngine
from app.evidence.confidence import ConfidenceEngine


class ImpactAnalyzer:
    """
    Given a RepositoryModel and a developer task, determines:
    1. Directly matched entities
    2. Upstream callers (who calls the matched code)
    3. Downstream dependencies (what the matched code calls)
    4. Related tests
    5. Historical context
    6. Existing findings on impacted code
    7. Risk assessment

    Uses bounded graph traversal to avoid returning the entire repository.
    """

    MAX_DEPTH = 3
    MAX_AFFECTED = 50

    def __init__(
        self,
        repo: RepositoryModel,
        findings: List[ForensicFinding],
        git_file_stats: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        self.repo = repo
        self.findings = findings
        self.git_file_stats = git_file_stats or {}
        self.task_parser = TaskParser(repo)

        # Build adjacency lists
        self._callers: Dict[str, List[Tuple[str, float]]] = {}   # target -> [(caller, confidence)]
        self._callees: Dict[str, List[Tuple[str, float]]] = {}   # caller -> [(callee, confidence)]
        self._importers: Dict[str, List[str]] = {}               # target_file -> [source_files]
        self._imported_by: Dict[str, List[str]] = {}             # source_file -> [target_files]
        self._test_map: Dict[str, List[str]] = {}                # source_file -> [test_files]

        self._build_graph()

    def _build_graph(self) -> None:
        for rel in self.repo.relationships:
            if rel.type == "calls":
                if rel.target not in self._callers:
                    self._callers[rel.target] = []
                self._callers[rel.target].append((rel.source, rel.confidence))

                if rel.source not in self._callees:
                    self._callees[rel.source] = []
                self._callees[rel.source].append((rel.target, rel.confidence))

            elif rel.type == "imports":
                if rel.target not in self._importers:
                    self._importers[rel.target] = []
                self._importers[rel.target].append(rel.source)

                if rel.source not in self._imported_by:
                    self._imported_by[rel.source] = []
                self._imported_by[rel.source].append(rel.target)

            elif rel.type == "tests":
                if rel.target not in self._test_map:
                    self._test_map[rel.target] = []
                self._test_map[rel.target].append(rel.source)

    def analyze(self, task: str) -> ImpactAnalysisResponse:
        analysis_id = f"impact-{uuid.uuid4().hex[:8]}"

        # Step 1: Parse task
        parsed = self.task_parser.parse(task)
        matched_entities = parsed["matched_entities"]
        matched_concepts = parsed["concepts"]

        # Step 2: Collect directly matched entities as seeds
        seed_entity_ids: Set[str] = set(matched_entities)
        # Also add all entities in matched files
        for f in parsed["matched_files"]:
            for eid, entity in self.repo.entities.items():
                if entity.file == f and not entity.is_test:
                    seed_entity_ids.add(eid)

        # Step 3: BFS to find affected entities
        affected: Dict[str, AffectedEntity] = {}
        relationships_out: List[Dict[str, Any]] = []

        # Add direct matches (depth=0)
        for eid in seed_entity_ids:
            entity = self.repo.entities.get(eid)
            if entity and not entity.is_test:
                score = 0.95
                affected[eid] = AffectedEntity(
                    entity_id=eid,
                    name=entity.name,
                    type=entity.type,
                    file=entity.file,
                    line=entity.line_start,
                    impact_score=score,
                    impact_level="HIGH",
                    depth=0,
                    reasons=["Direct task match"],
                )

        # BFS traversal from seeds
        visited: Set[str] = set(seed_entity_ids)
        queue: deque = deque()
        for eid in seed_entity_ids:
            queue.append((eid, 0))

        while queue and len(affected) < self.MAX_AFFECTED:
            current_id, depth = queue.popleft()
            if depth >= self.MAX_DEPTH:
                continue

            next_depth = depth + 1

            # Upstream: who calls this entity?
            for caller_id, conf in self._callers.get(current_id, []):
                if caller_id not in visited:
                    visited.add(caller_id)
                    entity = self.repo.entities.get(caller_id)
                    if entity and not entity.is_test:
                        score = self._depth_score(next_depth, conf, "upstream_caller")
                        affected[caller_id] = AffectedEntity(
                            entity_id=caller_id,
                            name=entity.name,
                            type=entity.type,
                            file=entity.file,
                            line=entity.line_start,
                            impact_score=score,
                            impact_level=self._score_to_level(score),
                            depth=next_depth,
                            reasons=[f"Calls affected entity (depth {next_depth})"],
                        )
                        relationships_out.append({
                            "source": caller_id,
                            "target": current_id,
                            "type": "CALLS",
                            "confidence": conf,
                        })
                        queue.append((caller_id, next_depth))

            # Downstream: what does this entity call?
            for callee_id, conf in self._callees.get(current_id, []):
                if callee_id not in visited:
                    visited.add(callee_id)
                    entity = self.repo.entities.get(callee_id)
                    if entity and not entity.is_test:
                        score = self._depth_score(next_depth, conf, "downstream_dep")
                        affected[callee_id] = AffectedEntity(
                            entity_id=callee_id,
                            name=entity.name,
                            type=entity.type,
                            file=entity.file,
                            line=entity.line_start,
                            impact_score=score,
                            impact_level=self._score_to_level(score),
                            depth=next_depth,
                            reasons=[f"Called by affected entity (depth {next_depth})"],
                        )
                        relationships_out.append({
                            "source": current_id,
                            "target": callee_id,
                            "type": "CALLS",
                            "confidence": conf,
                        })
                        queue.append((callee_id, next_depth))

            # File-level: importers of the current entity's file
            current_entity = self.repo.entities.get(current_id)
            if current_entity and next_depth <= 2:
                for importer_file in self._importers.get(current_entity.file, []):
                    # Add file-level entity for the importing file
                    if importer_file in self.repo.entities and importer_file not in visited:
                        visited.add(importer_file)
                        imp_entity = self.repo.entities[importer_file]
                        if not imp_entity.is_test:
                            score = self._depth_score(next_depth, 0.85, "file_importer")
                            affected[importer_file] = AffectedEntity(
                                entity_id=importer_file,
                                name=imp_entity.name,
                                type="file",
                                file=importer_file,
                                impact_score=score,
                                impact_level=self._score_to_level(score),
                                depth=next_depth,
                                reasons=[f"Imports affected file (depth {next_depth})"],
                            )
                            relationships_out.append({
                                "source": importer_file,
                                "target": current_entity.file,
                                "type": "IMPORTS",
                                "confidence": 0.85,
                            })

        # Step 4: Collect related tests
        tests_out: List[Dict[str, Any]] = []
        affected_files = set(ae.file for ae in affected.values())
        for src_file in affected_files:
            test_files = self._test_map.get(src_file, [])
            for tf in test_files:
                tests_out.append({
                    "test_file": tf,
                    "tests_for": src_file,
                    "confidence": 0.85,
                })

        # Step 5: Collect relevant findings
        findings_out: List[Dict[str, Any]] = []
        for finding in self.findings:
            if finding.affected_file in affected_files:
                findings_out.append({
                    "finding_id": finding.finding_id,
                    "type": finding.finding_type,
                    "title": finding.title,
                    "file": finding.affected_file,
                    "severity": finding.severity,
                })

        # Step 6: Historical context
        historical: List[Dict[str, Any]] = []
        for f in affected_files:
            stats = self.git_file_stats.get(f)
            if stats:
                historical.append({
                    "file": f,
                    "total_commits": stats.get("total_commits", 0),
                    "recent_commits": stats.get("recent_commits", 0),
                    "primary_contributor": stats.get("primary_contributor"),
                    "contributor_count": stats.get("contributor_count", 0),
                    "churn": stats.get("churn", "unknown"),
                })

        # Step 7: Risk analysis
        risk_engine = RiskEngine(
            affected_entities=list(affected.values()),
            relationships=relationships_out,
            tests=tests_out,
            findings=findings_out,
            historical=historical,
            repo=self.repo,
        )
        risk_report = risk_engine.calculate()

        # Step 8: Build recommended investigation path
        recommended_path = self._build_path(affected)

        # Build sorted affected list (highest impact first)
        affected_sorted = sorted(affected.values(), key=lambda x: x.impact_score, reverse=True)

        return ImpactAnalysisResponse(
            analysis_id=analysis_id,
            repository_id=self.repo.repository_id,
            task=task,
            matched_concepts=matched_concepts,
            matched_entities=list(seed_entity_ids),
            affected_entities=affected_sorted,
            relationships=relationships_out,
            tests=tests_out,
            findings=findings_out,
            historical_context=historical,
            risk=risk_report,
            recommended_path=recommended_path,
        )

    def _depth_score(self, depth: int, confidence: float, rel_type: str) -> float:
        base_scores = {0: 0.95, 1: 0.80, 2: 0.60, 3: 0.40}
        base = base_scores.get(depth, 0.30)
        # Upstream callers are slightly more impactful than downstream deps
        if rel_type == "upstream_caller":
            base += 0.05
        score = base * confidence
        return round(min(0.95, max(0.10, score)), 2)

    def _score_to_level(self, score: float) -> str:
        if score >= 0.75:
            return "HIGH"
        elif score >= 0.45:
            return "MEDIUM"
        return "LOW"

    def _build_path(self, affected: Dict[str, AffectedEntity]) -> List[PathStep]:
        path: List[PathStep] = []
        sorted_entities = sorted(affected.values(), key=lambda x: (-x.impact_score, x.depth))

        step_num = 1
        seen_files: Set[str] = set()
        for ae in sorted_entities:
            if ae.file in seen_files:
                continue
            seen_files.add(ae.file)

            # Determine role
            file_lower = ae.file.lower()
            if "controller" in file_lower or "handler" in file_lower or "route" in file_lower:
                role = "entry_point"
            elif "service" in file_lower or "manager" in file_lower:
                role = "business_logic"
            elif "repository" in file_lower or "repo" in file_lower or "store" in file_lower:
                role = "data_access"
            elif "test" in file_lower:
                role = "test"
            elif "auth" in file_lower or "valid" in file_lower:
                role = "validation"
            else:
                role = "dependency"

            path.append(PathStep(
                step=step_num,
                entity=ae.name,
                file=ae.file,
                reason=ae.reasons[0] if ae.reasons else "Related to task",
                role=role,
            ))
            step_num += 1

            if step_num > 10:
                break

        return path
