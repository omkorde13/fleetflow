import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { deliveryApi, driverApi } from '../../services/api';
import { MapPin, Package, CheckCircle, XCircle, ToggleLeft, ToggleRight, Loader2 } from 'lucide-react';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import EmptyState from '../../components/common/EmptyState';
import { useAuthStore } from '../../context/authStore';
import toast from 'react-hot-toast';

const STATUS_LABELS: Record<string, string> = {
  ONLINE: 'Online', OFFLINE: 'Offline', BUSY: 'Busy', ON_DELIVERY: 'On Delivery',
};

export default function DriverDashboard() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [pending, setPending] = useState<any[]>([]);
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);
  const [accepting, setAccepting] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const [profileRes, deliveriesRes] = await Promise.all([
        driverApi.getProfile(),
        deliveryApi.list({ status: 'PENDING', limit: 20 }),
      ]);
      setProfile(profileRes.data);
      setPending(deliveriesRes.data.deliveries);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const toggleStatus = async () => {
    if (!profile) return;
    const next = profile.status === 'ONLINE' ? 'OFFLINE' : 'ONLINE';
    setToggling(true);
    try {
      await driverApi.updateStatus(next);
      setProfile((p: any) => ({ ...p, status: next }));
      toast.success(`You are now ${next.toLowerCase()}`);
    } catch {
      toast.error('Failed to update status');
    } finally {
      setToggling(false);
    }
  };

  const acceptDelivery = async (id: string) => {
    setAccepting(id);
    try {
      await deliveryApi.accept(id);
      toast.success('Delivery accepted!');
      navigate(`/driver/delivery/${id}`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Failed to accept');
    } finally {
      setAccepting(null);
    }
  };

  if (loading) return <div className="flex justify-center py-20"><LoadingSpinner /></div>;

  const isOnline = profile?.status === 'ONLINE';

  return (
    <div className="space-y-6">
      {/* Status card */}
      <div className={`card flex items-center justify-between ${isOnline ? 'border-green-200 bg-green-50' : 'border-gray-200'}`}>
        <div>
          <h2 className="text-lg font-bold text-gray-900">
            Hi, {user?.full_name?.split(' ')[0]} 👋
          </h2>
          <p className={`text-sm font-medium mt-1 ${isOnline ? 'text-green-600' : 'text-gray-500'}`}>
            {STATUS_LABELS[profile?.status ?? 'OFFLINE']}
          </p>
        </div>
        <button onClick={toggleStatus} disabled={toggling}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-colors ${
            isOnline ? 'bg-green-100 text-green-700 hover:bg-green-200' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}>
          {toggling ? <Loader2 className="w-4 h-4 animate-spin" /> :
            isOnline ? <ToggleRight className="w-5 h-5" /> : <ToggleLeft className="w-5 h-5" />}
          {isOnline ? 'Go Offline' : 'Go Online'}
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="card text-center">
          <p className="text-3xl font-bold text-blue-600">{profile?.total_deliveries ?? 0}</p>
          <p className="text-xs text-gray-500 mt-1">Total Deliveries</p>
        </div>
        <div className="card text-center">
          <p className="text-3xl font-bold text-yellow-500">
            {profile?.rating?.toFixed(1) ?? '—'}
          </p>
          <p className="text-xs text-gray-500 mt-1">Avg Rating ⭐</p>
        </div>
      </div>

      {/* Pending orders */}
      <div>
        <h3 className="text-lg font-semibold text-gray-800 mb-3">
          Available Orders {pending.length > 0 && `(${pending.length})`}
        </h3>

        {!isOnline ? (
          <div className="card text-center py-8 text-gray-400">
            <ToggleLeft className="w-12 h-12 mx-auto mb-3 opacity-40" />
            <p className="text-sm">Go online to see available deliveries</p>
          </div>
        ) : pending.length === 0 ? (
          <EmptyState title="No pending orders" description="New delivery requests will appear here." />
        ) : (
          <div className="space-y-3">
            {pending.map((d) => (
              <div key={d.id} className="card">
                <div className="flex justify-between items-start mb-3">
                  <span className="text-xs font-mono text-gray-400">#{d.id}</span>
                  {d.total_fare && <span className="font-bold text-lg text-gray-900">₹{d.total_fare.toFixed(0)}</span>}
                </div>

                <div className="space-y-2 mb-4">
                  <div className="flex items-start gap-2">
                    <MapPin className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                    <span className="text-sm text-gray-700 line-clamp-1">{d.pickup_address}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <MapPin className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
                    <span className="text-sm text-gray-700 line-clamp-1">{d.dropoff_address}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs text-gray-400 mb-4">
                  {d.distance_km && <span>{d.distance_km.toFixed(1)} km</span>}
                  {d.package_description && (
                    <span className="flex items-center gap-1">
                      <Package className="w-3 h-3" /> {d.package_description}
                    </span>
                  )}
                </div>

                <button
                  onClick={() => acceptDelivery(d.id)}
                  disabled={accepting === d.id}
                  className="btn-primary w-full flex items-center justify-center gap-2"
                >
                  {accepting === d.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                  {accepting === d.id ? 'Accepting...' : 'Accept Delivery'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
