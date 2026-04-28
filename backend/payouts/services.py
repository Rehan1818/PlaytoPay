import hashlib
import json
import random
from datetime import timedelta
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import BigIntegerField, Case, F, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError

from .models import BankAccount, IdempotencyKey, LedgerEntry, Merchant, Payout


def request_payload_hash(payload: dict) -> str:
    payload_json = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _store_idempotent_response(
    *,
    merchant: Merchant,
    parsed_key: UUID,
    payload_hash: str,
    response: dict,
    status_code: int,
    expires_at,
    payout: Payout | None = None,
) -> tuple[dict, int]:
    try:
        IdempotencyKey.objects.create(
            merchant=merchant,
            key=parsed_key,
            request_hash=payload_hash,
            response_body=response,
            status_code=status_code,
            payout=payout,
            expires_at=expires_at,
        )
        return response, status_code
    except IntegrityError:
        existing = IdempotencyKey.objects.select_for_update().get(merchant=merchant, key=parsed_key)
        if existing.request_hash != payload_hash:
            raise ValidationError("Idempotency key reused with different payload")
        return existing.response_body, existing.status_code


def ledger_balances(merchant_id: int) -> dict:
    aggregates = LedgerEntry.objects.filter(merchant_id=merchant_id).aggregate(
        credits=Coalesce(
            Sum(
                Case(
                    When(entry_type=LedgerEntry.EntryType.CREDIT, then=F("amount_paise")),
                    default=Value(0),
                    output_field=BigIntegerField(),
                )
            ),
            Value(0),
        ),
        holds=Coalesce(
            Sum(
                Case(
                    When(entry_type=LedgerEntry.EntryType.HOLD, then=F("amount_paise")),
                    default=Value(0),
                    output_field=BigIntegerField(),
                )
            ),
            Value(0),
        ),
        hold_releases=Coalesce(
            Sum(
                Case(
                    When(entry_type=LedgerEntry.EntryType.HOLD_RELEASE, then=F("amount_paise")),
                    default=Value(0),
                    output_field=BigIntegerField(),
                )
            ),
            Value(0),
        ),
        payout_debits=Coalesce(
            Sum(
                Case(
                    When(entry_type=LedgerEntry.EntryType.PAYOUT_DEBIT, then=F("amount_paise")),
                    default=Value(0),
                    output_field=BigIntegerField(),
                )
            ),
            Value(0),
        ),
    )
    held_balance = aggregates["holds"] - aggregates["hold_releases"]
    available_balance = aggregates["credits"] - aggregates["holds"] + aggregates["hold_releases"] - aggregates["payout_debits"]
    return {
        "available_balance_paise": int(available_balance),
        "held_balance_paise": int(held_balance),
        "net_balance_paise": int(aggregates["credits"] - aggregates["payout_debits"]),
    }


@transaction.atomic
def create_payout_request(merchant_id: int, idempotency_key: str, payload: dict) -> tuple[dict, int]:
    merchant = Merchant.objects.select_for_update().get(id=merchant_id)
    parsed_key = UUID(idempotency_key)
    now = timezone.now()
    payload_hash = request_payload_hash(payload)
    existing = (
        IdempotencyKey.objects.select_for_update()
        .filter(merchant=merchant, key=parsed_key, expires_at__gt=now)
        .first()
    )
    if existing:
        if existing.request_hash != payload_hash:
            raise ValidationError("Idempotency key reused with different payload")
        return existing.response_body, existing.status_code

    bank_account = BankAccount.objects.filter(id=payload["bank_account_id"], merchant=merchant).first()
    if not bank_account:
        raise ValidationError("Bank account does not belong to merchant")

    amount_paise = int(payload["amount_paise"])
    balances = ledger_balances(merchant.id)
    if balances["available_balance_paise"] < amount_paise:
        response = {
            "error": "insufficient_balance",
            "available_balance_paise": balances["available_balance_paise"],
        }
        status_code = status.HTTP_400_BAD_REQUEST
        return _store_idempotent_response(
            merchant=merchant,
            parsed_key=parsed_key,
            payload_hash=payload_hash,
            response=response,
            status_code=status_code,
            expires_at=now + timedelta(hours=24),
        )

    payout = Payout.objects.create(
        merchant=merchant,
        bank_account=bank_account,
        amount_paise=amount_paise,
        status=Payout.Status.PENDING,
    )
    LedgerEntry.objects.create(
        merchant=merchant,
        payout=payout,
        entry_type=LedgerEntry.EntryType.HOLD,
        amount_paise=amount_paise,
        note="Payout hold",
    )
    response = {
        "id": str(payout.id),
        "status": payout.status,
        "amount_paise": payout.amount_paise,
        "merchant_id": merchant.id,
        "bank_account_id": bank_account.id,
    }
    status_code = status.HTTP_201_CREATED
    return _store_idempotent_response(
        merchant=merchant,
        parsed_key=parsed_key,
        payload_hash=payload_hash,
        response=response,
        status_code=status_code,
        expires_at=now + timedelta(hours=24),
        payout=payout,
    )


