import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { deliveryApi, paymentApi } from '../../services/api';
import RazorpayButton from '../../components/payment/RazorpayButton';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import StatusBadge from '../../components/delivery/StatusBadge';
import FareBreakdown from '../../components/delivery/FareBreakdown';
import { CheckCircle, Receipt } from 'lucide-react';
import toast from 'react-hot-toast';

export default function PaymentPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [delivery, setDelivery] = useState<any>(null);
  const [payment, setPayment] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [paid, setPaid] = useState(false);

  useEffect(() => {
    Promise.all([
      deliveryApi.get(id!),
      paymentApi.history().then((r) => r.data.find((p: any) => p.delivery_id === id)),
    ]).then(([dRes, pay]) => {
      setDelivery(dRes.data);
      if (pay) {
        setPayment(pay);
        if (pay.status === 'SUCCESS') setPaid(true);
      }
    }).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="flex justify-center py-20"><LoadingSpinner /></div>;
  if (!delivery) return <p className="text-center text-gray-500">Delivery not found</p>;

  if (paid) {
    return (
      <div className="max-w-md mx-auto text-center py-16">
        <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-800 mb-2">Payment Successful</h2>
        <p className="text-gray-500 mb-6">Payment ID: {payment?.razorpay_payment_id}</p>
        <button onClick={() => navigate('/deliveries')} className="btn-primary">
          View Deliveries
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Payment</h1>

      <div className="card space-y-3">
        <div className="flex items-center justify-between">
          <span className="font-medium text-gray-700">Delivery #{delivery.id}</span>
          <StatusBadge status={delivery.status} />
        </div>
        <div className="text-sm text-gray-500 space-y-1">
          <p>From: {delivery.pickup_address}</p>
          <p>To: {delivery.dropoff_address}</p>
        </div>
      </div>

      {delivery.total_fare && (
        <FareBreakdown
          baseFare={delivery.base_fare ?? 0}
          distanceFare={(delivery.total_fare - (delivery.base_fare ?? 0) + (delivery.discount_amount ?? 0))}
          distanceKm={delivery.distance_km ?? 0}
          weatherMultiplier={1}
          surgeMultiplier={delivery.surge_multiplier ?? 1}
          discount={delivery.discount_amount ?? 0}
          total={delivery.total_fare}
        />
      )}

      <div className="card">
        <p className="text-sm text-gray-500 mb-4 flex items-center gap-2">
          <Receipt className="w-4 h-4" />
          Secure payment powered by Razorpay
        </p>
        <RazorpayButton
          deliveryId={delivery.id}
          amount={delivery.total_fare ?? 0}
          onSuccess={() => { setPaid(true); }}
        />
      </div>
    </div>
  );
}
