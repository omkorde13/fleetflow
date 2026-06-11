import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Package, CheckCircle, Clock, TrendingUp } from 'lucide-react';
import { deliveryApi } from '../../services/api';
import DeliveryCard from '../../components/delivery/DeliveryCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import EmptyState from '../../components/common/EmptyState';
import { useAuthStore } from '../../context/authStore';

interface Stats { total: number; active: number; completed: number; }

export default function ClientDashboard() {
  const { user } = useAuthStore();
  const [deliveries, setDeliveries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<Stats>({ total: 0, active: 0, completed: 0 });

  useEffect(() => {
    deliveryApi.list({ limit: 10 }).then(({ data }) => {
      const items = data.deliveries;
      setDeliveries(items);
      setStats({
        total: data.total,
        active: items.filter((d: any) => ['PENDING','ASSIGNED','PICKED_UP','IN_TRANSIT'].includes(d.status)).length,
        completed: items.filter((d: any) => d.status === 'DELIVERED').length,
      });
    }).finally(() => setLoading(false));
  }, []);

  const statCards = [
    { label: 'Total Orders', value: stats.total, icon: Package, color: 'text-blue-600 bg-blue-50' },
    { label: 'Active', value: stats.active, icon: Clock, color: 'text-yellow-600 bg-yellow-50' },
    { label: 'Delivered', value: stats.completed, icon: CheckCircle, color: 'text-green-600 bg-green-50' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Hi, {user?.full_name?.split(' ')[0]} 👋
          </h1>
          <p className="text-gray-500 text-sm mt-1">Manage your deliveries</p>
        </div>
        <Link to="/create-delivery" className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> New Delivery
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {statCards.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card flex items-center gap-4">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{value}</p>
              <p className="text-xs text-gray-500">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Recent deliveries */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">Recent Deliveries</h2>
          <Link to="/deliveries" className="text-sm text-blue-600 hover:underline">View all</Link>
        </div>

        {loading ? (
          <div className="flex justify-center py-12"><LoadingSpinner /></div>
        ) : deliveries.length === 0 ? (
          <EmptyState
            title="No deliveries yet"
            description="Create your first delivery to get started."
            action={
              <Link to="/create-delivery" className="btn-primary inline-flex items-center gap-2">
                <Plus className="w-4 h-4" /> Create Delivery
              </Link>
            }
          />
        ) : (
          <div className="grid gap-3">
            {deliveries.slice(0, 5).map((d) => <DeliveryCard key={d.id} delivery={d} />)}
          </div>
        )}
      </div>
    </div>
  );
}
