from typing import Dict, Any
from src.services.auth_service import AuthService
from src.repositories.payment_repository import PaymentRepository
from src.models.payment_model import PaymentRecord


class PaymentService:
    """
    Business service coordinating payment execution, validation, and storage.
    """

    def __init__(
        self,
        auth_service: AuthService = None,
        payment_repo: PaymentRepository = None,
    ):
        self.auth_service = auth_service or AuthService()
        self.payment_repo = payment_repo or PaymentRepository()

    def process_payment(self, user_id: str, amount: float, token: str) -> Dict[str, Any]:
        """
        Processes payment by validating token and committing record to database.
        """
        # Validate authentication flow
        is_authenticated = self.auth_service.authenticate_transaction(user_id, token)
        if not is_authenticated:
            raise PermissionError("Payment authentication failed: invalid or expired token.")

        if amount <= 0:
            raise ValueError("Payment amount must be positive.")

        # Persist transaction
        record: PaymentRecord = self.payment_repo.save_payment(user_id=user_id, amount=amount, status="success")
        return {
            "payment_id": record.payment_id,
            "status": "approved",
            "amount": record.amount,
            "timestamp": record.timestamp,
        }
