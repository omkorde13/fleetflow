import { useState } from 'react';
import { CreditCard, Loader2 } from 'lucide-react';
import { paymentApi } from '../../services/api';
import toast from 'react-hot-toast';

declare global {
  interface Window {
    Razorpay: any;
  }
}

interface RazorpayButtonProps {
  deliveryId: number;
  amount: number;
  onSuccess: () => void;
}

function loadRazorpay(): Promise<boolean> {
  return new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export default function RazorpayButton({ deliveryId, amount, onSuccess }: RazorpayButtonProps) {
  const [loading, setLoading] = useState(false);

  const handlePay = async () => {
    setLoading(true);
    try {
      const loaded = await loadRazorpay();
      if (!loaded) {
        toast.error('Failed to load payment gateway');
        return;
      }

      const { data } = await paymentApi.createOrder(deliveryId);

      const options = {
        key: data.key,
        amount: data.amount,
        currency: data.currency,
        name: 'FleetFlow',
        description: `Delivery #${deliveryId}`,
        order_id: data.razorpay_order_id,
        handler: async (response: any) => {
          try {
            await paymentApi.verify({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              delivery_id: deliveryId,
            });
            toast.success('Payment successful!');
            onSuccess();
          } catch {
            toast.error('Payment verification failed');
          }
        },
        prefill: { name: '', email: '', contact: '' },
        theme: { color: '#2563eb' },
        modal: { ondismiss: () => setLoading(false) },
      };

      new window.Razorpay(options).open();
    } catch (err) {
      toast.error('Failed to initiate payment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handlePay}
      disabled={loading}
      className="btn-primary w-full flex items-center justify-center gap-2"
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />}
      {loading ? 'Processing...' : `Pay ₹${amount.toFixed(0)}`}
    </button>
  );
}
