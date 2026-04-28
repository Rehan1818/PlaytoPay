import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Merchant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="BankAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("account_name", models.CharField(max_length=255)),
                ("account_number", models.CharField(max_length=64)),
                ("ifsc_code", models.CharField(max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "merchant",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bank_accounts", to="payouts.merchant"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Payout",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("amount_paise", models.BigIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed")],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("next_retry_at", models.DateTimeField(blank=True, null=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "bank_account",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payouts", to="payouts.bankaccount"),
                ),
                ("merchant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payouts", to="payouts.merchant")),
            ],
            options={
                "constraints": [models.CheckConstraint(condition=models.Q(amount_paise__gt=0), name="payout_positive_amount")],
            },
        ),
        migrations.CreateModel(
            name="LedgerEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "entry_type",
                    models.CharField(
                        choices=[
                            ("credit", "Credit"),
                            ("hold", "Hold"),
                            ("hold_release", "Hold Release"),
                            ("payout_debit", "Payout Debit"),
                        ],
                        max_length=32,
                    ),
                ),
                ("amount_paise", models.BigIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("note", models.CharField(blank=True, max_length=255)),
                ("merchant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ledger_entries", to="payouts.merchant")),
                (
                    "payout",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ledger_entries", to="payouts.payout"),
                ),
            ],
            options={
                "constraints": [models.CheckConstraint(condition=models.Q(amount_paise__gt=0), name="ledger_positive_amount")],
            },
        ),
        migrations.CreateModel(
            name="IdempotencyKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.UUIDField()),
                ("request_hash", models.CharField(max_length=128)),
                ("response_body", models.JSONField()),
                ("status_code", models.PositiveSmallIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("merchant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="idempotency_keys", to="payouts.merchant")),
                (
                    "payout",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="idempotency_records", to="payouts.payout"
                    ),
                ),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("merchant", "key"), name="uniq_merchant_idem_key")],
            },
        ),
    ]
