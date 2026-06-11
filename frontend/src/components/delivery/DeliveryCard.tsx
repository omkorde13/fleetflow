import { MapPin, Clock, Package } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import StatusBadge from './StatusBadge';

interface DeliveryCardProps {
  delivery: {
    id: string;
    pickup_address: string;
    dropoff_address: string;
    status: string;
    total_fare?: number;
    distance_km?: number;
    created_at: string;
    package_description?: string;
  };
  showTrack?: boolean;
}

export default function DeliveryCard({ delivery, showTrack = true }: DeliveryCardProps) {
  const navigate = useNavigate();
  const date = new Date(delivery.created_at).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  });

  return (
    <div className="card hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => showTrack && navigate(`/track/${delivery.id}`)}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono text-gray-400">#{delivery.id.slice(0, 8).toUpperCase()}</span>
          <StatusBadge status={delivery.status} />
        </div>
        {delivery.total_fare && (
          <span className="text-lg font-bold text-gray-900">
            ₹{delivery.total_fare.toFixed(0)}
          </span>
        )}
      </div>

      <div className="space-y-2 mb-3">
        <div className="flex items-start gap-2">
          <MapPin className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
          <span className="text-sm text-gray-700 line-clamp-1">{delivery.pickup_address}</span>
        </div>
        <div className="flex items-start gap-2">
          <MapPin className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
          <span className="text-sm text-gray-700 line-clamp-1">{delivery.dropoff_address}</span>
        </div>
      </div>

      <div className="flex items-center gap-4 text-xs text-gray-400">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" /> {date}
        </span>
        {delivery.distance_km && (
          <span>{delivery.distance_km.toFixed(1)} km</span>
        )}
        {delivery.package_description && (
          <span className="flex items-center gap-1">
            <Package className="w-3 h-3" />
            <span className="line-clamp-1">{delivery.package_description}</span>
          </span>
        )}
      </div>
    </div>
  );
}
