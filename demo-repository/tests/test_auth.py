from src.services.auth_service import AuthService
from src.auth.token_validator import TokenValidator


def test_auth_service_valid():
    auth = AuthService()
    is_valid = auth.authenticate_transaction("usr_123", "secure_valid_token_string_99")
    assert is_valid is True


def test_token_validator_empty():
    validator = TokenValidator()
    assert validator.validate_token("") is False
    assert validator.validate_token("short") is False
