interface FareBreakdownProps {
  baseFare: number;
  distanceFare: number;
  distanceKm: number;
  weatherMultiplier: number;
  surgeMultiplier: number;
  discount?: number;
  total: number;
  couponCode?: string;
}

export default function FareBreakdown({
  baseFare, distanceFare, distanceKm, weatherMultiplier,
  surgeMultiplier, discount = 0, total, couponCode,
}: FareBreakdownProps) {
  const subtotal = baseFare + distanceFare;

  return (
    <div className="bg-gray-50 rounded-xl p-4 space-y-2 text-sm">
      <h4 className="font-semibold text-gray-700 mb-3">Fare Breakdown</h4>

      <Row label="Base Fare" value={`₹${baseFare.toFixed(0)}`} />
      <Row label={`Distance (${distanceKm.toFixed(1)} km)`} value={`₹${distanceFare.toFixed(0)}`} />

      {weatherMultiplier > 1 && (
        <Row label="Weather Surcharge" value={`×${weatherMultiplier.toFixed(1)}`} highlight />
      )}
      {surgeMultiplier > 1 && (
        <Row label="Surge Pricing" value={`×${surgeMultiplier.toFixed(1)}`} highlight />
      )}

      <div className="border-t border-gray-200 pt-2">
        <Row label="Subtotal" value={`₹${subtotal.toFixed(0)}`} />
      </div>

      {discount > 0 && (
        <Row
          label={couponCode ? `Coupon (${couponCode})` : 'Discount'}
          value={`-₹${discount.toFixed(0)}`}
          className="text-green-600 font-medium"
        />
      )}

      <div className="border-t border-gray-300 pt-2">
        <Row label="Total" value={`₹${total.toFixed(0)}`} bold />
      </div>
    </div>
  );
}

function Row({
  label, value, bold, highlight, className = '',
}: {
  label: string;
  value: string;
  bold?: boolean;
  highlight?: boolean;
  className?: string;
}) {
  return (
    <div className={`flex justify-between ${bold ? 'font-bold text-base' : ''} ${highlight ? 'text-orange-600' : ''} ${className}`}>
      <span className="text-gray-600">{label}</span>
      <span className="text-gray-900">{value}</span>
    </div>
  );
}
