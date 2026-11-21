"""Importing this package registers every payment table on `Base.metadata`."""

from payment_service.models.payment import Payment, PaymentStatus

__all__ = ["Payment", "PaymentStatus"]
