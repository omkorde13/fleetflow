import axios from 'axios'

const NOMINATIM_BASE = 'https://nominatim.openstreetmap.org'

export interface GeocodeResult {
  display_name: string
  lat: number
  lng: number
}

export async function searchPlaces(query: string): Promise<GeocodeResult[]> {
  const { data } = await axios.get(`${NOMINATIM_BASE}/search`, {
    params: { q: query, format: 'json', limit: 5 },
  })
  return data.map((item: any) => ({
    display_name: item.display_name,
    lat: parseFloat(item.lat),
    lng: parseFloat(item.lon),
  }))
}

export async function reverseGeocode(lat: number, lng: number): Promise<string> {
  const { data } = await axios.get(`${NOMINATIM_BASE}/reverse`, {
    params: { lat, lon: lng, format: 'json' },
  })
  return data.display_name as string
}
