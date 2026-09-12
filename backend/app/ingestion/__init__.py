from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime, timezone


class RepositorySourceType(str, Enum):
    LOCAL = "local"
    GITHUB_PUBLIC = "github_public"
    GITHUB_PRIVATE = "github_private"


@dataclass
class RepositoryWorkspace:
    repository_id: str
    name: str
    source: str                              # 'local', 'github_public', 'github_private'
    path: str                                # Absolute path to working tree
    status: str = "ready"                    # 'ready', 'cloning', 'failed'
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseRepoLoader:
    def load(self) -> RepositoryWorkspace:
        raise NotImplementedError
