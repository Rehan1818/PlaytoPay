import type { Payout } from "../types";
import { formatINR, shortId, timeAgo } from "../utils";

type Props = { payouts: Payout[] };

function statusClass(status: string) {
  return `status-badge status-badge--${status}`;
}

export function PayoutHistory({ payouts }: Props) {
  return (
    <div className="panel">
      <div className="panel__header">
        <h2 className="panel__title">Payout history</h2>
        <span className="panel__meta">
          {payouts.length} payout{payouts.length !== 1 ? "s" : ""}
        </span>
      </div>
      <div className="payout-list">
        {payouts.length === 0 && (
          <p className="empty-state">No payouts yet</p>
        )}
        {payouts.map((payout) => (
          <div key={payout.id} className="payout-row">
            <span className="payout-id">#{shortId(payout.id)}</span>
            <span className={statusClass(payout.status)}>{payout.status}</span>
            <div className="payout-row__right">
              <span className="payout-amount">{formatINR(payout.amount_paise)}</span>
              <span className="payout-time">{timeAgo(payout.created_at)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}