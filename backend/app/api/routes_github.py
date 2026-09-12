from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.services.github_service import GitHubService

router = APIRouter(prefix="/github", tags=["GitHub Ingestion"])


class PublicGithubRequest(BaseModel):
    repo_url: str = Field(..., description="Public GitHub repository URL (e.g. https://github.com/owner/repo)")
    branch: Optional[str] = Field(default=None, description="Optional branch to clone")
    name: Optional[str] = Field(default=None, description="Optional repository name")
    repository_id: Optional[str] = Field(default=None, description="Optional repository ID")


class PrivateGithubRequest(BaseModel):
    repo_url: str = Field(..., description="Private GitHub repository URL")
    token: str = Field(..., description="GitHub Personal Access Token with repo read scope")
    branch: Optional[str] = Field(default=None, description="Optional branch to clone")
    name: Optional[str] = Field(default=None, description="Optional repository name")
    repository_id: Optional[str] = Field(default=None, description="Optional repository ID")


@router.post("/public", status_code=status.HTTP_201_CREATED)
def ingest_public_github(payload: PublicGithubRequest):
    """
    Ingest and clone a public GitHub repository.
    """
    try:
        workspace = GitHubService.ingest_public_repository(
            repo_url=payload.repo_url,
            branch=payload.branch,
            name=payload.name,
            repository_id=payload.repository_id,
        )
        return workspace.to_dict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/private", status_code=status.HTTP_201_CREATED)
def ingest_private_github(payload: PrivateGithubRequest):
    """
    Ingest and clone a private GitHub repository with personal access token authentication.
    """
    try:
        workspace = GitHubService.ingest_private_repository(
            repo_url=payload.repo_url,
            token=payload.token,
            branch=payload.branch,
            name=payload.name,
            repository_id=payload.repository_id,
        )
        return workspace.to_dict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
