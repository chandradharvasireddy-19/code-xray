import pytest
from app.analyzer.parser import PythonASTParser
from app.analyzer.dependencies import DependencyAnalyzer
from app.analyzer.call_graph import CallGraphBuilder
from app.analyzer.tests import TestAnalyzer
from app.models.repository import CodeEntity, Relationship


def test_ast_parser(tmp_path):
    code_file = tmp_path / "auth.py"
    code_file.write_text(
        "import os\n"
        "from typing import List\n\n"
        "class AuthService:\n"
        "    def authenticate(self, token: str) -> bool:\n"
        "        return self.verify(token)\n\n"
        "    def verify(self, token: str) -> bool:\n"
        "        return bool(token)\n",
        encoding="utf-8",
    )

    parser = PythonASTParser(str(tmp_path))
    entities, imports = parser.parse_file("auth.py")

    entity_names = [e.name for e in entities]
    assert "AuthService" in entity_names
    assert "authenticate" in entity_names
    assert "verify" in entity_names
    assert len(imports) >= 2


def test_dependency_analyzer():
    files = ["src/controller.py", "src/service.py"]
    analyzer = DependencyAnalyzer(files)

    from app.analyzer.parser import ImportStatement
    imports = [ImportStatement(module="src.service", names=["MyService"], is_from=True)]
    rels, ext = analyzer.analyze_file_imports("src/controller.py", imports)

    assert len(rels) == 1
    assert rels[0].source == "src/controller.py"
    assert rels[0].target == "src/service.py"


def test_call_graph_builder():
    entities = {
        "src/auth.py:AuthService.authenticate": CodeEntity(
            id="src/auth.py:AuthService.authenticate",
            type="method",
            name="authenticate",
            file="src/auth.py",
            calls=["self.verify"],
        ),
        "src/auth.py:AuthService.verify": CodeEntity(
            id="src/auth.py:AuthService.verify",
            type="method",
            name="verify",
            file="src/auth.py",
        ),
    }

    builder = CallGraphBuilder(entities, [])
    edges = builder.build()

    assert len(edges) == 1
    assert edges[0].source == "src/auth.py:AuthService.authenticate"
    assert edges[0].target == "src/auth.py:AuthService.verify"


def test_test_analyzer():
    test_files = ["tests/test_auth.py"]
    source_files = ["src/auth.py"]
    deps = [
        Relationship(source="tests/test_auth.py", target="src/auth.py", type="imports", confidence=0.9)
    ]

    analyzer = TestAnalyzer(test_files, source_files, {}, deps, [])
    test_rels, tested_map, untested = analyzer.analyze()

    assert len(test_rels) == 1
    assert "src/auth.py" in tested_map
    assert untested == []
