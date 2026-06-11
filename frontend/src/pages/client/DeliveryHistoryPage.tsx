import { useState, useEffect } from 'react';
import { deliveryApi } from '../../services/api';
import DeliveryCard from '../../components/delivery/DeliveryCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import EmptyState from '../../components/common/EmptyState';
import { Link } from 'react-router-dom';
import { Plus } from 'lucide-react';

const STATUSES = ['ALL', 'PENDING', 'ASSIGNED', 'IN_TRANSIT', 'DELIVERED', 'CANCELLED'];

export default function DeliveryHistoryPage() {
  const [deliveries, setDeliveries] = useState<any[]>([]);
  const [filtered, setFiltered] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState('ALL');

  useEffect(() => {
    deliveryApi.list({ limit: 100 }).then(({ data }) => {
      setDeliveries(data.deliveries);
      setFiltered(data.deliveries);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setFiltered(status === 'ALL' ? deliveries : deliveries.filter((d) => d.status === status));
  }, [status, deliveries]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">My Deliveries</h1>
        <Link to="/create-delivery" className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> New
        </Link>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
              status === s ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            {s === 'ALL' ? 'All' : s.replace('_', ' ')}
            {s !== 'ALL' && (
              <span className="ml-1 opacity-70">
                ({deliveries.filter((d) => d.status === s).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><LoadingSpinner /></div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No deliveries found"
          description={status !== 'ALL' ? `No ${status.toLowerCase()} deliveries.` : 'Create your first delivery.'}
          action={status === 'ALL' && (
            <Link to="/create-delivery" className="btn-primary inline-flex items-center gap-2">
              <Plus className="w-4 h-4" /> Create Delivery
            </Link>
          )}
        />
      ) : (
        <div className="grid gap-3">
          {filtered.map((d) => <DeliveryCard key={d.id} delivery={d} />)}
        </div>
      )}
    </div>
  );
}
