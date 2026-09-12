from src.auth.token_validator import TokenValidator


class AuthService:
    """
    Handles payment transaction authentication and authorization.
    """

    def __init__(self, validator: TokenValidator = None):
        self.validator = validator or TokenValidator()

    def authenticate_transaction(self, user_id: str, token: str) -> bool:
        """
        Verify that the user transaction token is valid and active.
        """
        if not user_id:
            return False
        return self.validator.validate_token(token)
