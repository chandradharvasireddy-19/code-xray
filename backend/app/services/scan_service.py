import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.models.repository import RepositoryModel, Relationship, CodeEntity
from app.models.finding import ForensicFinding
from app.storage.memory_store import db
from app.config import REPOS_DIR
from app.ingestion import RepositoryWorkspace, RepositorySourceType
from app.ingestion.local_repo import LocalRepoLoader
from app.ingestion.public_repo import PublicRepoLoader
from app.ingestion.private_repo import PrivateRepoLoader
from app.classification.repository_profile import RepositoryProfiler, RepositoryProfile
from app.privacy.secret_scanner import SecretScanner, DetectedSecret
from app.analyzer.repository import RepositoryLoader
from app.analyzer.parser import PythonASTParser, ImportStatement
from app.analyzer.dependencies import DependencyAnalyzer
from app.analyzer.call_graph import CallGraphBuilder
from app.analyzer.tests import TestAnalyzer
from app.analyzer.git_history import GitHistoryAnalyzer
from app.analyzer.docs import DocsAnalyzer, DocumentedRule
from app.detectors.architecture import ArchitectureDetector
from app.detectors.dead_features import DeadFeatureDetector
from app.detectors.ghost_dependencies import GhostDependencyDetector
from app.detectors.knowledge import KnowledgeConcentrationDetector
from app.ai.explainer import ForensicExplainer


