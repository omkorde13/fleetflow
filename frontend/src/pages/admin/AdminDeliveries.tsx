import { useState, useEffect } from 'react';
import { deliveryApi } from '../../services/api';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import StatusBadge from '../../components/delivery/StatusBadge';
import { Search, MapPin } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function AdminDeliveries() {
  const navigate = useNavigate();
  const [deliveries, setDeliveries] = useState<any[]>([]);
  const [filtered, setFiltered] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('ALL');

  const STATUSES = ['ALL', 'PENDING', 'ASSIGNED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED', 'CANCELLED'];

  useEffect(() => {
    deliveryApi.list({ limit: 200 }).then(({ data }) => {
      setDeliveries(data.deliveries); setFiltered(data.deliveries);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    let result = deliveries;
    if (status !== 'ALL') result = result.filter((d) => d.status === status);
    if (search) {
      const q = search.toLowerCase();
      result = result.filter((d) =>
        d.pickup_address.toLowerCase().includes(q) ||
        d.dropoff_address.toLowerCase().includes(q) ||
        String(d.id).includes(q)
      );
    }
    setFiltered(result);
  }, [search, status, deliveries]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Deliveries</h1>
        <span className="text-sm text-gray-500">{deliveries.length} total</span>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input placeholder="Search by ID or address..." value={search}
          onChange={(e) => setSearch(e.target.value)} className="input-field pl-9" />
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {STATUSES.map((s) => (
          <button key={s} onClick={() => setStatus(s)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
              status === s ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}>
            {s === 'ALL' ? 'All' : s.replace('_', ' ')}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><LoadingSpinner /></div>
      ) : (
        <div className="card p-0 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">ID</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Route</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Fare</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Date</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((d) => (
                <tr key={d.id} className="hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => navigate(`/track/${d.id}`)}>
                  <td className="px-4 py-3 font-mono text-gray-600">#{String(d.id).slice(0, 8).toUpperCase()}</td>
                  <td className="px-4 py-3">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-1.5 text-xs text-gray-500">
                        <MapPin className="w-3 h-3 text-green-500 shrink-0" />
                        <span className="line-clamp-1 max-w-xs">{d.pickup_address}</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs text-gray-500">
                        <MapPin className="w-3 h-3 text-red-500 shrink-0" />
                        <span className="line-clamp-1 max-w-xs">{d.dropoff_address}</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={d.status} /></td>
                  <td className="px-4 py-3 font-medium">{d.total_fare ? `₹${d.total_fare.toFixed(0)}` : '—'}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(d.created_at).toLocaleDateString('en-IN')}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-blue-600 text-xs hover:underline">Track →</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && <p className="text-center text-gray-400 py-8">No deliveries found</p>}
        </div>
      )}
    </div>
  );
}
