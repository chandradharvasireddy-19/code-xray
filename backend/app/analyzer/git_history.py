import os
import re
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from app.models.repository import CommitMeta, ContributorMeta, FileMeta


class GitHistoryAnalyzer:
    """
    Mines Git commit history, file churn, author contributions, and ownership concentration.
    Degrades gracefully if Git is not installed or the directory is not a Git repository.
    """

    def __init__(self, repo_path: str, max_commits: int = 200):
        self.repo_path = Path(repo_path).resolve()
        self.max_commits = max_commits
        self.is_git_repo = (self.repo_path / ".git").exists()

    def analyze(self) -> Tuple[List[CommitMeta], Dict[str, ContributorMeta], Dict[str, Dict[str, Any]], bool]:
        """
        Returns:
            - List of CommitMeta objects
            - Map of author_name -> ContributorMeta
            - Map of rel_file_path -> Git file stats dict (commits, top_author, ownership, churn)
            - is_data_incomplete boolean
        """
        if not self.is_git_repo:
            return [], {}, {}, True

        commits: List[CommitMeta] = []
        contributors: Dict[str, ContributorMeta] = {}
        file_stats: Dict[str, Dict[str, Any]] = {}

        try:
            # Run git log with custom separator and name-status
            cmd = [
                "git", "-C", str(self.repo_path), "log",
                f"-n{self.max_commits}",
                "--pretty=format:COMMIT_START%n%H%n%an%n%ad%n%s",
                "--date=iso",
                "--name-only",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )

            if result.returncode != 0 or not result.stdout.strip():
                return [], {}, {}, True

            raw_blocks = result.stdout.split("COMMIT_START\n")
            
            # File -> Dict[author, count]
            file_authors: Dict[str, Dict[str, int]] = {}
            # File -> total commits
            file_commit_counts: Dict[str, int] = {}
            # File -> recent commits
            file_recent_counts: Dict[str, int] = {}

            now = datetime.now(timezone.utc)
            ninety_days_ago = now - timedelta(days=90)

            for block in raw_blocks:
                if not block.strip():
                    continue
                lines = block.strip().splitlines()
                if len(lines) < 4:
                    continue

                commit_hash = lines[0].strip()
                author = lines[1].strip()
                date_str = lines[2].strip()
                subject = lines[3].strip()
                changed_files = [l.strip().replace("\\", "/") for l in lines[4:] if l.strip()]

                # Parse date
                is_recent = False
                try:
                    commit_dt = datetime.fromisoformat(date_str)
                    if commit_dt.tzinfo is None:
                        commit_dt = commit_dt.replace(tzinfo=timezone.utc)
                    if commit_dt >= ninety_days_ago:
                        is_recent = True
                except Exception:
                    pass

                commits.append(CommitMeta(
                    hash=commit_hash,
                    author=author,
                    date=date_str,
                    message=subject,
                    changed_files=changed_files,
                ))

                # Track contributors
                if author not in contributors:
                    contributors[author] = ContributorMeta(name=author, commit_count=0, files_touched=[])
                contributors[author].commit_count += 1
                for cf in changed_files:
                    if cf not in contributors[author].files_touched:
                        contributors[author].files_touched.append(cf)

                    # Track file stats
                    if cf not in file_authors:
                        file_authors[cf] = {}
                        file_commit_counts[cf] = 0
                        file_recent_counts[cf] = 0

                    file_commit_counts[cf] += 1
                    file_authors[cf][author] = file_authors[cf].get(author, 0) + 1
                    if is_recent:
                        file_recent_counts[cf] += 1

            # Compute concentration & ownership per file
            for f_path, a_counts in file_authors.items():
                total_c = file_commit_counts[f_path]
                sorted_authors = sorted(a_counts.items(), key=lambda x: x[1], reverse=True)
                top_author, top_author_count = sorted_authors[0]
                ownership_pct = round(top_author_count / total_c, 2) if total_c > 0 else 0.0

                churn_level = "low"
                if total_c >= 20:
                    churn_level = "high"
                elif total_c >= 7:
                    churn_level = "medium"

                file_stats[f_path] = {
                    "total_commits": total_c,
                    "recent_commits": file_recent_counts.get(f_path, 0),
                    "contributor_count": len(a_counts),
                    "primary_contributor": top_author,
                    "top_contributor_ownership": ownership_pct,
                    "commits_by_contributor": a_counts,
                    "churn": churn_level,
                }

            return commits, contributors, file_stats, False

        except Exception:
            return [], {}, {}, True
