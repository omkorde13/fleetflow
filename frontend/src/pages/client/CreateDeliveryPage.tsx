import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Tag, Package } from 'lucide-react';
import toast from 'react-hot-toast';
import { deliveryApi } from '../../services/api';
import MapPicker from '../../components/map/MapPicker';
import FareBreakdown from '../../components/delivery/FareBreakdown';

interface Location { lat: number; lng: number; address: string; }
interface FareEstimate {
  base_fare: number; distance_km: number; distance_fare: number;
  weather_multiplier: number; surge_multiplier: number;
  discount: number; total_fare: number; coupon_code?: string;
}

export default function CreateDeliveryPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(1);
  const [submitting, setSubmitting] = useState(false);
  const [estimating, setEstimating] = useState(false);
  const [fareEstimate, setFareEstimate] = useState<FareEstimate | null>(null);

  const [pickup, setPickup] = useState<Location>({ lat: 0, lng: 0, address: '' });
  const [dropoff, setDropoff] = useState<Location>({ lat: 0, lng: 0, address: '' });
  const [coupon, setCoupon] = useState('');
  const [packageDesc, setPackageDesc] = useState('');
  const [packageWeight, setPackageWeight] = useState('');
  const [notes, setNotes] = useState('');

  const handleEstimate = async () => {
    if (!pickup.lat || !dropoff.lat) { toast.error('Select pickup and dropoff locations'); return; }
    if (!pickup.address || !dropoff.address) { toast.error('Enter addresses for both locations'); return; }
    setEstimating(true);
    try {
      const { data } = await deliveryApi.estimateFare({
        pickup_lat: pickup.lat, pickup_lng: pickup.lng,
        dropoff_lat: dropoff.lat, dropoff_lng: dropoff.lng,
        coupon_code: coupon || undefined,
      });
      setFareEstimate(data);
      setStep(2);
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Estimation failed');
    } finally {
      setEstimating(false);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const { data } = await deliveryApi.create({
        pickup_address: pickup.address, pickup_lat: pickup.lat, pickup_lng: pickup.lng,
        dropoff_address: dropoff.address, dropoff_lat: dropoff.lat, dropoff_lng: dropoff.lng,
        parcel_description: packageDesc || undefined,
        parcel_weight: packageWeight ? parseFloat(packageWeight) : undefined,
        coupon_code: coupon || undefined,
        special_instructions: notes || undefined,
      });
      toast.success('Delivery created!');
      navigate(`/track/${data.id}`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Failed to create delivery');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">New Delivery</h1>

      {step === 1 && (
        <div className="space-y-6">
          {/* Pickup */}
          <div className="card space-y-3">
            <h3 className="font-semibold text-gray-700">📍 Pickup Location</h3>
            <input placeholder="Pickup address" value={pickup.address}
              onChange={(e) => setPickup((p) => ({ ...p, address: e.target.value }))}
              className="input-field" />
            <MapPicker label="" lat={pickup.lat || undefined} lng={pickup.lng || undefined}
              onChange={(lat, lng) => setPickup((p) => ({ ...p, lat, lng }))}
              onAddressChange={(address) => setPickup((p) => ({ ...p, address }))} />
          </div>

          {/* Dropoff */}
          <div className="card space-y-3">
            <h3 className="font-semibold text-gray-700">🏁 Dropoff Location</h3>
            <input placeholder="Dropoff address" value={dropoff.address}
              onChange={(e) => setDropoff((p) => ({ ...p, address: e.target.value }))}
              className="input-field" />
            <MapPicker label="" lat={dropoff.lat || undefined} lng={dropoff.lng || undefined}
              onChange={(lat, lng) => setDropoff((p) => ({ ...p, lat, lng }))}
              onAddressChange={(address) => setDropoff((p) => ({ ...p, address }))} />
          </div>

          {/* Package details */}
          <div className="card space-y-3">
            <h3 className="font-semibold text-gray-700 flex items-center gap-2">
              <Package className="w-4 h-4" /> Package Details (optional)
            </h3>
            <input placeholder="Package description (e.g. Electronics)" value={packageDesc}
              onChange={(e) => setPackageDesc(e.target.value)} className="input-field" />
            <input placeholder="Weight in kg" type="number" value={packageWeight}
              onChange={(e) => setPackageWeight(e.target.value)} className="input-field" />
            <textarea placeholder="Delivery notes" value={notes} rows={2}
              onChange={(e) => setNotes(e.target.value)}
              className="input-field resize-none" />
          </div>

          {/* Coupon */}
          <div className="card">
            <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <Tag className="w-4 h-4" /> Coupon Code (optional)
            </label>
            <input placeholder="Enter coupon code" value={coupon}
              onChange={(e) => setCoupon(e.target.value.toUpperCase())}
              className="input-field font-mono" />
          </div>

          <button onClick={handleEstimate} disabled={estimating} className="btn-primary w-full flex items-center justify-center gap-2">
            {estimating && <Loader2 className="w-4 h-4 animate-spin" />}
            {estimating ? 'Calculating fare...' : 'Get Fare Estimate →'}
          </button>
        </div>
      )}

      {step === 2 && fareEstimate && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="card space-y-2">
            <h3 className="font-semibold text-gray-700 mb-3">Order Summary</h3>
            <div className="text-sm text-gray-600">
              <p><span className="font-medium">From:</span> {pickup.address}</p>
              <p><span className="font-medium">To:</span> {dropoff.address}</p>
            </div>
          </div>

          <FareBreakdown
            baseFare={fareEstimate.base_fare}
            distanceFare={fareEstimate.distance_fare}
            distanceKm={fareEstimate.distance_km}
            weatherMultiplier={fareEstimate.weather_multiplier}
            surgeMultiplier={fareEstimate.surge_multiplier}
            discount={fareEstimate.discount}
            total={fareEstimate.total_fare}
            couponCode={coupon}
          />

          <div className="flex gap-3">
            <button onClick={() => setStep(1)} className="btn-secondary flex-1">← Edit</button>
            <button onClick={handleSubmit} disabled={submitting} className="btn-primary flex-1 flex items-center justify-center gap-2">
              {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
              {submitting ? 'Creating...' : 'Confirm & Create'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
