from django.core.management.base import BaseCommand

from payouts.models import BankAccount, LedgerEntry, Merchant


class Command(BaseCommand):
    help = "Seed merchants, bank accounts, and credits"

    def handle(self, *args, **options):
        merchants = []
        for name in ["Alpha Studio", "Beta Agency", "Gamma Freelance"]:
            merchant, _ = Merchant.objects.get_or_create(name=name)
            merchants.append(merchant)
            BankAccount.objects.get_or_create(
                merchant=merchant,
                account_name=name,
                account_number=f"00000{merchant.id}1234",
                ifsc_code="HDFC0001234",
            )
        for merchant in merchants:
            for amount in [50000, 125000, 80000]:
                LedgerEntry.objects.get_or_create(
                    merchant=merchant,
                    entry_type=LedgerEntry.EntryType.CREDIT,
                    amount_paise=amount,
                    note="Seed credit",
                )
        self.stdout.write(self.style.SUCCESS("Seeded merchants and ledger credits"))
