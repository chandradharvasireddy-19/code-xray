import pytest
from src.controllers.payment_controller import PaymentController
from src.services.payment_service import PaymentService
from src.repositories.payment_repository import PaymentRepository


def test_payment_processing_success():
    controller = PaymentController()
    payload = {
        "user_id": "usr_9988",
        "amount": 150.0,
        "token": "valid_secure_bearer_token_12345",
    }
    result = controller.handle_payment(payload)
    assert result["status"] == "approved"
    assert result["amount"] == 150.0
    assert "payment_id" in result


def test_payment_processing_invalid_token():
    controller = PaymentController()
    payload = {
        "user_id": "usr_9988",
        "amount": 150.0,
        "token": "invalid_bad_token",
    }
    with pytest.raises(PermissionError):
        controller.handle_payment(payload)
