import { useState, useEffect } from 'react';
import { offerApi } from '../../services/api';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import EmptyState from '../../components/common/EmptyState';
import { Tag, Plus, ToggleLeft, ToggleRight, Loader2, X } from 'lucide-react';
import toast from 'react-hot-toast';

export default function AdminOffers() {
  const [offers, setOffers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [disabling, setDisabling] = useState<string | null>(null);
  const [form, setForm] = useState({
    code: '', title: '', description: '', offer_type: 'PERCENTAGE',
    value: '', max_discount: '', min_order_value: '', max_uses: '',
    valid_from: '', valid_until: '',
  });

  useEffect(() => {
    offerApi.listActive().then(({ data }) => setOffers(data)).finally(() => setLoading(false));
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const { data } = await offerApi.create({
        ...form,
        discount_value: parseFloat(form.value),
        max_discount: form.max_discount ? parseFloat(form.max_discount) : undefined,
        min_order_value: parseFloat(form.min_order_value || '0'),
        usage_limit: form.max_uses ? parseInt(form.max_uses) : undefined,
      });
      setOffers((prev) => [data, ...prev]);
      setShowForm(false);
      toast.success('Offer created!');
      setForm({ code: '', title: '', description: '', offer_type: 'PERCENTAGE', value: '', max_discount: '', min_order_value: '', max_uses: '', valid_from: '', valid_until: '' });
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Failed to create offer');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDisable = async (id: string) => {
    setDisabling(id);
    try {
      await offerApi.disable(id);
      setOffers((prev) => prev.map((o) => o.id === id ? { ...o, is_active: false } : o));
      toast.success('Offer disabled');
    } catch {
      toast.error('Failed to disable');
    } finally {
      setDisabling(null);
    }
  };

  const formatValue = (o: any) => {
    if (o.offer_type === 'PERCENTAGE') return `${o.discount_value}% off`;
    if (o.offer_type === 'FLAT') return `₹${o.discount_value} off`;
    return 'Free Delivery';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Offers</h1>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2">
          {showForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          {showForm ? 'Cancel' : 'New Offer'}
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="card">
          <h3 className="font-semibold text-gray-700 mb-4">Create Offer</h3>
          <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Coupon Code</label>
                <input name="code" required value={form.code} onChange={handleChange}
                  className="input-field font-mono uppercase" placeholder="SAVE20" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Offer Type</label>
                <select name="offer_type" value={form.offer_type} onChange={handleChange} className="input-field">
                  <option value="PERCENTAGE">Percentage</option>
                  <option value="FLAT">Flat Discount</option>
                  <option value="FREE_DELIVERY">Free Delivery</option>
                </select>
              </div>
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Title</label>
              <input name="title" required value={form.title} onChange={handleChange}
                className="input-field" placeholder="Save 20% on your next order" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                {form.offer_type === 'PERCENTAGE' ? 'Percentage (%)' : 'Flat Amount (₹)'}
              </label>
              <input name="value" type="number" required value={form.value} onChange={handleChange}
                className="input-field" placeholder={form.offer_type === 'PERCENTAGE' ? '20' : '50'} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Max Discount (₹)</label>
              <input name="max_discount" type="number" value={form.max_discount} onChange={handleChange}
                className="input-field" placeholder="100 (optional)" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Min Order Value (₹)</label>
              <input name="min_order_value" type="number" value={form.min_order_value} onChange={handleChange}
                className="input-field" placeholder="0" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Max Uses</label>
              <input name="max_uses" type="number" value={form.max_uses} onChange={handleChange}
                className="input-field" placeholder="Unlimited" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Valid From</label>
              <input name="valid_from" type="datetime-local" required value={form.valid_from} onChange={handleChange}
                className="input-field" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Valid Until</label>
              <input name="valid_until" type="datetime-local" required value={form.valid_until} onChange={handleChange}
                className="input-field" />
            </div>
            <div className="sm:col-span-2">
              <button type="submit" disabled={submitting} className="btn-primary flex items-center gap-2">
                {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                Create Offer
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12"><LoadingSpinner /></div>
      ) : offers.length === 0 ? (
        <EmptyState icon={<Tag className="w-16 h-16" />} title="No offers yet"
          description="Create your first offer to attract customers." />
      ) : (
        <div className="grid gap-3">
          {offers.map((o) => (
            <div key={o.id} className={`card flex items-center justify-between ${!o.is_active ? 'opacity-60' : ''}`}>
              <div className="flex items-center gap-4">
                <div className="bg-blue-50 text-blue-700 font-mono font-bold text-sm px-3 py-2 rounded-lg">
                  {o.code}
                </div>
                <div>
                  <p className="font-medium text-gray-800">{o.title}</p>
                  <p className="text-sm text-gray-500">{formatValue(o)} · {o.used_count} uses</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={o.is_active ? 'badge-green' : 'badge-gray'}>
                  {o.is_active ? 'Active' : 'Disabled'}
                </span>
                {o.is_active && (
                  <button onClick={() => handleDisable(o.id)} disabled={disabling === o.id}
                    className="text-gray-400 hover:text-red-500 transition-colors p-1">
                    {disabling === o.id
                      ? <Loader2 className="w-4 h-4 animate-spin" />
                      : <ToggleRight className="w-5 h-5" />}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
