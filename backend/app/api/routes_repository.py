from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.services.repository_service import RepositoryService
from app.storage.memory_store import db

router = APIRouter(prefix="", tags=["Repository"])


class LocalRepoRegisterRequest(BaseModel):
    path: str = Field(..., description="Absolute local filesystem path to the repository directory")
    name: Optional[str] = Field(default=None, description="Optional custom repository name")
    repository_id: Optional[str] = Field(default=None, description="Optional unique identifier")


class RepositorySummaryResponse(BaseModel):
    repository_id: str
    name: str
    path: str
    file_count: int
    source_files: int
    test_files: int
    languages: Dict[str, int]
    created_at: str


@router.get("/repositories", response_model=List[RepositorySummaryResponse])
def list_repositories():
    """
    List all scanned/registered repositories.
    """
    return RepositoryService.list_repositories()


@router.get("/repository/{repository_id}")
def get_repository_details(repository_id: str):
    """
    Get full metadata and structure of a registered repository.
    """
    repo = RepositoryService.get_repository(repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repository_id}' not found.",
        )
    return {
        "repository_id": repo.repository_id,
        "name": repo.name,
        "path": repo.path,
        "files": repo.files,
        "directories": repo.directories,
        "languages": repo.languages,
        "source_files": repo.source_files,
        "test_files": repo.test_files,
        "documentation_files": repo.documentation_files,
        "configuration_files": repo.configuration_files,
        "declared_dependencies": repo.declared_dependencies,
        "entities_count": len(repo.entities),
        "relationships_count": len(repo.relationships),
        "commits_count": len(repo.commits),
        "contributors_count": len(repo.contributors),
        "created_at": repo.created_at,
    }


@router.post("/repository/local", status_code=status.HTTP_201_CREATED)
def register_local_repository(payload: LocalRepoRegisterRequest):
    """
    Register a local repository path into a workspace.
    """
    try:
        workspace = RepositoryService.register_local_repository(
            path=payload.path,
            name=payload.name,
            repository_id=payload.repository_id,
        )
        return workspace.to_dict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
