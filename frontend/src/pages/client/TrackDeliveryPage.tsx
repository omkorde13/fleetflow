import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { deliveryApi } from '@/services/api'
import { useDeliveryTracking } from '@/hooks/useWebSocket'
import { MapPin, Navigation, Package, CheckCircle, Clock, Phone } from 'lucide-react'

// Fix Leaflet marker icons in Vite
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const driverIcon = L.divIcon({
  html: `<div style="background:#3B82F6;width:32px;height:32px;border-radius:50%;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;">
    <svg width="16" height="16" fill="white" viewBox="0 0 24 24"><path d="M18 18.5a1.5 1.5 0 0 0 1.5-1.5H20V9l-3-4h-1V4a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h1a1.5 1.5 0 0 0 3 0h7a1.5 1.5 0 0 0 1.5 1.5z"/></svg>
  </div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  className: '',
})

function RecenterMap({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap()
  useEffect(() => {
    map.setView([lat, lng], map.getZoom())
  }, [lat, lng])
  return null
}

const STATUS_STEPS = ['PENDING', 'ASSIGNED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED']
const STATUS_LABELS: Record<string, string> = {
  PENDING: 'Finding Driver',
  ASSIGNED: 'Driver Assigned',
  PICKED_UP: 'Parcel Picked Up',
  IN_TRANSIT: 'On the Way',
  DELIVERED: 'Delivered!',
}

export default function TrackDeliveryPage() {
  const { deliveryId } = useParams<{ deliveryId: string }>()
  const navigate = useNavigate()
  const [delivery, setDelivery] = useState<any>(null)
  const [driverLocation, setDriverLocation] = useState<{ lat: number; lng: number } | null>(null)
  const [locationHistory, setLocationHistory] = useState<[number, number][]>([])
  const [currentStatus, setCurrentStatus] = useState<string>('')

  // Load delivery
  useEffect(() => {
    if (!deliveryId) return
    deliveryApi.get(deliveryId).then(({ data }) => {
      setDelivery(data)
      setCurrentStatus(data.status)
    })
  }, [deliveryId])

  // WebSocket tracking
  const handleLocationUpdate = useCallback((data: any) => {
    setDriverLocation({ lat: data.lat, lng: data.lng })
    setLocationHistory(prev => [...prev.slice(-50), [data.lat, data.lng]])
  }, [])

  const handleDeliveryUpdate = useCallback((data: any) => {
    setCurrentStatus(data.status)
    if (data.status === 'DELIVERED') {
      // Show celebration
    }
  }, [])

  const { isConnected } = useDeliveryTracking(
    deliveryId!,
    handleLocationUpdate,
    handleDeliveryUpdate,
  )

  if (!delivery) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full" />
      </div>
    )
  }

  const currentStep = STATUS_STEPS.indexOf(currentStatus)
  const mapCenter: [number, number] = driverLocation
    ? [driverLocation.lat, driverLocation.lng]
    : [delivery.pickup_lat, delivery.pickup_lng]

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4 flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-700">←</button>
        <div>
          <h1 className="font-semibold text-gray-900">Track Delivery</h1>
          <p className="text-sm text-gray-500">#{deliveryId?.slice(0, 8).toUpperCase()}</p>
        </div>
        <div className={`ml-auto flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
          isConnected ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
          {isConnected ? 'Live' : 'Connecting...'}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Map */}
        <div className="flex-1">
          <MapContainer center={mapCenter} zoom={14} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            />

            {/* Pickup marker */}
            <Marker position={[delivery.pickup_lat, delivery.pickup_lng]}>
              <Popup>📦 Pickup: {delivery.pickup_address}</Popup>
            </Marker>

            {/* Dropoff marker */}
            <Marker position={[delivery.dropoff_lat, delivery.dropoff_lng]}>
              <Popup>🎯 Dropoff: {delivery.dropoff_address}</Popup>
            </Marker>

            {/* Driver marker */}
            {driverLocation && (
              <Marker position={[driverLocation.lat, driverLocation.lng]} icon={driverIcon}>
                <Popup>🚗 Driver is here</Popup>
              </Marker>
            )}

            {/* Route trail */}
            {locationHistory.length > 1 && (
              <Polyline
                positions={locationHistory}
                color="#3B82F6"
                weight={3}
                opacity={0.7}
                dashArray="8"
              />
            )}

            {driverLocation && <RecenterMap lat={driverLocation.lat} lng={driverLocation.lng} />}
          </MapContainer>
        </div>

        {/* Side Panel */}
        <div className="w-80 bg-white border-l border-gray-200 flex flex-col overflow-y-auto">
          {/* Status stepper */}
          <div className="p-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900 mb-4">Delivery Status</h2>
            <div className="space-y-3">
              {STATUS_STEPS.filter(s => s !== 'IN_TRANSIT').map((step, i) => {
                const stepIndex = STATUS_STEPS.indexOf(step)
                const isDone = currentStep > stepIndex
                const isCurrent = currentStep === stepIndex
                return (
                  <div key={step} className="flex items-center gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                      isDone ? 'bg-green-500' : isCurrent ? 'bg-blue-500' : 'bg-gray-200'
                    }`}>
                      {isDone ? (
                        <CheckCircle className="w-4 h-4 text-white" />
                      ) : (
                        <span className="text-xs text-white font-bold">{i + 1}</span>
                      )}
                    </div>
                    <span className={`text-sm ${isCurrent ? 'text-blue-700 font-semibold' : isDone ? 'text-green-700' : 'text-gray-400'}`}>
                      {STATUS_LABELS[step]}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Delivery details */}
          <div className="p-4 space-y-4">
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Pickup</h3>
              <p className="text-sm text-gray-700">{delivery.pickup_address}</p>
            </div>
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Dropoff</h3>
              <p className="text-sm text-gray-700">{delivery.dropoff_address}</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">Distance</p>
                <p className="font-semibold text-gray-900">{delivery.distance_km?.toFixed(1)} km</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">Fare</p>
                <p className="font-semibold text-gray-900">₹{delivery.total_fare?.toFixed(2)}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
