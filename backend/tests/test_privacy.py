import pytest
from app.privacy.secret_scanner import SecretScanner
from app.privacy.redactor import SecretRedactor
from app.privacy.context_filter import ContextFilter


def test_secret_scanner_detection(tmp_path):
    config_file = tmp_path / "config.env"
    config_file.write_text(
        "API_KEY='sk-1234567890abcdef1234567890abcdef'\n"
        "GITHUB_TOKEN='ghp_1234567890abcdefghijklmnopqrstuvwxyz'\n",
        encoding="utf-8",
    )

    scanner = SecretScanner(str(tmp_path))
    secrets = scanner.scan()

    assert len(secrets) >= 2
    types = [s.secret_type for s in secrets]
    assert "api_key" in types
    assert "token" in types


def test_secret_redactor():
    redactor = SecretRedactor()
    raw = "My OpenAI key is sk-abcdef1234567890abcdef1234567890 and pass is password='secretPassword123'"
    redacted = redactor.redact_text(raw)

    assert "sk-abcdef" not in redacted
    assert "[REDACTED:API_KEY]" in redacted
    assert "secretPassword123" not in redacted


def test_context_filter():
    filter_engine = ContextFilter()
    sample_finding = {
        "title": "Secret in code",
        "finding_type": "security",
        "affected_file": "app.py",
        "description": "Found key sk-abcdef1234567890abcdef1234567890 in config",
        "evidence_chain": [],
    }
    filtered = filter_engine.filter_finding_context(sample_finding)

    assert "sk-abcdef" not in filtered["description"]
    assert "[REDACTED:API_KEY]" in filtered["description"]
