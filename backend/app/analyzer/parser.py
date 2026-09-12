from __future__ import annotations

import ast
from pathlib import Path
from typing import Sequence

from .models import CallInfo, ClassInfo, FunctionInfo, ImportInfo, ParsedFile, ParseError


class _ASTExtractor(ast.NodeVisitor):
    """AST visitor that extracts factual structural elements from Python code."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.imports: list[ImportInfo] = []
        self.functions: list[FunctionInfo] = []
        self.classes: list[ClassInfo] = []
        self.calls: list[CallInfo] = []

        # Scope tracking
        self._current_class: str | None = None
        self._current_function: str | None = None

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    file_path=self.file_path,
                    module=alias.name,
                    name=None,
                    alias=alias.asname,
                    line_number=node.lineno,
                    is_from_import=False,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        prefix = "." * node.level if node.level else ""
        module_name = prefix + (node.module or "")
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    file_path=self.file_path,
                    module=module_name,
                    name=alias.name,
                    alias=alias.asname,
                    line_number=node.lineno,
                    is_from_import=True,
                )
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        prev_class = self._current_class
        self._current_class = node.name

        base_classes: list[str] = []
        for base in node.bases:
            try:
                base_classes.append(ast.unparse(base))
            except Exception:
                base_classes.append("<complex>")

        methods: list[str] = [
            item.name
            for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        self.classes.append(
            ClassInfo(
                name=node.name,
                file_path=self.file_path,
                line_number=node.lineno,
                base_classes=base_classes,
                methods=methods,
            )
        )

        # Visit class body
        self.generic_visit(node)
        self._current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_function(node, is_async=True)

    def _handle_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_async: bool,
    ) -> None:
        args_list = [arg.arg for arg in node.args.args]
        is_method = self._current_class is not None

        func_info = FunctionInfo(
            name=node.name,
            file_path=self.file_path,
            line_number=node.lineno,
            arguments=args_list,
            is_method=is_method,
            class_name=self._current_class,
            is_async=is_async,
        )
        self.functions.append(func_info)

        prev_function = self._current_function
        if is_method and self._current_class:
            self._current_function = f"{self._current_class}.{node.name}"
        else:
            self._current_function = node.name

        self.generic_visit(node)
        self._current_function = prev_function

    def visit_Call(self, node: ast.Call) -> None:
        try:
            callee_repr = ast.unparse(node.func)
        except Exception:
            callee_repr = "<complex_call>"

        caller = self._current_function if self._current_function else "<module>"

        self.calls.append(
            CallInfo(
                caller=caller,
                callee=callee_repr,
                file_path=self.file_path,
                line_number=node.lineno,
                caller_class=self._current_class,
            )
        )
        self.generic_visit(node)


class SourceParser:
    """Parses Python source files using standard library `ast`."""

    def parse_source(self, code: str, file_path: str = "<unknown>") -> ParsedFile:
        """Parse Python source code string into a structured ParsedFile model."""
        try:
            tree = ast.parse(code, filename=file_path)
        except SyntaxError as err:
            error = ParseError(
                file_path=file_path,
                error_message=str(err.msg),
                line_number=err.lineno,
            )
            return ParsedFile(file_path=file_path, errors=[error])
        except Exception as err:
            error = ParseError(
                file_path=file_path,
                error_message=str(err),
                line_number=None,
            )
            return ParsedFile(file_path=file_path, errors=[error])

        extractor = _ASTExtractor(file_path=file_path)
        extractor.visit(tree)

        return ParsedFile(
            file_path=file_path,
            imports=extractor.imports,
            functions=extractor.functions,
            classes=extractor.classes,
            calls=extractor.calls,
            errors=[],
        )

    def parse_file(self, file_path: str | Path, base_path: str | Path | None = None) -> ParsedFile:
        """Parse a single Python file from disk.

        Args:
            file_path: Absolute or relative path to the Python file.
            base_path: Optional repository base path to compute a relative file_path in reports.

        Returns:
            A ParsedFile containing extracted facts or recorded parse errors.
        """
        path = Path(file_path)
        display_path = (
            str(path.relative_to(base_path)).replace("\\", "/")
            if base_path and path.is_relative_to(base_path)
            else str(path).replace("\\", "/")
        )

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as err:
            return ParsedFile(
                file_path=display_path,
                errors=[ParseError(file_path=display_path, error_message=f"Failed to read file: {err}")],
            )

        return self.parse_source(content, file_path=display_path)

    def parse_files(
        self,
        file_paths: Sequence[str | Path],
        base_path: str | Path | None = None,
    ) -> list[ParsedFile]:
        """Parse multiple Python files sequentially, continuing on syntax errors.

        Args:
            file_paths: Collection of file paths to parse.
            base_path: Optional repository base path to make reported file paths relative.

        Returns:
            List of ParsedFile instances corresponding to each input file.
        """
        return [self.parse_file(fp, base_path=base_path) for fp in file_paths]


# Convenient alias
PythonParser = SourceParser
