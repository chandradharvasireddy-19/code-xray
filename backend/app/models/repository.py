from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


@dataclass
class CodeEntity:
    id: str                                  # Stable identifier: e.g., 'src/auth/service.py:AuthService.authenticate'
    type: str                                # 'function', 'method', 'class', 'module', 'file'
    name: str                                # Short symbol name
    file: str                                # Relative file path
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    docstring: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    bases: List[str] = field(default_factory=list)        # Class inheritance
    params: List[str] = field(default_factory=list)       # Function arguments
    calls: List[str] = field(default_factory=list)        # Raw names invoked
    is_exported: bool = True
    is_test: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Relationship:
    source: str                              # Entity ID or file path
    target: str                              # Entity ID, file path, or package name
    type: str                                # 'imports', 'calls', 'inherits', 'tests'
    confidence: float = 1.0                  # 0.0 to 1.0
    line: Optional[int] = None
    detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FileMeta:
    path: str                                # Relative file path
    full_path: str                           # Absolute path
    size_bytes: int = 0
    language: str = "unknown"
    is_source: bool = False
    is_test: bool = False
    is_doc: bool = False
    is_config: bool = False
    commit_count: int = 0
    dominant_contributor: Optional[str] = None
    contributor_count: int = 0
    churn_score: float = 0.0
    last_modified: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CommitMeta:
    hash: str
    author: str
    date: str
    message: str
    changed_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContributorMeta:
    name: str
    commit_count: int = 0
    files_touched: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepositoryModel:
    repository_id: str
    name: str
    path: str
    files: List[str] = field(default_factory=list)
    directories: List[str] = field(default_factory=list)
    languages: Dict[str, int] = field(default_factory=dict)
    source_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    documentation_files: List[str] = field(default_factory=list)
    configuration_files: List[str] = field(default_factory=list)
    declared_dependencies: Dict[str, Optional[str]] = field(default_factory=dict)
    entities: Dict[str, CodeEntity] = field(default_factory=dict)
    relationships: List[Relationship] = field(default_factory=list)
    commits: List[CommitMeta] = field(default_factory=list)
    contributors: Dict[str, ContributorMeta] = field(default_factory=dict)
    file_metadata: Dict[str, FileMeta] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "name": self.name,
            "path": self.path,
            "files": self.files,
            "directories": self.directories,
            "languages": self.languages,
            "source_files": self.source_files,
            "test_files": self.test_files,
            "documentation_files": self.documentation_files,
            "configuration_files": self.configuration_files,
            "declared_dependencies": self.declared_dependencies,
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "relationships": [r.to_dict() for r in self.relationships],
            "commits": [c.to_dict() for c in self.commits],
            "contributors": {k: v.to_dict() for k, v in self.contributors.items()},
            "file_metadata": {k: v.to_dict() for k, v in self.file_metadata.items()},
            "created_at": self.created_at,
        }
