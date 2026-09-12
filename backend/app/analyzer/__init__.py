"""CodeWitness Forensic Analyzer Module.

Collects factual structural, dependency, test, and Git history information about a repository.
Does NOT make forensic decisions, calculate risk scores, or assert severity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .call_graph import CallGraph, CallGraphBuilder
from .dependencies import DependencyAnalyzer
from .git_history import GitHistoryAnalyzer
from .models import (
    CallInfo,
    CallRelationship,
    ClassInfo,
    CommitInfo,
    DependenciesReport,
    DependencyInfo,
    FileContribution,
    FileGitHistory,
    FunctionInfo,
    GitHistoryReport,
    ImportInfo,
    LocalDependencyInfo,
    ParsedFile,
    ParseError,
    RepositoryAnalysisReport,
    TestInfo,
    TestsReport,
)
from .parser import PythonParser, SourceParser
from .repository import RepositoryAnalyzer
from .tests import TestAnalyzer, TestDiscovery


class CodeWitnessAnalyzer:
    """Orchestrates all factual analyzer modules across a repository."""

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.repo_analyzer = RepositoryAnalyzer(self.repo_path)
        self.parser = SourceParser()
        self.dep_analyzer = DependencyAnalyzer(self.repo_path)
        self.call_graph_builder = CallGraphBuilder()
        self.test_analyzer = TestAnalyzer(parser=self.parser)
        self.git_analyzer = GitHistoryAnalyzer(self.repo_path)

    def analyze(self) -> RepositoryAnalysisReport:
        """Run all analyzer components and compile factual repository report."""
        # 1. Discover files
        discovered_files = self.repo_analyzer.discover_files()
        python_files = self.repo_analyzer.get_python_files()
        test_files = self.repo_analyzer.get_test_files()

        # 2. Parse source files
        parsed_files_map: dict[str, ParsedFile] = {}
        all_errors: list[ParseError] = []

        for rel_path in python_files:
            abs_path = self.repo_path / rel_path
            pf = self.parser.parse_file(abs_path, base_path=self.repo_path)
            parsed_files_map[str(rel_path).replace("\\", "/")] = pf
            all_errors.extend(pf.errors)

        parsed_list = list(parsed_files_map.values())

        # 3. Analyze dependencies
        dep_report = self.dep_analyzer.analyze(parsed_list, repo_path=self.repo_path)

        # 4. Build call graph
        call_graph = self.call_graph_builder.build(parsed_list)

        # 5. Discover tests
        test_parsed = [
            parsed_files_map[str(tf).replace("\\", "/")]
            for tf in test_files
            if str(tf).replace("\\", "/") in parsed_files_map
        ]
        test_report = self.test_analyzer.analyze(test_parsed)

        # 6. Analyze Git history
        git_report = self.git_analyzer.analyze()

        return RepositoryAnalysisReport(
            repo_path=str(self.repo_path).replace("\\", "/"),
            total_files=len(discovered_files),
            python_files=[str(p).replace("\\", "/") for p in python_files],
            test_files=[str(t).replace("\\", "/") for t in test_files],
            parsed_files=parsed_files_map,
            parse_errors=all_errors,
            dependencies=dep_report,
            call_graph_nodes=call_graph.node_count,
            call_graph_edges=call_graph.edge_count,
            tests=test_report,
            git_history=git_report,
        )


def analyze_repository(repo_path: str | Path) -> RepositoryAnalysisReport:
    """Convenience function to run the full CodeWitness analyzer pipeline."""
    return CodeWitnessAnalyzer(repo_path).analyze()


__all__ = [
    "RepositoryAnalyzer",
    "SourceParser",
    "PythonParser",
    "DependencyAnalyzer",
    "CallGraph",
    "CallGraphBuilder",
    "TestAnalyzer",
    "TestDiscovery",
    "GitHistoryAnalyzer",
    "CodeWitnessAnalyzer",
    "analyze_repository",
    "ParseError",
    "ImportInfo",
    "FunctionInfo",
    "ClassInfo",
    "CallInfo",
    "ParsedFile",
    "DependencyInfo",
    "LocalDependencyInfo",
    "DependenciesReport",
    "CallRelationship",
    "TestInfo",
    "TestsReport",
    "CommitInfo",
    "FileContribution",
    "FileGitHistory",
    "GitHistoryReport",
    "RepositoryAnalysisReport",
]
