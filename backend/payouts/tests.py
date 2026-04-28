import threading
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import BankAccount, LedgerEntry, Merchant, Payout
from .services import create_payout_request, process_pending_payout, retry_stuck_payouts


class PayoutEngineTests(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(name="Test Merchant")
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_name="Test Merchant",
            account_number="1234567890",
            ifsc_code="HDFC0001234",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=10000,
            note="Initial credit",
        )

    def test_idempotency_returns_same_response_without_duplicate(self):
        key = str(uuid.uuid4())
        payload = {"amount_paise": 5000, "bank_account_id": self.bank_account.id}
        first_response, first_status = create_payout_request(self.merchant.id, key, payload)
        second_response, second_status = create_payout_request(self.merchant.id, key, payload)

        self.assertEqual(first_status, 201)
        self.assertEqual(second_status, 201)
        self.assertEqual(first_response, second_response)
        self.assertEqual(self.merchant.payouts.count(), 1)
        self.assertEqual(
            self.merchant.ledger_entries.filter(entry_type=LedgerEntry.EntryType.HOLD).count(),
            1,
        )

    def test_concurrent_requests_only_one_succeeds(self):
        results = []
        lock = threading.Lock()

        def run_one():
            payload = {"amount_paise": 6000, "bank_account_id": self.bank_account.id}
            response, status_code = create_payout_request(self.merchant.id, str(uuid.uuid4()), payload)
            with lock:
                results.append((status_code, response))

        t1 = threading.Thread(target=run_one)
        t2 = threading.Thread(target=run_one)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        success_count = sum(1 for status_code, _ in results if status_code == 201)
        failure_count = sum(1 for status_code, _ in results if status_code == 400)
        self.assertEqual(success_count, 1)
        self.assertEqual(failure_count, 1)

    def test_state_machine_blocks_failed_to_completed(self):
        payout = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=1000,
            status=Payout.Status.PENDING,
        )
        payout.transition_to(Payout.Status.PROCESSING)
        payout.transition_to(Payout.Status.FAILED)

        with self.assertRaises(ValidationError):
            payout.transition_to(Payout.Status.COMPLETED)

    def test_retry_exhaustion_fails_and_refunds_atomically(self):
        payout = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=2000,
            status=Payout.Status.PENDING,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            payout=payout,
            entry_type=LedgerEntry.EntryType.HOLD,
            amount_paise=payout.amount_paise,
            note="Payout hold",
        )
        payout.transition_to(Payout.Status.PROCESSING)
        payout.attempts = 3
        payout.next_retry_at = timezone.now() - timedelta(seconds=1)
        payout.save(update_fields=["status", "attempts", "next_retry_at", "updated_at"])

        retry_stuck_payouts()
        payout.refresh_from_db()
        self.assertEqual(payout.status, Payout.Status.FAILED)
        self.assertEqual(
            LedgerEntry.objects.filter(
                payout=payout,
                entry_type=LedgerEntry.EntryType.HOLD_RELEASE,
            ).count(),
            1,
        )

    def test_hanging_processing_gets_retried(self):
        payout = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=2500,
            status=Payout.Status.PENDING,
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            payout=payout,
            entry_type=LedgerEntry.EntryType.HOLD,
            amount_paise=payout.amount_paise,
            note="Payout hold",
        )
        with patch("payouts.services.random.random", return_value=0.95):
            status_value = process_pending_payout(str(payout.id))
        self.assertEqual(status_value, Payout.Status.PROCESSING)

        payout.refresh_from_db()
        payout.next_retry_at = timezone.now() - timedelta(seconds=1)
        payout.save(update_fields=["next_retry_at", "updated_at"])
        retry_ids = retry_stuck_payouts()
        self.assertIn(str(payout.id), retry_ids)
