import { useEffect, useState } from "react";
import { fetchDashboard, requestPayout } from "./api/dashboard";
import { BalanceCards } from "./components/BalanceCards";
import { LedgerList } from "./components/LedgerList";
import { MerchantSelector } from "./components/MerchantSelector";
import { PayoutForm } from "./components/PayoutForm";
import { PayoutHistory } from "./components/PayoutHistory";
import type { DashboardResponse } from "./types";

export function App() {
  const [merchantId, setMerchantId] = useState(1);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [loadError, setLoadError] = useState("");

  const loadDashboard = async () => {
    const data = await fetchDashboard(merchantId);
    setDashboard(data);
  };

  useEffect(() => {
    setDashboard(null);
    setLoadError("");
    loadDashboard().catch((e) => setLoadError(String(e)));
    const interval = setInterval(
      () => loadDashboard().catch(() => undefined),
      4000
    );
    return () => clearInterval(interval);
  }, [merchantId]);

  const handlePayout = async (amountPaise: number, bankAccountId: number) => {
    await requestPayout(merchantId, amountPaise, bankAccountId);
    await loadDashboard();
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__left">
          <h1 className="app-title">Playto Pay</h1>
          <p className="app-subtitle">Merchant payout dashboard</p>
        </div>
        <MerchantSelector value={merchantId} onChange={setMerchantId} />
      </header>

      {loadError && <p className="load-error">{loadError}</p>}

      {dashboard && (
        <>
          <BalanceCards balances={dashboard.balances} />

          <div className="main-grid">
            <PayoutForm merchantId={merchantId} onSubmit={handlePayout} />
            <div className="side-panels">
              <LedgerList entries={dashboard.recent_ledger} />
              <PayoutHistory payouts={dashboard.payouts} />
            </div>
          </div>
        </>
      )}

      {!dashboard && !loadError && (
        <p className="loading-text">Loading...</p>
      )}
    </div>
  );
}