"""Importing this package registers every payment table on `Base.metadata`."""

from payment_service.models.payment import Payment, PaymentMethod, PaymentStatus

__all__ = ["Payment", "PaymentMethod", "PaymentStatus"]
