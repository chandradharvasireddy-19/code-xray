from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .models import ParsedFile, TestInfo, TestsReport
from .parser import SourceParser


class TestAnalyzer:
    """Statically discovers tests, test frameworks, and referenced symbols without executing code."""

    __test__ = False

    def __init__(self, parser: SourceParser | None = None) -> None:
        self.parser = parser or SourceParser()

    def _is_unittest_class(self, base_classes: list[str]) -> bool:
        """Check if any base class indicates a unittest TestCase."""
        return any(
            base in ("TestCase", "unittest.TestCase", "django.test.TestCase")
            for base in base_classes
        )

    def analyze_file(self, parsed_file: ParsedFile) -> list[TestInfo]:
        """Discover tests within a single parsed test file."""
        tests: list[TestInfo] = []
        file_path = parsed_file.file_path

        # Map class names to their base classes
        class_bases = {cls.name: cls.base_classes for cls in parsed_file.classes}

        # Calls grouped by caller
        calls_by_caller: dict[str, list[str]] = {}
        for call in parsed_file.calls:
            calls_by_caller.setdefault(call.caller, []).append(call.callee)

        # Collect symbols imported into this test file
        imported_symbols: list[str] = [
            imp.name for imp in parsed_file.imports if imp.name
        ]

        for func in parsed_file.functions:
            is_unittest = False
            is_pytest = False
            framework = "unknown"

            # Check if inside a TestCase class
            if func.is_method and func.class_name:
                bases = class_bases.get(func.class_name, [])
                if self._is_unittest_class(bases) and func.name.startswith("test"):
                    is_unittest = True
                    framework = "unittest"
                elif func.name.startswith("test_") or func.name.endswith("_test"):
                    is_pytest = True
                    framework = "pytest"
            else:
                # Standalone test function
                if func.name.startswith("test_") or func.name.endswith("_test"):
                    is_pytest = True
                    framework = "pytest"

            if is_unittest or is_pytest:
                caller_key = f"{func.class_name}.{func.name}" if func.class_name else func.name
                callees_called = calls_by_caller.get(caller_key, [])

                # Referenced symbols: calls inside test + relevant imported symbols
                referenced: set[str] = set()
                for c in callees_called:
                    # Ignore standard assertions and self helper calls
                    if not c.startswith("self.assert") and not c.startswith("assert"):
                        referenced.add(c)

                # Add imported names if they appear in callees or arguments
                for imp_name in imported_symbols:
                    if any(imp_name in c for c in callees_called):
                        referenced.add(imp_name)

                tests.append(
                    TestInfo(
                        file_path=file_path,
                        test_name=func.name,
                        line_number=func.line_number,
                        framework=framework,
                        test_class=func.class_name,
                        referenced_symbols=sorted(referenced),
                    )
                )

        return tests

    def analyze(self, test_files: Sequence[str | Path | ParsedFile]) -> TestsReport:
        """Analyze a collection of test files and produce a consolidated TestsReport.

        Args:
            test_files: Sequence of file paths or pre-parsed ParsedFile instances.

        Returns:
            A TestsReport containing discovered tests and detected frameworks.
        """
        all_tests: list[TestInfo] = []
        frameworks: set[str] = set()
        recorded_files: list[str] = []

        for item in test_files:
            if isinstance(item, ParsedFile):
                pf = item
            else:
                pf = self.parser.parse_file(item)

            recorded_files.append(pf.file_path)
            tests = self.analyze_file(pf)
            all_tests.extend(tests)

            for t in tests:
                if t.framework != "unknown":
                    frameworks.add(t.framework)

        return TestsReport(
            test_files=sorted(recorded_files),
            tests=all_tests,
            frameworks_detected=sorted(frameworks),
        )


# Convenient alias
TestDiscovery = TestAnalyzer
