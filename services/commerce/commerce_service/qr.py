"""Signed pickup QR codes.

The QR code encodes a JSON payload `{order_id, user_id, shop_id, created_at, signature}`. The
signature is an HMAC-SHA256 over the other fields with a server-side secret, so a forged or edited
code is rejected when the shop scans it.
"""

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from commerce_service.config import get_settings
from commerce_service.models import Order


class InvalidQrError(Exception):
    pass


@dataclass(frozen=True)
class QrClaims:
    order_id: uuid.UUID
    user_id: uuid.UUID
    shop_id: uuid.UUID
    created_at: str


def _sign(claims: QrClaims) -> str:
    message = "|".join(
        [str(claims.order_id), str(claims.user_id), str(claims.shop_id), claims.created_at]
    )
    key = get_settings().qr_signing_secret.encode()
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()


def claims_for(order: Order) -> QrClaims:
    created_at = order.created_at.astimezone(UTC).isoformat(timespec="microseconds")
    return QrClaims(order.id, order.user_id, order.shop_id, created_at)


def qr_payload(order: Order) -> str:
    """The exact string to encode in the QR image."""
    claims = claims_for(order)
    payload = {
        "order_id": str(claims.order_id),
        "user_id": str(claims.user_id),
        "shop_id": str(claims.shop_id),
        "created_at": claims.created_at,
        "signature": _sign(claims),
    }
    return json.dumps(payload, separators=(",", ":"))


def verify_qr_payload(raw: str) -> QrClaims:
    """Parse and verify a scanned payload; raises `InvalidQrError` if it is not authentic."""
    try:
        data = json.loads(raw)
        claims = QrClaims(
            order_id=uuid.UUID(data["order_id"]),
            user_id=uuid.UUID(data["user_id"]),
            shop_id=uuid.UUID(data["shop_id"]),
            created_at=str(data["created_at"]),
        )
        datetime.fromisoformat(claims.created_at)
        signature = str(data["signature"])
    except (ValueError, KeyError, TypeError) as exc:
        raise InvalidQrError("QR code is not a BrewPass pickup code.") from exc

    if not hmac.compare_digest(signature, _sign(claims)):
        raise InvalidQrError("QR code signature is invalid.")
    return claims
