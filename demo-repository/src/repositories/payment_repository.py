import uuid
from datetime import datetime, timezone
from typing import Dict, Optional
from src.models.payment_model import PaymentRecord


class PaymentRepository:
    """
    Data access layer for payment transactions.
    """

    def __init__(self):
        self._db: Dict[str, PaymentRecord] = {}

    def save_payment(self, user_id: str, amount: float, status: str = "completed") -> PaymentRecord:
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        record = PaymentRecord(
            payment_id=payment_id,
            user_id=user_id,
            amount=amount,
            status=status,
            timestamp=now,
        )
        self._db[payment_id] = record
        return record

    def get_payment(self, payment_id: str) -> Optional[PaymentRecord]:
        return self._db.get(payment_id)
