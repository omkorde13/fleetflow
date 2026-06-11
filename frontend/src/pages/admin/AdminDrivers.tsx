import { useState, useEffect } from 'react';
import { adminApi } from '../../services/api';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import { Search, ShieldCheck, Ban, Star, Truck } from 'lucide-react';
import toast from 'react-hot-toast';

const STATUS_COLOR: Record<string, string> = {
  ONLINE: 'badge-green', OFFLINE: 'badge-gray', BUSY: 'badge-yellow', ON_DELIVERY: 'badge-blue',
};

export default function AdminDrivers() {
  const [drivers, setDrivers] = useState<any[]>([]);
  const [filtered, setFiltered] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [acting, setActing] = useState<string | null>(null);

  useEffect(() => {
    adminApi.listDrivers().then(({ data }) => { setDrivers(data.drivers); setFiltered(data.drivers); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const q = search.toLowerCase();
    setFiltered(q ? drivers.filter((d) =>
      d.vehicle_number?.toLowerCase().includes(q) ||
      d.license_number?.toLowerCase().includes(q) ||
      d.user?.full_name?.toLowerCase().includes(q)
    ) : drivers);
  }, [search, drivers]);

  const verify = async (driver: any) => {
    setActing(driver.id);
    try {
      await adminApi.verifyDriver(driver.id);
      setDrivers((prev) => prev.map((d) => d.id === driver.id ? { ...d, is_verified: true } : d));
      toast.success('Driver verified!');
    } catch {
      toast.error('Failed to verify');
    } finally {
      setActing(null);
    }
  };

  const suspend = async (driver: any) => {
    if (!confirm(`Suspend ${driver.user?.full_name}?`)) return;
    setActing(driver.id);
    try {
      await adminApi.suspendDriver(driver.id);
      setDrivers((prev) => prev.map((d) => d.id === driver.id ? { ...d, is_suspended: true } : d));
      toast.success('Driver suspended');
    } catch {
      toast.error('Failed to suspend');
    } finally {
      setActing(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Drivers</h1>
        <span className="text-sm text-gray-500">{drivers.length} registered</span>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input placeholder="Search by name, vehicle, license..."
          value={search} onChange={(e) => setSearch(e.target.value)} className="input-field pl-9" />
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><LoadingSpinner /></div>
      ) : (
        <div className="grid gap-4">
          {filtered.map((driver) => (
            <div key={driver.id} className="card">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-gray-900">
                      {driver.user?.full_name ?? `Driver #${driver.id}`}
                    </h3>
                    {driver.is_verified && (
                      <ShieldCheck className="w-4 h-4 text-blue-500" title="Verified" />
                    )}
                    {driver.is_suspended && (
                      <Ban className="w-4 h-4 text-red-500" title="Suspended" />
                    )}
                  </div>
                  <p className="text-xs text-gray-400">{driver.user?.email}</p>
                </div>
                <span className={STATUS_COLOR[driver.status] ?? 'badge-gray'}>{driver.status}</span>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm mb-3">
                <div className="bg-gray-50 rounded-lg p-2">
                  <p className="text-xs text-gray-400">Vehicle</p>
                  <p className="font-medium text-gray-700">
                    {driver.vehicle_type?.replace('_', ' ')} · {driver.vehicle_number}
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-2">
                  <p className="text-xs text-gray-400">Rating / Deliveries</p>
                  <p className="font-medium text-gray-700 flex items-center gap-1">
                    <Star className="w-3 h-3 text-yellow-500" />
                    {driver.rating?.toFixed(1) ?? '—'} · {driver.total_deliveries} trips
                  </p>
                </div>
              </div>

              {!driver.is_suspended && (
                <div className="flex gap-2">
                  {!driver.is_verified && (
                    <button onClick={() => verify(driver)} disabled={acting === driver.id}
                      className="btn-primary flex-1 flex items-center justify-center gap-1.5 text-sm py-1.5">
                      <ShieldCheck className="w-4 h-4" /> Verify
                    </button>
                  )}
                  <button onClick={() => suspend(driver)} disabled={acting === driver.id}
                    className="btn-danger flex-1 flex items-center justify-center gap-1.5 text-sm py-1.5">
                    <Ban className="w-4 h-4" /> Suspend
                  </button>
                </div>
              )}
            </div>
          ))}
          {filtered.length === 0 && <p className="text-center text-gray-400 py-8">No drivers found</p>}
        </div>
      )}
    </div>
  );
}