@transaction.atomic
def process_pending_payout(payout_id: str) -> str:
    payout = Payout.objects.select_for_update().select_related("merchant").get(id=payout_id)
    if payout.status == Payout.Status.PENDING:
        payout.transition_to(Payout.Status.PROCESSING)
        payout.attempts += 1
        payout.save(update_fields=["status", "attempts", "updated_at"])

    if payout.status != Payout.Status.PROCESSING:
        return payout.status

    roll = random.random()
    if roll < 0.7:
        payout.transition_to(Payout.Status.COMPLETED)
        payout.processed_at = timezone.now()
        payout.next_retry_at = None
        payout.save(update_fields=["status", "processed_at", "next_retry_at", "updated_at"])
        LedgerEntry.objects.create(
            merchant=payout.merchant,
            payout=payout,
            entry_type=LedgerEntry.EntryType.PAYOUT_DEBIT,
            amount_paise=payout.amount_paise,
            note="Payout completed",
        )
    elif roll < 0.9:
        payout.transition_to(Payout.Status.FAILED)
        payout.processed_at = timezone.now()
        payout.next_retry_at = None
        payout.save(update_fields=["status", "processed_at", "next_retry_at", "updated_at"])
        LedgerEntry.objects.create(
            merchant=payout.merchant,
            payout=payout,
            entry_type=LedgerEntry.EntryType.HOLD_RELEASE,
            amount_paise=payout.amount_paise,
            note="Payout failed refund",
        )
    else:
        # stay in processing; retry scheduler will handle this payout
        payout.next_retry_at = timezone.now() + timedelta(seconds=30 * (2 ** (payout.attempts - 1)))
        payout.save(update_fields=["next_retry_at", "updated_at"])
    return payout.status


@transaction.atomic
def retry_stuck_payouts() -> list[str]:
    now = timezone.now()
    stuck_ids = list(
        Payout.objects.select_for_update()
        .filter(
            status=Payout.Status.PROCESSING,
            next_retry_at__isnull=False,
            next_retry_at__lte=now,
        )
        .values_list("id", flat=True)
    )
    to_process = []
    for payout_id in stuck_ids:
        payout = Payout.objects.select_for_update().select_related("merchant").get(id=payout_id)
        if payout.attempts >= 3:
            payout.transition_to(Payout.Status.FAILED)
            payout.processed_at = now
            payout.next_retry_at = None
            payout.save(update_fields=["status", "processed_at", "next_retry_at", "updated_at"])
            LedgerEntry.objects.create(
                merchant=payout.merchant,
                payout=payout,
                entry_type=LedgerEntry.EntryType.HOLD_RELEASE,
                amount_paise=payout.amount_paise,
                note="Payout retry exhausted refund",
            )
        else:
            # Clear retry schedule so processor re-simulates settlement now.
            payout.next_retry_at = None
            payout.save(update_fields=["next_retry_at", "updated_at"])
            to_process.append(str(payout.id))
    return to_process
