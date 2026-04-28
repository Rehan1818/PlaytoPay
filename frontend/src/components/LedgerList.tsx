import type { LedgerEntry } from "../types";
import { formatINR, timeAgo } from "../utils";

type Props = { entries: LedgerEntry[] };

function dotClass(type: string) {
  if (type === "credit") return "tx-dot tx-dot--credit";
  if (type === "hold") return "tx-dot tx-dot--hold";
  return "tx-dot tx-dot--debit";
}

function amountClass(type: string) {
  if (type === "credit") return "tx-amount tx-amount--credit";
  if (type === "hold") return "tx-amount tx-amount--hold";
  return "tx-amount tx-amount--debit";
}

function prefix(type: string) {
  return type === "credit" ? "+" : "-";
}

export function LedgerList({ entries }: Props) {
  return (
    <div className="panel">
      <div className="panel__header">
        <h2 className="panel__title">Recent ledger</h2>
        <span className="panel__meta">{entries.length} entries</span>
      </div>
      <div className="ledger-list">
        {entries.length === 0 && (
          <p className="empty-state">No transactions yet</p>
        )}
        {entries.map((entry) => (
          <div key={entry.id} className="ledger-item">
            <div className="ledger-item__left">
              <span className={dotClass(entry.entry_type)} />
              <div>
                <p className="tx-type">{entry.entry_type}</p>
                <p className="tx-time">{timeAgo(entry.created_at)}</p>
              </div>
            </div>
            <span className={amountClass(entry.entry_type)}>
              {prefix(entry.entry_type)}
              {formatINR(entry.amount_paise)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}