from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParseError:
    """Represents a syntax or parsing error in a source file."""
    file_path: str
    error_message: str
    line_number: int | None = None


@dataclass
class ImportInfo:
    """Represents an imported module or name."""
    file_path: str
    module: str
    name: str | None = None
    alias: str | None = None
    line_number: int = 1
    is_from_import: bool = False


@dataclass
class FunctionInfo:
    """Represents a function or method definition."""
    name: str
    file_path: str
    line_number: int
    arguments: list[str] = field(default_factory=list)
    is_method: bool = False
    class_name: str | None = None
    is_async: bool = False


@dataclass
class ClassInfo:
    """Represents a class definition."""
    name: str
    file_path: str
    line_number: int
    base_classes: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)


@dataclass
class CallInfo:
    """Represents a function or method call site."""
    caller: str
    callee: str
    file_path: str
    line_number: int
    caller_class: str | None = None


@dataclass
class ParsedFile:
    """Consolidated AST analysis for a single Python file."""
    file_path: str
    imports: list[ImportInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    calls: list[CallInfo] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)


@dataclass
class DependencyInfo:
    """Factual information about an external dependency."""
    name: str
    declared: bool
    imported: bool
    version_spec: str | None = None
    source_file: str | None = None


@dataclass
class LocalDependencyInfo:
    """Factual information about an internal inter-module dependency."""
    source_file: str
    target_module: str
    imported_names: list[str] = field(default_factory=list)
    line_number: int = 1


@dataclass
class DependenciesReport:
    """Report of all external and local dependency facts."""
    dependencies: list[DependencyInfo] = field(default_factory=list)
    local_dependencies: list[LocalDependencyInfo] = field(default_factory=list)
    declared_files_found: list[str] = field(default_factory=list)


@dataclass
class CallRelationship:
    """A directed edge in the call graph representing a function call."""
    caller: str
    callee: str
    file_path: str
    line_number: int


@dataclass
class TestInfo:
    """Factual information about a discovered test."""
    file_path: str
    test_name: str
    line_number: int
    framework: str
    test_class: str | None = None
    referenced_symbols: list[str] = field(default_factory=list)


@dataclass
class TestsReport:
    """Report of all discovered tests and frameworks."""
    test_files: list[str] = field(default_factory=list)
    tests: list[TestInfo] = field(default_factory=list)
    frameworks_detected: list[str] = field(default_factory=list)


@dataclass
class CommitInfo:
    """Factual information about a Git commit."""
    commit_hash: str
    author_name: str
    author_email: str
    timestamp: str
    message: str
    files_changed: list[str] = field(default_factory=list)


@dataclass
class FileContribution:
    """Factual author contribution percentage for a file."""
    author: str
    commit_count: int
    percentage: float


@dataclass
class FileGitHistory:
    """Factual Git history for an individual file."""
    file_path: str
    commits: list[str] = field(default_factory=list)
    contributors: list[FileContribution] = field(default_factory=list)
    total_commits: int = 0


@dataclass
class GitHistoryReport:
    """Consolidated Git history and contributor facts."""
    is_git_repo: bool = False
    total_commits: int = 0
    commits: list[CommitInfo] = field(default_factory=list)
    file_histories: dict[str, FileGitHistory] = field(default_factory=dict)
    error: str | None = None


@dataclass
class RepositoryAnalysisReport:
    """Top-level consolidated forensic facts about a repository."""
    repo_path: str
    total_files: int = 0
    python_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    parsed_files: dict[str, ParsedFile] = field(default_factory=dict)
    parse_errors: list[ParseError] = field(default_factory=list)
    dependencies: DependenciesReport = field(default_factory=DependenciesReport)
    call_graph_nodes: int = 0
    call_graph_edges: int = 0
    tests: TestsReport = field(default_factory=TestsReport)
    git_history: GitHistoryReport = field(default_factory=GitHistoryReport)
