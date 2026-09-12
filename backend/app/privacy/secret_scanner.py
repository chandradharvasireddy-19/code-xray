import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DetectedSecret:
    file: str
    line: int
    secret_type: str                         # 'api_key', 'token', 'password', 'private_key', 'connection_string', 'credential'
    confidence: float                        # 0.0 to 1.0
    snippet_preview: str                     # Redacted preview for logging
    raw_match: str                           # Raw secret text (for exact redacting)

    def to_dict(self, include_raw: bool = False) -> Dict[str, Any]:
        data = {
            "file": self.file,
            "line": self.line,
            "secret_type": self.secret_type,
            "confidence": self.confidence,
            "snippet_preview": self.snippet_preview,
        }
        if include_raw:
            data["raw_match"] = self.raw_match
        return data


class SecretScanner:
    """
    Practical heuristic and regex-based scanner for sensitive credentials,
    keys, tokens, and database connection strings.
    """

    PATTERNS = [
        # Private Keys
        (r"-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP)? PRIVATE KEY-----", "private_key", 0.98),
        # AWS Access Key
        (r"\b(AKIA[0-9A-Z]{16})\b", "api_key", 0.95),
        # GitHub Personal Access Token
        (r"\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{82})\b", "token", 0.98),
        # Generic Bearer / API Token
        (r"(?i)\b(?:api[_-]?key|access[_-]?token|secret[_-]?token|auth[_-]?token)\s*[:=]\s*['\"]([a-zA-Z0-9_\-\.]{16,64})['\"]", "api_key", 0.85),
        # Passwords in connection / config strings
        (r"(?i)\b(?:password|passwd|pwd)\s*[:=]\s*['\"]([^'\"\s]{6,40})['\"]", "password", 0.80),
        # Database Connection Strings
        (r"(?i)(?:postgres|postgresql|mysql|mongodb(?:\+srv)?|redis):\/\/[a-zA-Z0-9_\-]+:([^@\s]+)@[a-zA-Z0-9_\-\.:]+", "connection_string", 0.92),
        # Slack webhook / bot token
        (r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,34}", "token", 0.96),
        # Stripe API Key
        (r"\b(?:sk|pk)_(?:test|live)_[0-9a-zA-Z]{24,99}\b", "api_key", 0.95),
        # OpenAI API Key
        (r"\bsk-[a-zA-Z0-9]{32,64}\b", "api_key", 0.95),
    ]

    IGNORE_DIRS = {
        ".git", ".svn", "__pycache__", "node_modules", ".venv", "venv",
        "dist", "build", ".pytest_cache"
    }

    IGNORE_FILES = {
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"
    }

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()

    def scan(self) -> List[DetectedSecret]:
        secrets: List[DetectedSecret] = []
        if not self.repo_path.exists():
            return secrets

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.startswith(".")]

            for f_name in files:
                if f_name in self.IGNORE_FILES:
                    continue

                full_p = Path(root) / f_name
                rel_p = full_p.relative_to(self.repo_path).as_posix()

                # Skip binaries / large files (> 2MB)
                try:
                    if full_p.stat().st_size > 2 * 1024 * 1024:
                        continue
                except OSError:
                    continue

                try:
                    with open(full_p, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                except Exception:
                    continue

                for line_idx, line in enumerate(lines, start=1):
                    # Skip sample/template lines
                    if "example" in line.lower() or "your_" in line.lower() or "placeholder" in line.lower():
                        continue

                    for pattern, secret_type, confidence in self.PATTERNS:
                        matches = re.finditer(pattern, line)
                        for m in matches:
                            raw_val = m.group(1) if m.groups() else m.group(0)
                            if len(raw_val) < 6:
                                continue

                            # Create safe preview
                            preview = raw_val[:3] + "..." + raw_val[-3:] if len(raw_val) > 8 else "***"
                            snippet = line.strip().replace(raw_val, f"[REDACTED:{secret_type.upper()}]")

                            secrets.append(DetectedSecret(
                                file=rel_p,
                                line=line_idx,
                                secret_type=secret_type,
                                confidence=confidence,
                                snippet_preview=snippet[:120],
                                raw_match=raw_val,
                            ))

        return secrets
