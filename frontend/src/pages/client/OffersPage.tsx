import { useState, useEffect } from 'react';
import { offerApi } from '../../services/api';
import { Tag, Copy, CheckCircle, Clock } from 'lucide-react';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import EmptyState from '../../components/common/EmptyState';
import toast from 'react-hot-toast';

export default function OffersPage() {
  const [offers, setOffers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    offerApi.listActive().then(({ data }) => setOffers(data)).finally(() => setLoading(false));
  }, []);

  const copyCode = (id: string, code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(id);
    toast.success(`Copied: ${code}`);
    setTimeout(() => setCopied(null), 2000);
  };

  const formatDiscount = (o: any) => {
    if (o.offer_type === 'PERCENTAGE') return `${o.discount_value}% off`;
    if (o.offer_type === 'FLAT') return `₹${o.discount_value} off`;
    return 'Free Delivery';
  };

  const validUntil = (d: string) =>
    new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });

  if (loading) return <div className="flex justify-center py-20"><LoadingSpinner /></div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Offers & Coupons</h1>

      {offers.length === 0 ? (
        <EmptyState icon={<Tag className="w-16 h-16" />} title="No offers available"
          description="Check back later for exclusive deals." />
      ) : (
        <div className="grid gap-4">
          {offers.map((o) => (
            <div key={o.id} className="card relative overflow-hidden">
              {/* Left accent */}
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-600 rounded-l-xl" />
              <div className="pl-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-bold text-gray-900 text-lg">{formatDiscount(o)}</h3>
                    <p className="text-sm font-medium text-gray-600 mt-0.5">{o.title}</p>
                  </div>
                  <button
                    onClick={() => copyCode(o.id, o.code)}
                    className="flex items-center gap-1.5 bg-blue-50 text-blue-700 px-3 py-1.5 rounded-lg text-sm font-mono font-medium hover:bg-blue-100 transition-colors"
                  >
                    {copied === o.id ? <CheckCircle className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    {o.code}
                  </button>
                </div>

                {o.description && <p className="text-sm text-gray-500 mt-2">{o.description}</p>}

                <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
                  {o.min_order_value > 0 && <span>Min order ₹{o.min_order_value}</span>}
                  {o.max_discount && <span>Max discount ₹{o.max_discount}</span>}
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" /> Valid till {validUntil(o.valid_until)}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
