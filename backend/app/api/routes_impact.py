from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.storage.memory_store import db
from app.impact.impact_analyzer import ImpactAnalyzer
from app.ai.explainer import ForensicExplainer

router = APIRouter(prefix="/impact", tags=["Change Impact Intelligence"])

explainer = ForensicExplainer()


class ImpactAnalysisRequest(BaseModel):
    task: str = Field(..., description="Natural language developer task or intent description")


@router.post("/{repository_id}", status_code=status.HTTP_201_CREATED)
def run_change_impact_analysis(repository_id: str, payload: ImpactAnalysisRequest):
    """
    Run Change Impact Intelligence analysis for a developer task on a scanned repository.
    Traverses dependency and call graphs, maps affected tests, historical churn,
    known architecture violations, computes multi-factor risk, and generates
    an evidence-backed explanation.
    """
    repo = db.get_repository(repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repository_id}' has not been scanned yet. Please scan it first.",
        )

    findings = db.get_findings_for_repo(repository_id)

    # Reconstruct git file stats if available
    git_file_stats: Dict[str, Dict[str, Any]] = {}
    for commit in repo.commits:
        for f in commit.changed_files:
            if f not in git_file_stats:
                git_file_stats[f] = {
                    "total_commits": 0,
                    "recent_commits": 0,
                    "primary_contributor": commit.author,
                    "contributor_count": 1,
                    "churn": "moderate",
                }
            git_file_stats[f]["total_commits"] += 1

    analyzer = ImpactAnalyzer(
        repo=repo,
        findings=findings,
        git_file_stats=git_file_stats,
    )
    result = analyzer.analyze(payload.task)

    # Generate AI explanation with deterministic fallback
    try:
        explanation = explainer.explain_impact(result.to_dict())
        result.ai_explanation = explanation
    except Exception:
        result.ai_explanation = None

    # Persist
    db.save_impact_analysis(result)

    result_dict = result.to_dict()

    # Provide frontend-friendly top-level summary
    top_entity = result.affected_entities[0] if result.affected_entities else None
    overall_impact_level = top_entity.impact_level if top_entity else "LOW"

    result_dict["summary"] = {
        "impact_level": overall_impact_level,
        "affected_entities": len(result.affected_entities),
        "risk_score": result.risk.risk_score if result.risk else 0,
        "risk_level": result.risk.risk_level if result.risk else "LOW",
        "related_tests_count": len(result.tests),
        "related_findings_count": len(result.findings),
    }

    return result_dict


@router.get("/{repository_id}/{analysis_id}")
def get_impact_analysis_result(repository_id: str, analysis_id: str):
    """
    Retrieve previously calculated change impact analysis by ID.
    """
    analysis = db.get_impact_analysis(analysis_id)
    if not analysis or analysis.repository_id != repository_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Impact analysis '{analysis_id}' not found for repository '{repository_id}'.",
        )
    return analysis.to_dict()


@router.get("/{repository_id}")
def list_impact_analyses_for_repo(repository_id: str):
    """
    List all impact analyses performed on a repository.
    """
    analyses = db.get_impacts_for_repo(repository_id)
    return [
        {
            "analysis_id": a.analysis_id,
            "task": a.task,
            "affected_entities_count": len(a.affected_entities),
            "risk_score": a.risk.risk_score if a.risk else 0,
            "risk_level": a.risk.risk_level if a.risk else "LOW",
            "created_at": a.created_at,
        }
        for a in analyses
    ]
