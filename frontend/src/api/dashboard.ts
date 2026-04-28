import type { DashboardResponse } from "../types";

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export async function fetchDashboard(merchantId: number): Promise<DashboardResponse> {
  const res = await fetch(`${API_BASE}/dashboard?merchant_id=${merchantId}`);
  if (!res.ok) throw new Error("Failed to load dashboard");
  return res.json() as Promise<DashboardResponse>;
}

export async function requestPayout(
  merchantId: number,
  amountPaise: number,
  bankAccountId: number
): Promise<void> {
  const idempotencyKey = crypto.randomUUID();
  const res = await fetch(`${API_BASE}/payouts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Merchant-Id": String(merchantId),
      "Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify({ amount_paise: amountPaise, bank_account_id: bankAccountId }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error ?? "Payout request failed");
}