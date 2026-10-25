"""Razorpay test-mode order and verified payment lifecycle operations."""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.auction import Auction, AuctionStatus
from app.models.transaction import (
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentStatus,
    PaymentWebhookEvent,
    Transaction,
    is_payment_status_transition_allowed,
)

logger = logging.getLogger("bidsmart_api.payments")


class RazorpayClient:
    """Small REST adapter using Razorpay's documented Orders and Payments APIs."""

    base_url = "https://api.razorpay.com/v1"

    def __init__(self, key_id: str, key_secret: str):
        self.auth = (key_id, key_secret)

    def create_order(
        self, *, amount: int, currency: str, receipt: str, notes: Dict[str, str]
    ) -> Dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/orders",
            auth=self.auth,
            json={
                "amount": amount,
                "currency": currency,
                "receipt": receipt,
                "notes": notes,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()

    def get_payment(self, payment_id: str) -> Dict[str, Any]:
        response = httpx.get(
            f"{self.base_url}/payments/{payment_id}",
            auth=self.auth,
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


class PaymentService:
    def __init__(self, config=settings, provider=None):
        self.config = config
        self.provider = provider

    def _credentials(self, *, webhook: bool = False):
        key_id = getattr(self.config, "RAZORPAY_KEY_ID", "")
        key_secret = getattr(self.config, "RAZORPAY_KEY_SECRET", "")
        currency = getattr(self.config, "RAZORPAY_CURRENCY", "")

        if getattr(self.config, "RAZORPAY_MODE", None) != "test":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment processing is available only in Razorpay TEST mode.",
            )
        if not key_id.startswith("rzp_test_") or not key_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Razorpay TEST credentials are not configured.",
            )
        if currency != "USD":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Razorpay payment currency must be USD.",
            )
        webhook_secret = getattr(self.config, "RAZORPAY_WEBHOOK_SECRET", "")
        if webhook and not webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Razorpay webhook verification is not configured.",
            )
        if self.provider is None:
            self.provider = RazorpayClient(key_id, key_secret)
        return key_id, key_secret, webhook_secret

    @staticmethod
    def _minor_amount(amount: Decimal) -> int:
        value = Decimal(amount)
        minor = value * 100
        if value <= 0 or minor != minor.to_integral_value():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Transaction amount cannot be represented in USD cents.",
            )
        return int(minor)

    @staticmethod
    def _check_transaction_context(
        auction: Optional[Auction],
        transaction: Optional[Transaction],
        buyer_id: Optional[int] = None,
    ):
        if auction is None or transaction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Eligible auction payment was not found.",
            )
        if auction.status != AuctionStatus.COMPLETED or auction.winner_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment is available only for a completed auction with a winner.",
            )
        if transaction.buyer_id != auction.winner_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Transaction buyer does not match the auction winner.",
            )
        if transaction.seller_id != auction.product.seller_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Transaction seller does not match the auction owner.",
            )
        if buyer_id is not None and (
            auction.winner_id != buyer_id or transaction.buyer_id != buyer_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the winning buyer can access this payment.",
            )

    def create_order(self, db: Session, *, buyer_id: int, auction_id: int):
        key_id, _, _ = self._credentials()
        try:
            auction = (
                db.query(Auction)
                .filter(Auction.id == auction_id)
                .with_for_update()
                .populate_existing()
                .one_or_none()
            )
            transaction = (
                db.query(Transaction)
                .filter(Transaction.auction_id == auction_id)
                .with_for_update()
                .populate_existing()
                .one_or_none()
            )
            self._check_transaction_context(auction, transaction, buyer_id)

            if transaction.payment_status == PaymentStatus.SETTLEMENT_COMPLETED_DEMO:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This auction has already been paid.",
                )
            if transaction.payment_status not in {
                PaymentStatus.SETTLEMENT_PENDING_DEMO,
                PaymentStatus.SETTLEMENT_FAILED_DEMO,
            }:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This transaction is not eligible for payment.",
                )

            amount_minor = self._minor_amount(transaction.amount)
            currency = self.config.RAZORPAY_CURRENCY
            attempt = (
                db.query(PaymentAttempt)
                .filter(PaymentAttempt.transaction_id == transaction.id)
                .with_for_update()
                .populate_existing()
                .one_or_none()
            )
            if attempt is not None:
                if attempt.amount_minor != amount_minor or attempt.currency != currency:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="The saved payment order does not match the transaction.",
                    )
                if attempt.status == PaymentAttemptStatus.PAYMENT_COMPLETED:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="This auction has already been paid.",
                    )
                if transaction.payment_status == PaymentStatus.SETTLEMENT_FAILED_DEMO:
                    transaction.payment_status = PaymentStatus.SETTLEMENT_PENDING_DEMO
                attempt.status = PaymentAttemptStatus.ORDER_CREATED
                db.commit()
                return {
                    "key_id": key_id,
                    "order_id": attempt.provider_order_id,
                    "amount": attempt.amount_minor,
                    "currency": attempt.currency,
                }

            provider = self.provider or RazorpayClient(
                self.config.RAZORPAY_KEY_ID, self.config.RAZORPAY_KEY_SECRET
            )
            receipt = f"txn{transaction.id}-{uuid.uuid4().hex[:24]}"
            order = provider.create_order(
                amount=amount_minor,
                currency=currency,
                receipt=receipt,
                notes={
                    "transaction_id": str(transaction.id),
                    "auction_id": str(auction.id),
                },
            )
            if (
                not isinstance(order, dict)
                or not isinstance(order.get("id"), str)
                or not order["id"]
                or order.get("amount") != amount_minor
                or order.get("currency") != currency
            ):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Razorpay returned an invalid order response.",
                )

            attempt = PaymentAttempt(
                transaction_id=transaction.id,
                provider_order_id=order["id"],
                amount_minor=amount_minor,
                currency=currency,
                status=PaymentAttemptStatus.ORDER_CREATED,
            )
            db.add(attempt)
            if transaction.payment_status == PaymentStatus.SETTLEMENT_FAILED_DEMO:
                transaction.payment_status = PaymentStatus.SETTLEMENT_PENDING_DEMO
            db.commit()
            return {
                "key_id": key_id,
                "order_id": attempt.provider_order_id,
                "amount": attempt.amount_minor,
                "currency": attempt.currency,
            }
        except HTTPException:
            db.rollback()
            raise
        except httpx.HTTPError as exc:
            db.rollback()
            logger.warning("Razorpay order request failed: %s", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Razorpay could not create a payment order.",
            ) from exc
        except IntegrityError as exc:
            db.rollback()
            logger.warning("Payment-order uniqueness conflict.")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A payment order was created concurrently. Retry to retrieve it.",
            ) from exc
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _verify_payment_signature(
        order_id: str, payment_id: str, signature: str, key_secret: str
    ) -> bool:
        message = f"{order_id}|{payment_id}".encode("utf-8")
        expected = hmac.new(
            key_secret.encode("utf-8"), message, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _locked_order_context(self, db: Session, order_id: str):
        attempt = (
            db.query(PaymentAttempt)
            .filter(PaymentAttempt.provider_order_id == order_id)
            .one_or_none()
        )
        if attempt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment order was not found.",
            )
        transaction_hint = (
            db.query(Transaction)
            .filter(Transaction.id == attempt.transaction_id)
            .one_or_none()
        )
        auction = (
            db.query(Auction)
            .filter(Auction.id == transaction_hint.auction_id)
            .with_for_update()
            .one_or_none()
            if transaction_hint is not None
            else None
        )
        transaction = (
            db.query(Transaction)
            .filter(Transaction.id == attempt.transaction_id)
            .with_for_update()
            .populate_existing()
            .one_or_none()
        )
        attempt = (
            db.query(PaymentAttempt)
            .filter(PaymentAttempt.id == attempt.id)
            .with_for_update()
            .populate_existing()
            .one_or_none()
        )
        self._check_transaction_context(auction, transaction)
        return attempt, transaction, auction

    def _complete_payment(
        self,
        db: Session,
        attempt: PaymentAttempt,
        transaction: Transaction,
        payment_id: str,
    ):
        if transaction.payment_status == PaymentStatus.SETTLEMENT_COMPLETED_DEMO:
            if attempt.provider_payment_id == payment_id:
                return False
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A different payment has already completed this transaction.",
            )
        if transaction.payment_status == PaymentStatus.SETTLEMENT_FAILED_DEMO:
            if not is_payment_status_transition_allowed(
                transaction.payment_status, PaymentStatus.SETTLEMENT_PENDING_DEMO
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Transaction cannot be reopened for verified payment.",
                )
            transaction.payment_status = PaymentStatus.SETTLEMENT_PENDING_DEMO
        if not is_payment_status_transition_allowed(
            transaction.payment_status, PaymentStatus.SETTLEMENT_COMPLETED_DEMO
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Transaction cannot be completed from its current status.",
            )
        if attempt.provider_payment_id not in {None, payment_id}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A different provider payment is already associated with this order.",
            )
        transaction.payment_status = PaymentStatus.SETTLEMENT_COMPLETED_DEMO
        transaction.settled_at = datetime.now(timezone.utc).replace(tzinfo=None)
        attempt.provider_payment_id = payment_id
        attempt.status = PaymentAttemptStatus.PAYMENT_COMPLETED
        return True

    @staticmethod
    def _verify_provider_payment(
        payment: Any, attempt: PaymentAttempt, payment_id: str, order_id: str
    ):
        if (
            not isinstance(payment, dict)
            or payment.get("id") != payment_id
            or payment.get("order_id") != order_id
            or payment.get("status") != "captured"
            or payment.get("amount") != attempt.amount_minor
            or payment.get("currency") != attempt.currency
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Razorpay payment is not captured for this order and amount.",
            )

    def _validate_attempt_against_transaction(
        self, attempt: PaymentAttempt, transaction: Transaction
    ):
        authoritative_amount_minor = self._minor_amount(transaction.amount)
        if (
            self.config.RAZORPAY_CURRENCY != "USD"
            or attempt.currency != "USD"
            or attempt.amount_minor != authoritative_amount_minor
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment records do not match the authoritative USD transaction.",
            )

    def verify_payment(
        self,
        db: Session,
        *,
        buyer_id: int,
        order_id: str,
        payment_id: str,
        signature: str,
    ):
        _, key_secret, _ = self._credentials()
        if not all(isinstance(value, str) and value for value in (
            order_id, payment_id, signature
        )):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Razorpay payment verification data.",
            )
        if not self._verify_payment_signature(
            order_id, payment_id, signature, key_secret
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Razorpay payment signature.",
            )
        try:
            attempt, transaction, auction = self._locked_order_context(db, order_id)
            self._check_transaction_context(auction, transaction, buyer_id)
            self._validate_attempt_against_transaction(attempt, transaction)
            if (
                transaction.payment_status == PaymentStatus.SETTLEMENT_COMPLETED_DEMO
                and attempt.provider_payment_id == payment_id
            ):
                return self._payment_result(transaction, duplicate=True)

            provider = self.provider or RazorpayClient(
                self.config.RAZORPAY_KEY_ID, self.config.RAZORPAY_KEY_SECRET
            )
            payment = provider.get_payment(payment_id)
            self._verify_provider_payment(payment, attempt, payment_id, order_id)
            self._complete_payment(db, attempt, transaction, payment_id)
            db.commit()
            return self._payment_result(transaction, duplicate=False)
        except HTTPException:
            db.rollback()
            raise
        except httpx.HTTPError as exc:
            db.rollback()
            logger.warning("Razorpay payment lookup failed: %s", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Razorpay could not verify the payment.",
            ) from exc
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _payment_result(transaction: Transaction, *, duplicate: bool):
        return {
            "transaction_id": transaction.id,
            "payment_status": transaction.payment_status.value,
            "settled_at": transaction.settled_at,
            "already_processed": duplicate,
        }

    def process_webhook(
        self,
        db: Session,
        *,
        raw_body: bytes,
        signature: str,
        event_id: Optional[str] = None,
    ):
        _, _, webhook_secret = self._credentials(webhook=True)
        expected = hmac.new(
            webhook_secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Razorpay webhook signature.",
            )
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Razorpay webhook payload.",
            ) from exc

        event_type = body.get("event") if isinstance(body, dict) else None
        if event_type not in {"payment.captured", "payment.failed"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported Razorpay webhook event.",
            )
        try:
            payment = body["payload"]["payment"]["entity"]
            payment_id = payment["id"]
            order_id = payment["order_id"]
            amount_minor = payment["amount"]
            currency = payment["currency"]
            payment_state = payment["status"]
            if not all(isinstance(item, str) and item for item in (
                payment_id, order_id, currency, payment_state
            )) or type(amount_minor) is not int:
                raise ValueError("Invalid payment entity fields")
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Razorpay payment event payload.",
            ) from exc

        resolved_event_id = hashlib.sha256(raw_body).hexdigest()
        if len(resolved_event_id) > 64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Razorpay event identifier.",
            )

        try:
            if db.query(PaymentWebhookEvent).filter(
                PaymentWebhookEvent.event_id == resolved_event_id
            ).first():
                db.rollback()
                return {"status": "duplicate", "event_id": resolved_event_id}

            attempt, transaction, _ = self._locked_order_context(db, order_id)
            self._validate_attempt_against_transaction(attempt, transaction)
            if (
                amount_minor != attempt.amount_minor
                or currency != attempt.currency
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Razorpay event amount or currency does not match the order.",
                )

            if event_type == "payment.captured":
                if payment_state != "captured":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Captured event does not contain a captured payment.",
                    )
                self._complete_payment(db, attempt, transaction, payment_id)
            else:
                if payment_state != "failed":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed event does not contain a failed payment.",
                    )
                if transaction.payment_status != PaymentStatus.SETTLEMENT_COMPLETED_DEMO:
                    if is_payment_status_transition_allowed(
                        transaction.payment_status,
                        PaymentStatus.SETTLEMENT_FAILED_DEMO,
                    ):
                        transaction.payment_status = PaymentStatus.SETTLEMENT_FAILED_DEMO
                        attempt.status = PaymentAttemptStatus.PAYMENT_FAILED

            db.add(PaymentWebhookEvent(
                event_id=resolved_event_id,
                event_type=event_type,
            ))
            db.commit()
            return {
                "status": "processed",
                "event_id": resolved_event_id,
                "transaction_id": transaction.id,
                "payment_status": transaction.payment_status.value,
            }
        except HTTPException:
            db.rollback()
            raise
        except IntegrityError as exc:
            db.rollback()
            if db.query(PaymentWebhookEvent).filter(
                PaymentWebhookEvent.event_id == resolved_event_id
            ).first():
                return {"status": "duplicate", "event_id": resolved_event_id}
            logger.warning("Payment webhook uniqueness conflict.")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment event conflicts with an existing payment record.",
            ) from exc
        except Exception:
            db.rollback()
            raise


payment_service = PaymentService()
