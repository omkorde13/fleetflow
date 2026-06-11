type DeliveryStatus =
  | 'PENDING'
  | 'ASSIGNED'
  | 'PICKED_UP'
  | 'IN_TRANSIT'
  | 'DELIVERED'
  | 'CANCELLED';

const config: Record<DeliveryStatus, { label: string; className: string }> = {
  PENDING:    { label: 'Pending',    className: 'badge-yellow' },
  ASSIGNED:   { label: 'Assigned',   className: 'badge-blue' },
  PICKED_UP:  { label: 'Picked Up',  className: 'badge-blue' },
  IN_TRANSIT: { label: 'In Transit', className: 'badge-blue' },
  DELIVERED:  { label: 'Delivered',  className: 'badge-green' },
  CANCELLED:  { label: 'Cancelled',  className: 'badge-red' },
};

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const { label, className } = config[status as DeliveryStatus] ?? {
    label: status,
    className: 'badge-gray',
  };
  return <span className={className}>{label}</span>;
}
