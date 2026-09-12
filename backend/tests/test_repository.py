from pathlib import Path
import pytest
from backend.app.analyzer.repository import RepositoryAnalyzer


def test_init_valid_directory(tmp_path: Path):
    analyzer = RepositoryAnalyzer(tmp_path)
    assert analyzer.repo_path == tmp_path.resolve()
    assert analyzer.repository_path == tmp_path.resolve()


def test_init_nonexistent_directory(tmp_path: Path):
    nonexistent = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        RepositoryAnalyzer(nonexistent)


def test_init_file_not_directory(tmp_path: Path):
    sample_file = tmp_path / "sample.txt"
    sample_file.touch()
    with pytest.raises(NotADirectoryError):
        RepositoryAnalyzer(sample_file)


def test_init_empty_path():
    with pytest.raises(ValueError):
        RepositoryAnalyzer("")


def test_discover_files_and_relative_paths(tmp_path: Path):
    (tmp_path / "root.py").touch()
    (tmp_path / "README.md").touch()
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.py").touch()

    analyzer = RepositoryAnalyzer(tmp_path)
    files = analyzer.discover_files()

    expected = sorted([
        Path("README.md"),
        Path("root.py"),
        Path("sub/nested.py"),
    ])
    assert files == expected
    # Also verify list_files alias
    assert analyzer.list_files() == expected


def test_ignored_directories_excluded(tmp_path: Path):
    # Create ignored directories and files inside them
    ignored_names = [".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"]
    for d_name in ignored_names:
        d_path = tmp_path / d_name
        d_path.mkdir()
        (d_path / "ignored.py").touch()

    # Create legitimate files
    (tmp_path / "valid.py").touch()
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "service.py").touch()

    analyzer = RepositoryAnalyzer(tmp_path)
    files = analyzer.discover_files()

    assert files == [Path("app/service.py"), Path("valid.py")]
    # Ensure no file has any ignored directory in its path components
    for f in files:
        for part in f.parts[:-1]:
            assert part not in analyzer.ignored_directories


def test_get_python_files(tmp_path: Path):
    (tmp_path / "main.py").touch()
    (tmp_path / "helper.py").touch()
    (tmp_path / "config.json").touch()
    (tmp_path / "README.md").touch()

    analyzer = RepositoryAnalyzer(tmp_path)
    py_files = analyzer.get_python_files()

    assert py_files == [Path("helper.py"), Path("main.py")]


def test_get_test_files(tmp_path: Path):
    # 1. files beginning with test_
    (tmp_path / "test_auth.py").touch()

    # 2. files ending with _test.py
    (tmp_path / "payment_test.py").touch()

    # 3. Python files inside a tests directory
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "conftest.py").touch()
    (tests_dir / "test_api.py").touch()
    (tests_dir / "fixture.json").touch()  # Not a Python file, must be excluded

    # Non-test files
    (tmp_path / "main.py").touch()
    (tmp_path / "auth.py").touch()

    analyzer = RepositoryAnalyzer(tmp_path)
    test_files = analyzer.get_test_files()

    expected = sorted([
        Path("payment_test.py"),
        Path("test_auth.py"),
        Path("tests/conftest.py"),
        Path("tests/test_api.py"),
    ])
    assert test_files == expected


def test_is_test_file_direct(tmp_path: Path):
    analyzer = RepositoryAnalyzer(tmp_path)

    assert analyzer.is_test_file(Path("test_service.py")) is True
    assert analyzer.is_test_file(Path("service_test.py")) is True
    assert analyzer.is_test_file(Path("tests/utils.py")) is True
    assert analyzer.is_test_file(Path("tests/data.txt")) is False
    assert analyzer.is_test_file(Path("app/main.py")) is False
