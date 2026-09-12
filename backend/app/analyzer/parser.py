import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from app.models.repository import CodeEntity


class ImportStatement:
    def __init__(
        self,
        module: Optional[str],
        names: List[str],
        level: int = 0,
        line: int = 1,
        is_from: bool = False,
    ):
        self.module = module
        self.names = names
        self.level = level                   # Relative import dot count (0 = absolute, 1 = ., 2 = ..)
        self.line = line
        self.is_from = is_from

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": self.module,
            "names": self.names,
            "level": self.level,
            "line": self.line,
            "is_from": self.is_from,
        }


class PythonASTParser:
    """
    Parses Python source files using standard library `ast`.
    Extracts structured CodeEntity instances, class inheritance, decorators,
    docstrings, function calls, and import statements.
    """

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.parse_errors: List[Dict[str, Any]] = []

    def parse_file(self, rel_path: str) -> Tuple[List[CodeEntity], List[ImportStatement]]:
        """
        Parse a single python file and return its entities and imports.
        """
        full_path = self.repo_path / rel_path
        if not full_path.exists():
            return [], []

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                source_text = f.read()
        except Exception as e:
            self.parse_errors.append({"file": rel_path, "error": f"Read error: {str(e)}"})
            return [], []

        try:
            tree = ast.parse(source_text, filename=rel_path)
        except SyntaxError as e:
            self.parse_errors.append({
                "file": rel_path,
                "line": e.lineno,
                "error": f"SyntaxError: {e.msg}",
            })
            return [], []
        except Exception as e:
            self.parse_errors.append({
                "file": rel_path,
                "error": f"AST parse error: {str(e)}",
            })
            return [], []

        entities: List[CodeEntity] = []
        imports: List[ImportStatement] = []

        is_test_file = "test" in rel_path.lower()

        # 1. Module level entity
        docstring = ast.get_docstring(tree)
        module_entity = CodeEntity(
            id=rel_path,
            type="file",
            name=Path(rel_path).name,
            file=rel_path,
            line_start=1,
            line_end=len(source_text.splitlines()) if source_text else 1,
            docstring=docstring,
            is_test=is_test_file,
        )
        entities.append(module_entity)

        # 2. Walk AST nodes
        for node in tree.body:
            # Imports
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
                imports.append(ImportStatement(
                    module=None,
                    names=names,
                    level=0,
                    line=node.lineno,
                    is_from=False,
                ))
            elif isinstance(node, ast.ImportFrom):
                names = [alias.name for alias in node.names]
                imports.append(ImportStatement(
                    module=node.module,
                    names=names,
                    level=node.level,
                    line=node.lineno,
                    is_from=True,
                ))

            # Classes
            elif isinstance(node, ast.ClassDef):
                class_entities = self._extract_class(node, rel_path, is_test_file)
                entities.extend(class_entities)

            # Top-level Functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_entity = self._extract_function(node, rel_path, parent_class=None, is_test_file=is_test_file)
                entities.append(func_entity)

        return entities, imports

    def _extract_class(
        self,
        node: ast.ClassDef,
        rel_path: str,
        is_test_file: bool,
    ) -> List[CodeEntity]:
        results: List[CodeEntity] = []

        bases = [self._get_name(base) for base in node.bases]
        decorators = [self._get_name(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)
        class_id = f"{rel_path}:{node.name}"

        is_test = is_test_file or "TestCase" in bases or node.name.startswith("Test")

        class_entity = CodeEntity(
            id=class_id,
            type="class",
            name=node.name,
            file=rel_path,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
            docstring=docstring,
            decorators=decorators,
            bases=bases,
            is_test=is_test,
        )
        results.append(class_entity)

        # Methods inside class
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_entity = self._extract_function(
                    item,
                    rel_path,
                    parent_class=node.name,
                    is_test_file=is_test,
                )
                results.append(method_entity)

        return results

    def _extract_function(
        self,
        node: Any,
        rel_path: str,
        parent_class: Optional[str],
        is_test_file: bool,
    ) -> CodeEntity:
        name = node.name
        is_method = parent_class is not None
        entity_type = "method" if is_method else "function"

        if is_method:
            entity_id = f"{rel_path}:{parent_class}.{name}"
        else:
            entity_id = f"{rel_path}:{name}"

        decorators = [self._get_name(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)

        # Parameters
        params = [arg.arg for arg in node.args.args]

        # Extract function calls inside function body
        calls = self._extract_calls(node)

        is_test = is_test_file or name.startswith("test_") or "test" in decorators

        return CodeEntity(
            id=entity_id,
            type=entity_type,
            name=name,
            file=rel_path,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
            docstring=docstring,
            decorators=decorators,
            params=params,
            calls=calls,
            is_test=is_test,
        )

    def _extract_calls(self, root_node: ast.AST) -> List[str]:
        """
        Extract all function/method call names in an AST node.
        """
        calls: List[str] = []
        for n in ast.walk(root_node):
            if isinstance(n, ast.Call):
                name = self._get_name(n.func)
                if name:
                    calls.append(name)
        return list(dict.fromkeys(calls))

    def _get_name(self, node: ast.AST) -> str:
        """
        Safely resolve AST expression node into dotted string identifier.
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val = self._get_name(node.value)
            return f"{val}.{node.attr}" if val else node.attr
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        return ""
