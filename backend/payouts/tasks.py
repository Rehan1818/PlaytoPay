from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task

from .models import Payout
from .services import process_pending_payout, retry_stuck_payouts


@db_task()
def process_payout_task(payout_id: str) -> str:
    return process_pending_payout(payout_id)


@db_periodic_task(crontab(minute="*"))
def enqueue_pending_payouts():
    for payout_id in Payout.objects.filter(status=Payout.Status.PENDING).values_list("id", flat=True)[:100]:
        process_payout_task(str(payout_id))


@db_periodic_task(crontab(minute="*"))
def retry_stuck_payouts_task():
    for payout_id in retry_stuck_payouts():
        process_payout_task(payout_id)
