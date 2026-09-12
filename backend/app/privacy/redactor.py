import re
from typing import Any, Dict, List, Optional
from app.privacy.secret_scanner import DetectedSecret


class SecretRedactor:
    """
    Redacts detected secrets and known sensitive tokens from text strings,
    dictionaries, and context payloads before passing them to external layers.
    """

    def __init__(self, detected_secrets: Optional[List[DetectedSecret]] = None):
        self.known_secrets = detected_secrets or []

    def redact_text(self, text: str) -> str:
        if not text:
            return text

        result = text
        # Redact specific scanned secrets
        for s in self.known_secrets:
            if s.raw_match and s.raw_match in result:
                result = result.replace(s.raw_match, f"[REDACTED:{s.secret_type.upper()}]")

        # Generic pattern redactions for any unindexed inline secrets
        result = re.sub(
            r"\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{82})\b",
            "[REDACTED:TOKEN]",
            result,
        )
        result = re.sub(
            r"\b(AKIA[0-9A-Z]{16})\b",
            "[REDACTED:API_KEY]",
            result,
        )
        result = re.sub(
            r"\bsk-[a-zA-Z0-9]{32,64}\b",
            "[REDACTED:API_KEY]",
            result,
        )
        result = re.sub(
            r"(?i)(?:password|passwd|pwd)\s*[:=]\s*['\"]([^'\"\s]{6,40})['\"]",
            r"password='[REDACTED:PASSWORD]'",
            result,
        )

        return result

    def redact_structure(self, data: Any) -> Any:
        """
        Recursively redacts dictionary keys or string values.
        """
        if isinstance(data, str):
            return self.redact_text(data)
        elif isinstance(data, list):
            return [self.redact_structure(item) for item in data]
        elif isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                if any(sens in k.lower() for sens in ["secret", "password", "token", "auth_header", "private_key"]):
                    new_dict[k] = "[REDACTED]"
                else:
                    new_dict[k] = self.redact_structure(v)
            return new_dict
        return data