class ScanService:
    """
    Full pipeline orchestrator:
    Ingestion -> Classification -> Privacy Scan -> AST -> Dependencies -> Call Graph
    -> Tests -> Git History -> Docs -> Detectors -> Evidence -> AI Explanation -> Store
    """

    def __init__(self):
        self.explainer = ForensicExplainer()

    def run_scan(
        self,
        path: Optional[str] = None,
        repo_url: Optional[str] = None,
        token: Optional[str] = None,
        branch: Optional[str] = None,
        name: Optional[str] = None,
        repository_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        scan_id = f"scan-{uuid.uuid4().hex[:8]}"
        repo_id = repository_id or f"repo-{uuid.uuid4().hex[:8]}"
        created_at = datetime.now(timezone.utc).isoformat()
        warnings: List[Dict[str, Any]] = []

        scan_record = {
            "scan_id": scan_id,
            "repository_id": repo_id,
            "status": "in_progress",
            "created_at": created_at,
            "warnings": warnings,
        }
        db.save_scan(scan_record)

        try:
            # 1. Ingestion
            workspace = self._ingest(
                path=path,
                repo_url=repo_url,
                token=token,
                branch=branch,
                name=name,
                repository_id=repo_id,
            )

            # 2. Baseline Repository Model
            repo_loader = RepositoryLoader(
                repo_id=repo_id,
                repo_path=workspace.path,
                repo_name=workspace.name,
            )
            repo: RepositoryModel = repo_loader.load()

            # 3. Classification
            profiler = RepositoryProfiler(
                repo_path=workspace.path,
                files=repo.files,
                declared_dependencies=repo.declared_dependencies,
            )
            profile: RepositoryProfile = profiler.profile()

            # 4. Privacy Scan
            secret_scanner = SecretScanner(workspace.path)
            detected_secrets: List[DetectedSecret] = secret_scanner.scan()

            # 5. AST & Dependency Analysis (Python)
            ast_parser = PythonASTParser(workspace.path)
            dep_analyzer = DependencyAnalyzer(repo.files)

            all_imports: Dict[str, List[ImportStatement]] = {}
            observed_imports: Dict[str, set] = {}

            python_files = [f for f in repo.files if f.endswith(".py")]
            for rel_file in python_files:
                entities, file_imports = ast_parser.parse_file(rel_file)
                for ent in entities:
                    repo.entities[ent.id] = ent
                all_imports[rel_file] = file_imports

                # Dependencies
                internal_rels, ext_imports = dep_analyzer.analyze_file_imports(rel_file, file_imports)
                repo.relationships.extend(internal_rels)

                for pkg, files in ext_imports.items():
                    if pkg not in observed_imports:
                        observed_imports[pkg] = set()
                    observed_imports[pkg].update(files)

            if ast_parser.parse_errors:
                warnings.extend(ast_parser.parse_errors)

            # 6. Call Graph Analysis
            cg_builder = CallGraphBuilder(repo.entities, repo.relationships)
            call_rels = cg_builder.build()
            repo.relationships.extend(call_rels)

            # 7. Test Analysis
            test_analyzer = TestAnalyzer(
                test_files=repo.test_files,
                source_files=repo.source_files,
                entities=repo.entities,
                file_dependencies=repo.relationships,
                call_relationships=call_rels,
            )
            test_rels, tested_map, untested_files = test_analyzer.analyze()
            repo.relationships.extend(test_rels)

            # 8. Git History Analysis
            git_analyzer = GitHistoryAnalyzer(workspace.path)
            commits, contributors, git_file_stats, is_incomplete = git_analyzer.analyze()
            repo.commits = commits
            repo.contributors = contributors
            if is_incomplete and not (Path(workspace.path) / ".git").exists():
                warnings.append({
                    "type": "git",
                    "message": "Git history unavailable (.git directory not found or not a repository).",
                })

            # 9. Architectural Documentation Rules
            docs_analyzer = DocsAnalyzer(workspace.path, repo.documentation_files)
            documented_rules = docs_analyzer.extract_rules()

            # 10. Forensic Detectors
            findings: List[ForensicFinding] = []

            # Architecture violations
            arch_detector = ArchitectureDetector(repo, documented_rules)
            findings.extend(arch_detector.detect())

            # Dead features
            dead_detector = DeadFeatureDetector(repo)
            findings.extend(dead_detector.detect())

            # Ghost dependencies
            ghost_detector = GhostDependencyDetector(repo, observed_imports)
            findings.extend(ghost_detector.detect())

            # Knowledge concentration
            knowledge_detector = KnowledgeConcentrationDetector(repo, git_file_stats)
            findings.extend(knowledge_detector.detect())

            # 11. AI Explanations for Findings
            for finding in findings:
                try:
                    finding.explanation = self.explainer.explain_finding(finding.to_dict())
                except Exception:
                    finding.explanation = finding.description

            # 12. Persistence
            db.save_repository(repo)
            db.save_findings(repo_id, findings)

            completed_at = datetime.now(timezone.utc).isoformat()
            summary = {
                "scan_id": scan_id,
                "repository_id": repo_id,
                "repository_name": repo.name,
                "status": "completed",
                "created_at": created_at,
                "completed_at": completed_at,
                "profile": profile.to_dict(),
                "file_count": len(repo.files),
                "entities_count": len(repo.entities),
                "relationships_count": len(repo.relationships),
                "findings_count": len(findings),
                "secrets_detected": len(detected_secrets),
                "untested_files_count": len(untested_files),
                "git_commits_analyzed": len(commits),
                "warnings": warnings,
            }

            db.update_scan_status(scan_id, status="completed", repository_id=repo_id)
            scan_record.update(summary)
            return scan_record

        except Exception as e:
            db.update_scan_status(scan_id, status="failed", repository_id=repo_id, error=str(e))
            scan_record["status"] = "failed"
            scan_record["error"] = str(e)
            return scan_record

    def _ingest(
        self,
        path: Optional[str],
        repo_url: Optional[str],
        token: Optional[str],
        branch: Optional[str],
        name: Optional[str],
        repository_id: str,
    ) -> RepositoryWorkspace:
        # -------------------------------------------------------------------
        # Fast-path: if this repository_id already has a workspace directory
        # on disk (created by a prior /github/public or /github/private call),
        # wrap it in a RepositoryWorkspace and return immediately without
        # attempting a second clone. This resolves the "directory already
        # exists and is not empty" error when scanning a previously-ingested
        # GitHub repository.
        # -------------------------------------------------------------------
        existing_workspace_path = REPOS_DIR / repository_id
        if existing_workspace_path.is_dir() and any(existing_workspace_path.iterdir()):
            # Determine a sensible name: prefer the caller-supplied name, then
            # fall back to what the db already knows, then use the directory name.
            existing_repo = db.get_repository(repository_id)
            resolved_name = (
                name
                or (existing_repo.name if existing_repo else None)
                or existing_workspace_path.name
            )
            source = (
                RepositorySourceType.GITHUB_PUBLIC.value
                if not token
                else RepositorySourceType.GITHUB_PRIVATE.value
            )
            return RepositoryWorkspace(
                repository_id=repository_id,
                name=resolved_name,
                source=source,
                path=str(existing_workspace_path.resolve()),
                status="ready",
                metadata={
                    "repo_url": repo_url or "",
                    "reused_existing_workspace": True,
                    "is_git_repo": (existing_workspace_path / ".git").exists(),
                },
            )

        if path:
            loader = LocalRepoLoader(
                local_path=path,
                repository_id=repository_id,
                name=name,
            )
            return loader.load()
        elif repo_url:
            if token:
                loader = PrivateRepoLoader(
                    repo_url=repo_url,
                    token=token,
                    branch=branch,
                    repository_id=repository_id,
                    name=name,
                )
                return loader.load()
            else:
                loader = PublicRepoLoader(
                    repo_url=repo_url,
                    branch=branch,
                    repository_id=repository_id,
                    name=name,
                )
                return loader.load()
        else:
            raise ValueError("Either local 'path' or remote 'repo_url' must be provided for repository scanning.")
