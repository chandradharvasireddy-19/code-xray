from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from app.models.finding import ForensicFinding
from app.storage.memory_store import db

router = APIRouter(tags=["Findings"])


@router.get("/findings/{repository_id}")
def get_findings_for_repository(
    repository_id: str,
    finding_type: Optional[str] = Query(None, description="Filter by finding type"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
):
    """
    List all forensic findings for a scanned repository, with optional type and severity filters.
    """
    repo = db.get_repository(repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repository_id}' not found.",
        )

    findings = db.get_findings_for_repo(repository_id)
    if finding_type:
        findings = [f for f in findings if f.finding_type == finding_type]
    if severity:
        findings = [f for f in findings if f.severity.lower() == severity.lower()]

    return {
        "repository_id": repository_id,
        "total_findings": len(findings),
        "findings": [f.to_dict() for f in findings],
    }


@router.get("/findings/{repository_id}/{finding_id}")
def get_finding_by_repo_and_id(repository_id: str, finding_id: str):
    """
    Retrieve a specific finding for a repository.
    """
    finding = db.get_finding(finding_id)
    if not finding or finding.repository_id != repository_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found for repository '{repository_id}'.",
        )
    return finding.to_dict()


@router.get("/finding/{finding_id}")
def get_finding_by_id(finding_id: str):
    """
    Retrieve a specific finding by finding_id.
    """
    finding = db.get_finding(finding_id)
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found.",
        )
    return finding.to_dict()
