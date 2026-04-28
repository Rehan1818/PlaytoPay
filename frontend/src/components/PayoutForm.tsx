import { FormEvent, useEffect, useMemo, useState } from "react";
import { formatINR } from "../utils";

type Props = {
  merchantId: number;
  onSubmit: (amountPaise: number, bankAccountId: number) => Promise<void>;
};

export function PayoutForm({ merchantId, onSubmit }: Props) {
  const [amountPaise, setAmountPaise] = useState(1000);
  const [bankAccountId, setBankAccountId] = useState(merchantId);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setBankAccountId(merchantId);
  }, [merchantId]);

  const canSubmit = useMemo(
    () => amountPaise > 0 && bankAccountId > 0,
    [amountPaise, bankAccountId]
  );

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await onSubmit(amountPaise, bankAccountId);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel__header">
        <h2 className="panel__title">Request payout</h2>
      </div>
      <form onSubmit={handleSubmit} className="payout-form">
        <div className="form-row">
          <label className="form-label">Amount (paise)</label>
          <input
            className="form-input"
            type="number"
            placeholder="e.g. 50000 = ₹500"
            value={amountPaise}
            min={1}
            onChange={(e) => setAmountPaise(Number(e.target.value || 0))}
          />
          <span className="form-hint">
            {amountPaise > 0 ? `= ${formatINR(amountPaise)}` : "Enter paise amount"}
          </span>
        </div>
        <div className="form-row">
          <label className="form-label">Bank account ID</label>
          <input
            className="form-input"
            type="number"
            placeholder="1"
            value={bankAccountId}
            min={1}
            onChange={(e) => setBankAccountId(Number(e.target.value || 1))}
          />
          <span className="form-hint">
            Auto-set to selected merchant (#{merchantId} to bank account #{merchantId})
          </span>
        </div>
        <button
          type="submit"
          disabled={!canSubmit || loading}
          className="payout-btn"
        >
          {loading ? "Submitting..." : "Create payout"}
        </button>
        {error && <p className="form-error">{error}</p>}
      </form>
    </div>
  );
}