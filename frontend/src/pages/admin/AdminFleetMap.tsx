import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet';
import L from 'leaflet';
import { useFleetMonitor } from '../../hooks/useWebSocket';
import { Wifi, WifiOff, Truck } from 'lucide-react';

// Custom driver icon
const driverIcon = L.divIcon({
  className: '',
  html: `<div style="
    background:#2563eb; color:white; border-radius:50%; width:32px; height:32px;
    display:flex; align-items:center; justify-content:center;
    font-size:16px; border:3px solid white;
    box-shadow:0 2px 8px rgba(0,0,0,0.3);
  ">🚗</div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

interface DriverLocation {
  driver_id: number;
  lat: number;
  lng: number;
  status: string;
  updated_at?: string;
}

export default function AdminFleetMap() {
  const [drivers, setDrivers] = useState<Map<number, DriverLocation>>(new Map());
  const { connected, lastEvent } = useFleetMonitor();

  useEffect(() => {
    if (!lastEvent) return;
    try {
      const data = typeof lastEvent === 'string' ? JSON.parse(lastEvent) : lastEvent;
      if (data.type === 'location_update' && data.driver_id) {
        setDrivers((prev) => {
          const next = new Map(prev);
          next.set(data.driver_id, {
            driver_id: data.driver_id,
            lat: data.lat,
            lng: data.lng,
            status: data.status ?? 'ONLINE',
            updated_at: data.timestamp,
          });
          return next;
        });
      }
    } catch {}
  }, [lastEvent]);

  const driverList = Array.from(drivers.values());

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Fleet Monitor</h1>
        <div className={`flex items-center gap-2 text-sm font-medium px-3 py-1.5 rounded-full ${
          connected ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'
        }`}>
          {connected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
          {connected ? 'Live' : 'Disconnected'}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card text-center">
          <p className="text-3xl font-bold text-blue-600">{driverList.length}</p>
          <p className="text-xs text-gray-500 mt-1">Active Drivers</p>
        </div>
        <div className="card text-center">
          <p className="text-3xl font-bold text-green-600">
            {driverList.filter((d) => d.status === 'ONLINE').length}
          </p>
          <p className="text-xs text-gray-500 mt-1">Online</p>
        </div>
        <div className="card text-center">
          <p className="text-3xl font-bold text-yellow-500">
            {driverList.filter((d) => d.status === 'ON_DELIVERY').length}
          </p>
          <p className="text-xs text-gray-500 mt-1">On Delivery</p>
        </div>
      </div>

      {/* Map */}
      <div className="h-[60vh] rounded-xl overflow-hidden border border-gray-200 shadow-sm">
        <MapContainer
          center={[19.076, 72.877]}
          zoom={12}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {driverList.map((driver) => (
            <Marker key={driver.driver_id} position={[driver.lat, driver.lng]} icon={driverIcon}>
              <Popup>
                <div className="text-sm">
                  <p className="font-semibold">Driver #{driver.driver_id}</p>
                  <p className="text-gray-500">{driver.status}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {driver.lat.toFixed(4)}, {driver.lng.toFixed(4)}
                  </p>
                  {driver.updated_at && (
                    <p className="text-xs text-gray-400">
                      {new Date(driver.updated_at).toLocaleTimeString()}
                    </p>
                  )}
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      {driverList.length === 0 && (
        <div className="text-center text-sm text-gray-400 py-2">
          Waiting for driver location updates...
        </div>
      )}
    </div>
  );
}
