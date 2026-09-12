from typing import Dict, Any
from src.services.payment_service import PaymentService
# ARCHITECTURE VIOLATION: Controller directly imports Repository, bypassing Service layer!
from src.repositories.payment_repository import PaymentRepository


class PaymentController:
    """
    HTTP Controller handling incoming payment requests.
    """

    def __init__(
        self,
        payment_service: PaymentService = None,
        payment_repo: PaymentRepository = None,
    ):
        self.service = payment_service or PaymentService()
        self.repo = payment_repo or PaymentRepository()

    def handle_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receives payment submission from API client.
        """
        user_id = payload.get("user_id")
        amount = payload.get("amount", 0.0)
        token = payload.get("token", "")

        return self.service.process_payment(user_id=user_id, amount=amount, token=token)

    def check_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Directly queries database repository, violating Controller -> Service -> Repository hierarchy.
        """
        record = self.repo.get_payment(payment_id)
        if not record:
            return {"status": "not_found"}
        return {"payment_id": record.payment_id, "status": record.status}
