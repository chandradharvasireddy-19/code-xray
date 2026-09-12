import threading
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app.models.repository import RepositoryModel
from app.models.finding import ForensicFinding
from app.models.impact import ImpactAnalysisResponse


class MemoryStore:
    """
    Thread-safe in-memory data store for repositories, scans, findings, and impact runs.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self.repositories: Dict[str, RepositoryModel] = {}
        self.scans: Dict[str, Dict[str, Any]] = {}
        self.findings: Dict[str, ForensicFinding] = {}            # keyed by finding_id
        self.repo_findings: Dict[str, List[str]] = {}             # repo_id -> list of finding_ids
        self.impact_analyses: Dict[str, ImpactAnalysisResponse] = {} # keyed by analysis_id
        self.repo_impacts: Dict[str, List[str]] = {}              # repo_id -> list of analysis_ids

    # Repository operations
    def save_repository(self, repo: RepositoryModel) -> None:
        with self._lock:
            self.repositories[repo.repository_id] = repo

    def get_repository(self, repository_id: str) -> Optional[RepositoryModel]:
        with self._lock:
            return self.repositories.get(repository_id)

    def list_repositories(self) -> List[RepositoryModel]:
        with self._lock:
            return list(self.repositories.values())

    # Scan operations
    def save_scan(self, scan_record: Dict[str, Any]) -> None:
        with self._lock:
            self.scans[scan_record["scan_id"]] = scan_record

    def update_scan_status(
        self,
        scan_id: str,
        status: str,
        repository_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            scan = self.scans.get(scan_id)
            if scan:
                scan["status"] = status
                if repository_id:
                    scan["repository_id"] = repository_id
                if error:
                    scan["error"] = error
                if status in ["completed", "failed"]:
                    scan["completed_at"] = datetime.now(timezone.utc).isoformat()
            return scan

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.scans.get(scan_id)

    def list_scans(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.scans.values())

    # Finding operations
    def save_findings(self, repository_id: str, findings: List[ForensicFinding]) -> None:
        with self._lock:
            if repository_id not in self.repo_findings:
                self.repo_findings[repository_id] = []
            for f in findings:
                self.findings[f.finding_id] = f
                if f.finding_id not in self.repo_findings[repository_id]:
                    self.repo_findings[repository_id].append(f.finding_id)

    def get_finding(self, finding_id: str) -> Optional[ForensicFinding]:
        with self._lock:
            return self.findings.get(finding_id)

    def get_findings_for_repo(self, repository_id: str) -> List[ForensicFinding]:
        with self._lock:
            f_ids = self.repo_findings.get(repository_id, [])
            return [self.findings[fid] for fid in f_ids if fid in self.findings]

    def list_all_findings(self) -> List[ForensicFinding]:
        with self._lock:
            return list(self.findings.values())

    # Impact operations
    def save_impact_analysis(self, analysis: ImpactAnalysisResponse) -> None:
        with self._lock:
            self.impact_analyses[analysis.analysis_id] = analysis
            if analysis.repository_id not in self.repo_impacts:
                self.repo_impacts[analysis.repository_id] = []
            if analysis.analysis_id not in self.repo_impacts[analysis.repository_id]:
                self.repo_impacts[analysis.repository_id].append(analysis.analysis_id)

    def get_impact_analysis(self, analysis_id: str) -> Optional[ImpactAnalysisResponse]:
        with self._lock:
            return self.impact_analyses.get(analysis_id)

    def get_impacts_for_repo(self, repository_id: str) -> List[ImpactAnalysisResponse]:
        with self._lock:
            a_ids = self.repo_impacts.get(repository_id, [])
            return [self.impact_analyses[aid] for aid in a_ids if aid in self.impact_analyses]

    def clear(self) -> None:
        with self._lock:
            self.repositories.clear()
            self.scans.clear()
            self.findings.clear()
            self.repo_findings.clear()
            self.impact_analyses.clear()
            self.repo_impacts.clear()


# Global singleton instance
db = MemoryStore()
