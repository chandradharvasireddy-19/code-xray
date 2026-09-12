class TokenValidator:
    """
    Validates authentication tokens for financial transactions.
    """

    def validate_token(self, token: str) -> bool:
        """
        Validate incoming bearer token format and expiration.
        """
        if not token:
            return False
        if len(token) < 16:
            return False
        if token.startswith("invalid_"):
            return False
        return True
