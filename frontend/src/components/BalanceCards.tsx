import type { Balances } from "../types";
import { formatINR } from "../utils";

type Props = { balances: Balances };

type CardProps = {
  label: string;
  amount: number;
  sub: string;
  variant: "available" | "held" | "net";
};

function BalanceCard({ label, amount, sub, variant }: CardProps) {
  return (
    <div className={`balance-card balance-card--${variant}`}>
      <div className="balance-card__accent" />
      <p className="balance-card__label">{label}</p>
      <p className="balance-card__amount">{formatINR(amount)}</p>
      <p className="balance-card__sub">{sub}</p>
    </div>
  );
}

export function BalanceCards({ balances }: Props) {
  return (
    <div className="balance-grid">
      <BalanceCard
        label="Available"
        amount={balances.available_balance_paise}
        sub="Ready to withdraw"
        variant="available"
      />
      <BalanceCard
        label="Held"
        amount={balances.held_balance_paise}
        sub="Pending payouts"
        variant="held"
      />
      <BalanceCard
        label="Net total"
        amount={balances.net_balance_paise}
        sub="Available + Held"
        variant="net"
      />
    </div>
  );
}