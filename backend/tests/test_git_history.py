from pathlib import Path
import git
from backend.app.analyzer.git_history import GitHistoryAnalyzer


def test_non_git_directory(tmp_path: Path):
    analyzer = GitHistoryAnalyzer(tmp_path)
    report = analyzer.analyze()

    assert report.is_git_repo is False
    assert report.total_commits == 0
    assert report.error is not None
    assert "not a valid Git repository" in report.error


def test_empty_git_repository(tmp_path: Path):
    repo = git.Repo.init(tmp_path)
    try:
        analyzer = GitHistoryAnalyzer(tmp_path)
        report = analyzer.analyze()

        assert report.is_git_repo is True
        assert report.total_commits == 0
        assert report.error is not None
        assert "no commits" in report.error.lower()
    finally:
        repo.close()


def test_commit_extraction_and_metadata(tmp_path: Path):
    repo = git.Repo.init(tmp_path)
    try:
        author = git.Actor("Jane Doe", "jane@example.com")

        # Commit 1
        f1 = tmp_path / "app.py"
        f1.write_text("def run(): pass\n", encoding="utf-8")
        repo.index.add(["app.py"])
        repo.index.commit("Initial app commit", author=author, committer=author)

        # Commit 2
        f2 = tmp_path / "config.py"
        f2.write_text("DEBUG = True\n", encoding="utf-8")
        repo.index.add(["config.py"])
        repo.index.commit("Add config file", author=author, committer=author)

        analyzer = GitHistoryAnalyzer(tmp_path)
        report = analyzer.analyze()

        assert report.is_git_repo is True
        assert report.total_commits == 2
        assert len(report.commits) == 2

        latest = report.commits[0]
        assert latest.author_name == "Jane Doe"
        assert latest.author_email == "jane@example.com"
        assert latest.message == "Add config file"
        assert "config.py" in latest.files_changed
        assert latest.timestamp is not None
    finally:
        repo.close()


def test_file_contributor_percentages(tmp_path: Path):
    repo = git.Repo.init(tmp_path)
    try:
        alice = git.Actor("Alice", "alice@example.com")
        bob = git.Actor("Bob", "bob@example.com")

        # Commit 1 by Alice on payment.py
        p_file = tmp_path / "payment.py"
        p_file.write_text("def pay(): pass\n", encoding="utf-8")
        repo.index.add(["payment.py"])
        repo.index.commit("Alice: create payment", author=alice, committer=alice)

        # Commit 2 by Bob on payment.py
        p_file.write_text("def pay(): return True\n", encoding="utf-8")
        repo.index.add(["payment.py"])
        repo.index.commit("Bob: modify payment", author=bob, committer=bob)

        # Commit 3 by Alice on payment.py
        p_file.write_text("def pay(): return False\n", encoding="utf-8")
        repo.index.add(["payment.py"])
        repo.index.commit("Alice: fix payment", author=alice, committer=alice)

        analyzer = GitHistoryAnalyzer(tmp_path)
        report = analyzer.analyze()

        assert "payment.py" in report.file_histories
        pay_hist = report.file_histories["payment.py"]
        assert pay_hist.total_commits == 3

        contrib_map = {c.author: (c.commit_count, c.percentage) for c in pay_hist.contributors}
        assert "Alice" in contrib_map
        assert "Bob" in contrib_map

        # Alice: 2 commits out of 3 -> 66.7%
        assert contrib_map["Alice"][0] == 2
        assert contrib_map["Alice"][1] == 66.7

        # Bob: 1 commit out of 3 -> 33.3%
        assert contrib_map["Bob"][0] == 1
        assert contrib_map["Bob"][1] == 33.3
    finally:
        repo.close()
