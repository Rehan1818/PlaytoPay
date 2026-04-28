type Props = {
    value: number;
    onChange: (id: number) => void;
  };
  
  export function MerchantSelector({ value, onChange }: Props) {
    return (
      <div className="merchant-selector">
        <span className="merchant-label">Merchant</span>
        <select
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="merchant-select"
        >
          {[1, 2, 3].map((id) => (
            <option key={id} value={id}>
              #{id}
            </option>
          ))}
        </select>
      </div>
    );
  }