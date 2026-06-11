import { useState, useEffect } from 'react';
import { driverApi } from '../../services/api';
import { useAuthStore } from '../../context/authStore';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import { User, Truck, FileText, Star, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

export default function DriverProfilePage() {
  const { user } = useAuthStore();
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    vehicle_type: 'TWO_WHEELER',
    vehicle_number: '',
    license_number: '',
  });

  useEffect(() => {
    driverApi.getProfile().then(({ data }) => setProfile(data))
      .catch(() => setProfile(null))
      .finally(() => setLoading(false));
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const { data } = await driverApi.createProfile(form);
      setProfile(data);
      toast.success('Driver profile created!');
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Failed to create profile');
    } finally {
      setCreating(false);
    }
  };

  if (loading) return <div className="flex justify-center py-20"><LoadingSpinner /></div>;

  // No profile yet — show creation form
  if (!profile) {
    return (
      <div className="max-w-md mx-auto space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Create Driver Profile</h1>
        <div className="card">
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Vehicle Type</label>
              <select name="vehicle_type" value={form.vehicle_type} onChange={handleChange} className="input-field">
                <option value="TWO_WHEELER">Two Wheeler</option>
                <option value="THREE_WHEELER">Three Wheeler</option>
                <option value="FOUR_WHEELER">Four Wheeler</option>
                <option value="TRUCK">Truck</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Vehicle Number</label>
              <input name="vehicle_number" required value={form.vehicle_number} onChange={handleChange}
                className="input-field font-mono" placeholder="MH12AB1234" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">License Number</label>
              <input name="license_number" required value={form.license_number} onChange={handleChange}
                className="input-field font-mono" placeholder="MH-12-20XX-XXXXXXX" />
            </div>
            <button type="submit" disabled={creating} className="btn-primary w-full flex items-center justify-center gap-2">
              {creating && <Loader2 className="w-4 h-4 animate-spin" />}
              Create Profile
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Driver Profile</h1>

      {/* Profile card */}
      <div className="card">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-14 h-14 bg-blue-100 rounded-2xl flex items-center justify-center">
            <User className="w-7 h-7 text-blue-600" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900">{user?.full_name}</h2>
            <p className="text-sm text-gray-500">{user?.email}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-50 rounded-xl p-3">
            <div className="flex items-center gap-2 mb-1">
              <Star className="w-4 h-4 text-yellow-500" />
              <span className="text-xs text-gray-500">Rating</span>
            </div>
            <p className="text-xl font-bold text-gray-900">
              {profile.rating?.toFixed(1) ?? '—'}/5.0
            </p>
          </div>
          <div className="bg-gray-50 rounded-xl p-3">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span className="text-xs text-gray-500">Deliveries</span>
            </div>
            <p className="text-xl font-bold text-gray-900">{profile.total_deliveries}</p>
          </div>
        </div>
      </div>

      {/* Vehicle details */}
      <div className="card">
        <h3 className="font-semibold text-gray-700 flex items-center gap-2 mb-4">
          <Truck className="w-4 h-4" /> Vehicle Details
        </h3>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-500">Type</dt>
            <dd className="font-medium text-gray-800">{profile.vehicle_type.replace('_', ' ')}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Number</dt>
            <dd className="font-mono font-medium text-gray-800">{profile.vehicle_number}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">License</dt>
            <dd className="font-mono font-medium text-gray-800">{profile.license_number}</dd>
          </div>
        </dl>
      </div>

      {/* Verification status */}
      <div className="card">
        <h3 className="font-semibold text-gray-700 flex items-center gap-2 mb-3">
          <FileText className="w-4 h-4" /> Verification Status
        </h3>
        <div className={`flex items-center gap-3 p-3 rounded-xl ${
          profile.is_verified ? 'bg-green-50' : 'bg-yellow-50'
        }`}>
          {profile.is_verified
            ? <CheckCircle className="w-5 h-5 text-green-500 shrink-0" />
            : <AlertCircle className="w-5 h-5 text-yellow-500 shrink-0" />
          }
          <div>
            <p className={`font-medium text-sm ${profile.is_verified ? 'text-green-700' : 'text-yellow-700'}`}>
              {profile.is_verified ? 'Verified Driver' : 'Pending Verification'}
            </p>
            <p className={`text-xs mt-0.5 ${profile.is_verified ? 'text-green-600' : 'text-yellow-600'}`}>
              {profile.is_verified
                ? 'Your account is fully verified and active.'
                : 'Admin review in progress. Usually takes 1–2 business days.'}
            </p>
          </div>
        </div>
      </div>

      {profile.is_suspended && (
        <div className="card border-red-200 bg-red-50">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
            <p className="text-sm text-red-700 font-medium">
              Your account has been suspended. Contact support.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
