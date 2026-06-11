import { useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Search, Crosshair, Loader2 } from 'lucide-react';
import { searchPlaces, reverseGeocode, type GeocodeResult } from '../../services/geocoding';

// Fix Leaflet marker icons in Vite
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

interface MapPickerProps {
  label: string;
  lat?: number;
  lng?: number;
  onChange: (lat: number, lng: number) => void;
  onAddressChange?: (address: string) => void;
}

function ClickHandler({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// Recenters the map whenever the position changes externally (search, GPS)
function RecenterMap({ lat, lng }: { lat?: number; lng?: number }) {
  const map = useMap();
  useEffect(() => {
    if (lat && lng) map.setView([lat, lng], map.getZoom());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lat, lng]);
  return null;
}

export default function MapPicker({ label, lat, lng, onChange, onAddressChange }: MapPickerProps) {
  const center: [number, number] = lat && lng ? [lat, lng] : [19.0760, 72.8777]; // Mumbai default

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<GeocodeResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [locating, setLocating] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  const pick = async (newLat: number, newLng: number) => {
    onChange(newLat, newLng);
    if (!onAddressChange) return;
    try {
      const address = await reverseGeocode(newLat, newLng);
      onAddressChange(address);
      setQuery(address);
    } catch {
      // reverse geocoding is best-effort
    }
  };

  const handleSearchChange = (value: string) => {
    setQuery(value);
    setResults([]);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (value.trim().length < 3) return;
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        setResults(await searchPlaces(value));
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 500);
  };

  const selectResult = (r: GeocodeResult) => {
    onChange(r.lat, r.lng);
    onAddressChange?.(r.display_name);
    setQuery(r.display_name);
    setResults([]);
  };

  const useMyLocation = () => {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        pick(coords.latitude, coords.longitude).finally(() => setLocating(false));
      },
      () => setLocating(false),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  return (
    <div>
      {label && <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>}

      <div className="flex gap-2 mb-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search for a location..."
            className="input-field pl-9"
          />
          {searching && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-gray-400" />}
          {results.length > 0 && (
            <ul className="absolute z-[1000] mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
              {results.map((r, i) => (
                <li
                  key={i}
                  onClick={() => selectResult(r)}
                  className="px-3 py-2 text-sm hover:bg-gray-50 cursor-pointer truncate"
                >
                  {r.display_name}
                </li>
              ))}
            </ul>
          )}
        </div>
        <button
          type="button"
          onClick={useMyLocation}
          disabled={locating}
          title="Use my current location"
          className="btn-secondary px-3 shrink-0"
        >
          {locating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Crosshair className="w-4 h-4" />}
        </button>
      </div>

      <p className="text-xs text-gray-400 mb-2">Search, use GPS, click, or drag the pin to set location</p>
      <div className="h-48 rounded-xl overflow-hidden border border-gray-200">
        <MapContainer center={center} zoom={13} style={{ height: '100%', width: '100%' }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <ClickHandler onPick={pick} />
          <RecenterMap lat={lat} lng={lng} />
          {lat && lng && (
            <Marker
              position={[lat, lng]}
              draggable
              eventHandlers={{
                dragend: (e) => {
                  const pos = e.target.getLatLng();
                  pick(pos.lat, pos.lng);
                },
              }}
            />
          )}
        </MapContainer>
      </div>
      {lat && lng && (
        <p className="text-xs text-gray-400 mt-1">
          {lat.toFixed(5)}, {lng.toFixed(5)}
        </p>
      )}
    </div>
  );
}
