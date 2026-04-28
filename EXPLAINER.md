# EXPLAINER

## 1) The Ledger

Balance calculation query is implemented in `backend/payouts/services.py` in `ledger_balances()`.

It aggregates entry types at the database level:
- credits
- holds
- hold releases
- payout debits

Then derives:
- available = credits - holds + hold_releases - payout_debits
- held = holds - hold_releases
- net = credits - payout_debits

Why this model:
- append-only ledger keeps immutable financial history
- balance is derived from journal entries, reducing drift risk from mutable balance fields
- each payout lifecycle event creates explicit accounting entries

## 2) The Lock

Overdraw prevention is in `create_payout_request()`:
- wraps logic in `@transaction.atomic`
- acquires row lock with `Merchant.objects.select_for_update().get(id=merchant_id)`
- computes available balance while lock is held
- inserts hold entry + payout only if funds are sufficient

Database primitive:
- PostgreSQL row-level lock (`SELECT ... FOR UPDATE`) on merchant row as concurrency anchor.
- serializes concurrent payout creations per merchant and prevents check-then-deduct race.

## 3) The Idempotency

Seen-key detection uses `IdempotencyKey` table with unique constraint on `(merchant, key)`.

Flow:
- Parse `Idempotency-Key` UUID
- Check existing non-expired record for merchant
- If found and payload hash matches: return stored response body/status exactly
- If found with different payload hash: reject

If request A is in flight and request B with same key arrives:
- both execute in DB transactions with merchant lock and idempotency lookup
- unique `(merchant, key)` constraint guarantees only one idempotency record wins
- loser path catches uniqueness conflict and replays stored response

## 4) The State Machine

State guard is in `Payout.transition_to()` in `backend/payouts/models.py`.

Allowed:
- pending -> processing
- processing -> completed
- processing -> failed

Blocked:
- completed -> pending
- failed -> completed
- any backward or lateral illegal transition raises `ValidationError`.

## 5) The AI Audit

Wrong AI suggestion (example):
- check balance in Python, then create payout in separate statements without lock.

Why wrong:
- introduces race where two concurrent requests read same available balance and both deduct.

Replacement:
- transactional `select_for_update` lock on merchant row
- DB-level aggregation + atomic hold entry creation in same transaction
- explicit idempotency persistence for network retry safety
