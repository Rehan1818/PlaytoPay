export type LedgerEntry = {
    id: number;
    entry_type: string;
    amount_paise: number;
    note: string;
    created_at: string;
  };
  
  export type Payout = {
    id: string;
    amount_paise: number;
    status: string;
    created_at: string;
    bank_account_id: number;
  };
  
  export type Balances = {
    available_balance_paise: number;
    held_balance_paise: number;
    net_balance_paise: number;
  };
  
  export type DashboardResponse = {
    merchant_id: number;
    balances: Balances;
    recent_ledger: LedgerEntry[];
    payouts: Payout[];
  };