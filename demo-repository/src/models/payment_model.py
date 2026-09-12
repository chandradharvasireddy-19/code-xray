from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class PaymentRequest:
    user_id: str
    amount: float
    token: str
    currency: str = "USD"


@dataclass
class PaymentRecord:
    payment_id: str
    user_id: str
    amount: float
    status: str
    timestamp: str
