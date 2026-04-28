import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Merchant(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class BankAccount(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="bank_accounts")
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=64)
    ifsc_code = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)


class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        CREDIT = "credit", "Credit"
        HOLD = "hold", "Hold"
        HOLD_RELEASE = "hold_release", "Hold Release"
        PAYOUT_DEBIT = "payout_debit", "Payout Debit"

    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="ledger_entries")
    payout = models.ForeignKey("Payout", on_delete=models.SET_NULL, related_name="ledger_entries", null=True, blank=True)
    entry_type = models.CharField(max_length=32, choices=EntryType.choices)
    amount_paise = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(amount_paise__gt=0), name="ledger_positive_amount"),
        ]


class Payout(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="payouts")
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name="payouts")
    amount_paise = models.BigIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(amount_paise__gt=0), name="payout_positive_amount"),
        ]

    def transition_to(self, new_status: str) -> None:
        allowed = {
            self.Status.PENDING: {self.Status.PROCESSING},
            self.Status.PROCESSING: {self.Status.COMPLETED, self.Status.FAILED},
            self.Status.COMPLETED: set(),
            self.Status.FAILED: set(),
        }
        if new_status not in allowed[self.status]:
            raise ValidationError(f"Illegal payout transition: {self.status} -> {new_status}")
        self.status = new_status


class IdempotencyKey(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="idempotency_keys")
    key = models.UUIDField()
    request_hash = models.CharField(max_length=128)
    response_body = models.JSONField()
    status_code = models.PositiveSmallIntegerField()
    payout = models.ForeignKey(Payout, on_delete=models.SET_NULL, null=True, blank=True, related_name="idempotency_records")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["merchant", "key"], name="uniq_merchant_idem_key"),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
