import os
from pathlib import Path
from typing import Dict, List, Tuple


class LanguageDetector:
    """
    Detects programming languages in a repository based on file extensions,
    excluding common ignore directories and calculating percentage distribution by byte size.
    """

    EXTENSION_MAP = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".c": "C",
        ".cpp": "C++",
        ".cc": "C++",
        ".cxx": "C++",
        ".h": "C/C++ Header",
        ".hpp": "C++ Header",
        ".cs": "C#",
        ".kt": "Kotlin",
        ".swift": "Swift",
        ".scala": "Scala",
        ".sh": "Shell",
        ".bash": "Shell",
        ".ps1": "PowerShell",
        ".html": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".sql": "SQL",
    }

    IGNORE_DIRS = {
        ".git", ".svn", ".hg", "__pycache__", ".pytest_cache",
        "node_modules", ".venv", "venv", "env", ".idea", ".vscode",
        "dist", "build", ".egg-info", ".tox", ".mypy_cache", "target"
    }

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()

    def detect(self) -> Dict[str, float]:
        """
        Calculates language distribution as normalized fractions (0.0 to 1.0)
        summing to 1.0, sorted from highest to lowest.
        """
        if not self.repo_path.exists():
            return {}

        lang_bytes: Dict[str, int] = {}
        total_bytes = 0

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.startswith(".")]

            for file_name in files:
                ext = Path(file_name).suffix.lower()
                lang = self.EXTENSION_MAP.get(ext)
                if lang:
                    full_p = Path(root) / file_name
                    try:
                        size = full_p.stat().st_size
                    except OSError:
                        size = 0
                    lang_bytes[lang] = lang_bytes.get(lang, 0) + size
                    total_bytes += size

        if total_bytes == 0:
            return {}

        distribution = {
            lang: round(bytes_count / total_bytes, 4)
            for lang, bytes_count in sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)
        }
        return distribution
