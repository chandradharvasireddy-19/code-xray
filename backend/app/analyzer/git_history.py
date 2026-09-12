from __future__ import annotations

from pathlib import Path
from typing import Sequence

try:
    import git
    from git.exc import GitError, InvalidGitRepositoryError, NoSuchPathError
except ImportError:
    git = None  # type: ignore
    GitError = Exception  # type: ignore
    InvalidGitRepositoryError = Exception  # type: ignore
    NoSuchPathError = Exception  # type: ignore

from .models import CommitInfo, FileContribution, FileGitHistory, GitHistoryReport


class GitHistoryAnalyzer:
    """Analyzes Git history and file contributor metrics using GitPython.

    Contribution calculation method:
    Contributor percentage is calculated as the ratio of commits touching a specific
    file authored by a given contributor to the total number of commits affecting that file:
        percentage = (author_commit_count / total_file_commits) * 100.0
    This represents factual authorship proportions without making forensic or risk claims.
    """

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path: Path = Path(repo_path).resolve()

    def analyze(self, max_commits: int | None = None) -> GitHistoryReport:
        """Analyze the repository's Git history.

        Args:
            max_commits: Optional cap on the number of commits to inspect.

        Returns:
            A GitHistoryReport containing commit details and file contributor statistics.
        """
        if git is None:
            return GitHistoryReport(
                is_git_repo=False,
                error="GitPython is not installed.",
            )

        try:
            repo = git.Repo(self.repo_path, search_parent_directories=True)
        except (InvalidGitRepositoryError, NoSuchPathError):
            return GitHistoryReport(
                is_git_repo=False,
                error="Repository path is not a valid Git repository.",
            )
        except Exception as err:
            return GitHistoryReport(
                is_git_repo=False,
                error=f"Failed to access Git repository: {err}",
            )

        # Check for empty repository (no commits yet)
        try:
            _ = repo.head.commit
        except (ValueError, Exception):
            repo.close()
            return GitHistoryReport(
                is_git_repo=True,
                total_commits=0,
                error="Git repository contains no commits yet.",
            )
        commits_list: list[CommitInfo] = []
        file_commit_map: dict[str, list[str]] = {}
        file_author_map: dict[str, dict[str, int]] = {}

        try:
            commit_iter = repo.iter_commits(max_count=max_commits)
            for commit in commit_iter:
                author_name = commit.author.name or "Unknown"
                author_email = commit.author.email or ""
                iso_timestamp = commit.committed_datetime.isoformat()
                message = commit.message.strip() if commit.message else ""

                # Determine files changed in this commit
                files_changed: list[str] = []
                if commit.parents:
                    diffs = commit.parents[0].diff(commit)
                    for d in diffs:
                        path_str = d.b_path or d.a_path
                        if path_str:
                            norm_path = path_str.replace("\\", "/")
                            files_changed.append(norm_path)
                else:
                    # Initial commit: all blobs in the tree
                    for item in commit.tree.traverse():
                        if item.type == "blob":
                            norm_path = item.path.replace("\\", "/")
                            files_changed.append(norm_path)

                commits_list.append(
                    CommitInfo(
                        commit_hash=commit.hexsha,
                        author_name=author_name,
                        author_email=author_email,
                        timestamp=iso_timestamp,
                        message=message,
                        files_changed=sorted(set(files_changed)),
                    )
                )

                for fpath in files_changed:
                    file_commit_map.setdefault(fpath, []).append(commit.hexsha)
                    author_counts = file_author_map.setdefault(fpath, {})
                    author_counts[author_name] = author_counts.get(author_name, 0) + 1

        except Exception as err:
            return GitHistoryReport(
                is_git_repo=True,
                total_commits=len(commits_list),
                commits=commits_list,
                error=f"Error reading commits: {err}",
            )
        finally:
            repo.close()

        # Calculate file contributor statistics
        file_histories: dict[str, FileGitHistory] = {}
        for fpath, commit_hashes in file_commit_map.items():
            total_file_commits = len(commit_hashes)
            author_counts = file_author_map.get(fpath, {})

            contributors: list[FileContribution] = []
            for author, count in author_counts.items():
                pct = (
                    round((count / total_file_commits) * 100.0, 1)
                    if total_file_commits > 0
                    else 0.0
                )
                contributors.append(
                    FileContribution(
                        author=author,
                        commit_count=count,
                        percentage=pct,
                    )
                )

            # Sort contributors by commit count descending
            contributors.sort(key=lambda c: c.commit_count, reverse=True)

            file_histories[fpath] = FileGitHistory(
                file_path=fpath,
                commits=commit_hashes,
                contributors=contributors,
                total_commits=total_file_commits,
            )

        return GitHistoryReport(
            is_git_repo=True,
            total_commits=len(commits_list),
            commits=commits_list,
            file_histories=file_histories,
            error=None,
        )
