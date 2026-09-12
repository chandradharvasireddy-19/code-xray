from pathlib import Path
from backend.app.analyzer.dependencies import DependencyAnalyzer
from backend.app.analyzer.parser import SourceParser


def test_declared_requirements_txt(tmp_path: Path):
    req_content = """
# Production requirements
requests>=2.28.0
numpy==1.24.0
pytest
fastapi[all]>=0.100.0
# End
"""
    (tmp_path / "requirements.txt").write_text(req_content, encoding="utf-8")

    analyzer = DependencyAnalyzer(tmp_path)
    pkgs = analyzer._parse_requirements_txt(tmp_path / "requirements.txt")

    assert "requests" in pkgs
    assert pkgs["requests"] == ">=2.28.0"
    assert "numpy" in pkgs
    assert pkgs["numpy"] == "==1.24.0"
    assert "pytest" in pkgs
    assert pkgs["pytest"] is None
    assert "fastapi" in pkgs


def test_declared_pyproject_toml(tmp_path: Path):
    toml_content = """
[project]
name = "demo"
dependencies = [
    "pydantic>=2.0.0",
    "uvicorn",
]
"""
    (tmp_path / "pyproject.toml").write_text(toml_content, encoding="utf-8")

    analyzer = DependencyAnalyzer(tmp_path)
    pkgs = analyzer._parse_pyproject_toml(tmp_path / "pyproject.toml")

    assert "pydantic" in pkgs
    assert pkgs["pydantic"] == ">=2.0.0"
    assert "uvicorn" in pkgs


def test_imported_vs_declared_reconciliation(tmp_path: Path):
    # Declared: requests, pandas
    (tmp_path / "requirements.txt").write_text("requests>=2.28.0\npandas\n", encoding="utf-8")

    # Code imports requests and httpx (httpx not declared; pandas not imported)
    code = """
import requests
import httpx
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="app.py")

    analyzer = DependencyAnalyzer(tmp_path)
    report = analyzer.analyze([pf])

    assert "requirements.txt" in report.declared_files_found

    dep_map = {d.name.lower(): d for d in report.dependencies}

    # requests: declared and imported
    assert "requests" in dep_map
    assert dep_map["requests"].declared is True
    assert dep_map["requests"].imported is True
    assert dep_map["requests"].source_file == "requirements.txt"

    # pandas: declared but not imported
    assert "pandas" in dep_map
    assert dep_map["pandas"].declared is True
    assert dep_map["pandas"].imported is False

    # httpx: imported but not declared
    assert "httpx" in dep_map
    assert dep_map["httpx"].declared is False
    assert dep_map["httpx"].imported is True


def test_stdlib_modules_filtered(tmp_path: Path):
    code = """
import os
import sys
import json
import math
import pathlib
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="script.py")

    analyzer = DependencyAnalyzer(tmp_path)
    report = analyzer.analyze([pf])

    # No external dependencies should be extracted for standard library modules
    ext_names = [d.name.lower() for d in report.dependencies]
    for std in ["os", "sys", "json", "math", "pathlib"]:
        assert std not in ext_names


def test_local_dependencies(tmp_path: Path):
    (tmp_path / "services").mkdir()
    (tmp_path / "services" / "payment.py").write_text("class PaymentService: pass\n", encoding="utf-8")

    code = """
from services.payment import PaymentService
from .helpers import format_data
"""
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="controllers/user.py")

    analyzer = DependencyAnalyzer(tmp_path)
    report = analyzer.analyze([pf])

    local_targets = [ld.target_module for ld in report.local_dependencies]
    assert "services.payment" in local_targets
    assert ".helpers" in local_targets


def test_missing_declared_files_graceful(tmp_path: Path):
    code = "import requests\n"
    parser = SourceParser()
    pf = parser.parse_source(code, file_path="main.py")

    analyzer = DependencyAnalyzer(tmp_path)
    report = analyzer.analyze([pf])

    assert len(report.declared_files_found) == 0
    assert len(report.dependencies) == 1
    assert report.dependencies[0].name == "requests"
    assert report.dependencies[0].declared is False
    assert report.dependencies[0].imported is True
