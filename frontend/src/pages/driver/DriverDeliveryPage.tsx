import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import L from 'leaflet';
import { deliveryApi } from '../../services/api';
import { useDriverLocationSender } from '../../hooks/useWebSocket';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import StatusBadge from '../../components/delivery/StatusBadge';
import { Navigation, Package, CheckCircle, Loader2, MapPin } from 'lucide-react';
import toast from 'react-hot-toast';

const pickupIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
  iconSize: [25, 41], iconAnchor: [12, 41],
});
const dropoffIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  iconSize: [25, 41], iconAnchor: [12, 41],
});

export default function DriverDeliveryPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [delivery, setDelivery] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);

  // Start GPS streaming for this delivery (uses the Driver profile id, which
  // is what Delivery.driver_id and the /ws/driver/{driver_id} endpoint key off)
  useDriverLocationSender(delivery?.driver_id ?? '', id);

  useEffect(() => {
    deliveryApi.get(id!).then(({ data }) => setDelivery(data)).finally(() => setLoading(false));
  }, [id]);

  const doAction = async (action: 'pickup' | 'complete') => {
    setActing(true);
    try {
      if (action === 'pickup') await deliveryApi.pickup(id!);
      else await deliveryApi.complete(id!);
      const { data } = await deliveryApi.get(id!);
      setDelivery(data);
      toast.success(action === 'pickup' ? 'Picked up successfully!' : 'Delivery completed! 🎉');
      if (action === 'complete') setTimeout(() => navigate('/driver/dashboard'), 2000);
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Action failed');
    } finally {
      setActing(false);
    }
  };

  if (loading) return <div className="flex justify-center py-20"><LoadingSpinner /></div>;
  if (!delivery) return <p className="text-center text-gray-500">Delivery not found</p>;

  const center: [number, number] = [delivery.pickup_lat, delivery.pickup_lng];
  const route: [number, number][] = [
    [delivery.pickup_lat, delivery.pickup_lng],
    [delivery.dropoff_lat, delivery.dropoff_lng],
  ];

  const canPickup = delivery.status === 'ASSIGNED';
  const canComplete = ['PICKED_UP', 'IN_TRANSIT'].includes(delivery.status);
  const isDelivered = delivery.status === 'DELIVERED';

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Delivery #{delivery.id}</h1>
        <StatusBadge status={delivery.status} />
      </div>

      {/* Map */}
      <div className="h-64 rounded-xl overflow-hidden border border-gray-200">
        <MapContainer center={center} zoom={13} style={{ height: '100%', width: '100%' }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <Marker position={[delivery.pickup_lat, delivery.pickup_lng]} icon={pickupIcon}>
            <Popup>📍 Pickup: {delivery.pickup_address}</Popup>
          </Marker>
          <Marker position={[delivery.dropoff_lat, delivery.dropoff_lng]} icon={dropoffIcon}>
            <Popup>🏁 Dropoff: {delivery.dropoff_address}</Popup>
          </Marker>
          <Polyline positions={route} color="#2563eb" weight={3} dashArray="8 4" />
        </MapContainer>
      </div>

      {/* Addresses */}
      <div className="card space-y-3">
        <div className="flex items-start gap-3">
          <MapPin className="w-5 h-5 text-green-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs text-gray-400">Pickup</p>
            <p className="text-sm font-medium text-gray-800">{delivery.pickup_address}</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <MapPin className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs text-gray-400">Dropoff</p>
            <p className="text-sm font-medium text-gray-800">{delivery.dropoff_address}</p>
          </div>
        </div>
        {delivery.package_description && (
          <div className="flex items-start gap-3">
            <Package className="w-5 h-5 text-gray-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-gray-400">Package</p>
              <p className="text-sm text-gray-700">{delivery.package_description}</p>
            </div>
          </div>
        )}
      </div>

      {/* Fare */}
      {delivery.total_fare && (
        <div className="card flex justify-between items-center">
          <span className="text-gray-600 text-sm">Delivery Fare</span>
          <span className="text-xl font-bold text-gray-900">₹{delivery.total_fare.toFixed(0)}</span>
        </div>
      )}

      {/* Actions */}
      {!isDelivered && (
        <div className="space-y-2">
          {canPickup && (
            <button onClick={() => doAction('pickup')} disabled={acting}
              className="btn-primary w-full flex items-center justify-center gap-2">
              {acting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Navigation className="w-4 h-4" />}
              {acting ? 'Updating...' : 'Mark as Picked Up'}
            </button>
          )}
          {canComplete && (
            <button onClick={() => doAction('complete')} disabled={acting}
              className="bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-lg transition-colors w-full flex items-center justify-center gap-2 disabled:opacity-50">
              {acting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
              {acting ? 'Completing...' : 'Mark as Delivered'}
            </button>
          )}
        </div>
      )}

      {isDelivered && (
        <div className="card text-center py-6">
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-2" />
          <p className="font-semibold text-gray-800">Delivery Completed!</p>
          <button onClick={() => navigate('/driver/dashboard')} className="btn-secondary mt-4">
            Back to Dashboard
          </button>
        </div>
      )}
    </div>
  );
}
