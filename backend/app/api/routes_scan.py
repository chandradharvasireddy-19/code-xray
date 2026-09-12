from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.services.scan_service import ScanService
from app.storage.memory_store import db

router = APIRouter(tags=["Scan & Analysis"])

scan_service = ScanService()


class ScanRequest(BaseModel):
    path: Optional[str] = Field(default=None, description="Local directory path to scan")
    repo_url: Optional[str] = Field(default=None, description="Remote Git URL to clone and scan")
    token: Optional[str] = Field(default=None, description="Optional GitHub token for private repositories")
    branch: Optional[str] = Field(default=None, description="Target branch")
    name: Optional[str] = Field(default=None, description="Optional repository name")
    repository_id: Optional[str] = Field(default=None, description="Optional custom repository ID")


@router.post("/repository/scan", status_code=status.HTTP_201_CREATED)
@router.post("/scan", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def scan_repository(payload: ScanRequest):
    """
    Trigger end-to-end repository scan and forensic analysis.
    Supports local filesystem paths and remote Git URLs.
    """
    if not payload.path and not payload.repo_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'path' (local repository) or 'repo_url' (remote Git repository) must be provided.",
        )

    result = scan_service.run_scan(
        path=payload.path,
        repo_url=payload.repo_url,
        token=payload.token,
        branch=payload.branch,
        name=payload.name,
        repository_id=payload.repository_id,
    )
    if result.get("status") == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {result.get('error')}",
        )
    return result


@router.get("/repository/scan/{scan_id}")
@router.get("/scan/{scan_id}", include_in_schema=False)
def get_scan_status(scan_id: str):
    """
    Retrieve scan progress, status, and summary results.
    """
    scan = db.get_scan(scan_id)
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID '{scan_id}' not found.",
        )
    return scan


@router.get("/analysis/{repository_id}")
def get_repository_analysis(repository_id: str):
    """
    Retrieve full forensic analysis results for a repository.
    Includes classification profile, code entities, dependency graph,
    call graph, test relationships, and detected findings.
    """
    repo = db.get_repository(repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis found for repository '{repository_id}'.",
        )

    findings = db.get_findings_for_repo(repository_id)

    return {
        "repository_id": repo.repository_id,
        "name": repo.name,
        "path": repo.path,
        "created_at": repo.created_at,
        "summary": {
            "total_files": len(repo.files),
            "source_files": len(repo.source_files),
            "test_files": len(repo.test_files),
            "total_entities": len(repo.entities),
            "total_relationships": len(repo.relationships),
            "total_findings": len(findings),
            "total_commits": len(repo.commits),
        },
        "languages": repo.languages,
        "declared_dependencies": repo.declared_dependencies,
        "entities": [e.to_dict() for e in repo.entities.values()],
        "relationships": [r.to_dict() for r in repo.relationships],
        "findings": [f.to_dict() for f in findings],
        "commits": [c.to_dict() for c in repo.commits],
        "contributors": {k: v.to_dict() for k, v in repo.contributors.items()},
    }
