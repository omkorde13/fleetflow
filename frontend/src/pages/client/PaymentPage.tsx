import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { deliveryApi, paymentApi } from '../../services/api';
import RazorpayButton from '../../components/payment/RazorpayButton';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import StatusBadge from '../../components/delivery/StatusBadge';
import FareBreakdown from '../../components/delivery/FareBreakdown';
import { CheckCircle, Receipt, Banknote, Loader2, Clock } from 'lucide-react';
import toast from 'react-hot-toast';

export default function PaymentPage() {
  const { deliveryId } = useParams<{ deliveryId: string }>();
  const navigate = useNavigate();
  const [delivery, setDelivery] = useState<any>(null);
  const [payment, setPayment] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [paid, setPaid] = useState(false);
  const [codLoading, setCodLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      deliveryApi.get(deliveryId!),
      paymentApi.getByDelivery(deliveryId!).then((r) => r.data),
    ]).then(([dRes, pay]) => {
      setDelivery(dRes.data);
      if (pay) {
        setPayment(pay);
        if (pay.status === 'SUCCESS') setPaid(true);
      }
    }).finally(() => setLoading(false));
  }, [deliveryId]);

  // Poll for driver confirmation while a cash payment is pending
  useEffect(() => {
    if (!deliveryId || !payment || payment.payment_method !== 'CASH' || payment.status !== 'PENDING') return;

    const interval = setInterval(() => {
      paymentApi.getByDelivery(deliveryId).then((r) => {
        if (r.data) {
          setPayment(r.data);
          if (r.data.status === 'SUCCESS') setPaid(true);
        }
      });
    }, 5000);

    return () => clearInterval(interval);
  }, [deliveryId, payment]);

  if (loading) return <div className="flex justify-center py-20"><LoadingSpinner /></div>;
  if (!delivery) return <p className="text-center text-gray-500">Delivery not found</p>;

  const handleCashPayment = async () => {
    setCodLoading(true);
    try {
      await paymentApi.payCash(delivery.id);
      toast.success('Marked as cash payment. Waiting for driver to confirm.');
      const { data } = await paymentApi.getByDelivery(delivery.id);
      setPayment(data);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to record cash payment');
    } finally {
      setCodLoading(false);
    }
  };

  if (paid) {
    return (
      <div className="max-w-md mx-auto text-center py-16">
        <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-800 mb-2">Payment Successful</h2>
        <p className="text-gray-500 mb-6">
          {payment?.payment_method === 'CASH'
            ? 'Paid via Cash on Delivery'
            : `Payment ID: ${payment?.razorpay_payment_id ?? ''}`}
        </p>
        <button onClick={() => navigate('/deliveries')} className="btn-primary">
          View Deliveries
        </button>
      </div>
    );
  }

  if (payment?.payment_method === 'CASH' && payment?.status === 'PENDING') {
    return (
      <div className="max-w-md mx-auto text-center py-16">
        <Clock className="w-16 h-16 text-amber-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-800 mb-2">Waiting for Driver Confirmation</h2>
        <p className="text-gray-500 mb-6">
          You marked ₹{(delivery.total_fare ?? 0).toFixed(0)} as paid in cash. This page will
          update automatically once the driver confirms they received the payment.
        </p>
        <button onClick={() => navigate('/deliveries')} className="btn-secondary">
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

      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-gray-200" />
        <span className="text-xs text-gray-400 uppercase">or</span>
        <div className="flex-1 h-px bg-gray-200" />
      </div>

      <div className="card">
        <p className="text-sm text-gray-500 mb-4 flex items-center gap-2">
          <Banknote className="w-4 h-4" />
          Pay the driver in cash on delivery
        </p>
        <button
          onClick={handleCashPayment}
          disabled={codLoading}
          className="btn-secondary w-full flex items-center justify-center gap-2"
        >
          {codLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Banknote className="w-4 h-4" />}
          {codLoading ? 'Processing...' : `Cash on Delivery (₹${(delivery.total_fare ?? 0).toFixed(0)})`}
        </button>
      </div>
    </div>
  );
}
