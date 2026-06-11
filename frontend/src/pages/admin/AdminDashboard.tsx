import { useEffect, useState } from 'react'
import { adminApi } from '@/services/api'
import { useFleetMonitor } from '@/hooks/useWebSocket'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line
} from 'recharts'
import {
  Users, Truck, Package, CheckCircle, DollarSign,
  TrendingUp, Activity, AlertCircle
} from 'lucide-react'
import toast from 'react-hot-toast'

interface Metrics {
  total_users: number
  total_drivers: number
  active_drivers: number
  active_deliveries: number
  completed_deliveries: number
  total_revenue: number
  today_revenue: number
  today_deliveries: number
}

const MetricCard = ({
  icon: Icon, label, value, sub, color
}: {
  icon: any, label: string, value: string | number, sub?: string, color: string
}) => (
  <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
    <div className="flex items-center justify-between mb-4">
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <div className={`w-10 h-10 ${color} rounded-lg flex items-center justify-center`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
    </div>
    <p className="text-2xl font-bold text-gray-900">{value}</p>
    {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
  </div>
)

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [revenueData, setRevenueData] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [liveEvents, setLiveEvents] = useState<any[]>([])

  // Real-time fleet events
  const { lastEvent: fleetEvent } = useFleetMonitor()
  useEffect(() => {
    if (!fleetEvent) return
    setLiveEvents(prev => [
      { ...fleetEvent, time: new Date().toLocaleTimeString() },
      ...prev.slice(0, 9)
    ])
  }, [fleetEvent])

  useEffect(() => {
    const load = async () => {
      try {
        const [dashRes, revenueRes] = await Promise.all([
          adminApi.dashboard(),
          adminApi.revenueReport('daily'),
        ])
        setMetrics(dashRes.data.metrics)
        setRevenueData(revenueRes.data.data.slice(0, 14).reverse())
      } catch {
        toast.error('Failed to load dashboard')
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
          <p className="text-gray-500 text-sm">Real-time fleet analytics and monitoring</p>
        </div>
        <div className="flex items-center gap-2 bg-green-50 text-green-700 px-3 py-1.5 rounded-full text-sm font-medium">
          <Activity className="w-3.5 h-3.5" />
          Live
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard icon={Users} label="Total Users" value={metrics?.total_users || 0} color="bg-blue-500" />
        <MetricCard icon={Truck} label="Active Drivers" value={`${metrics?.active_drivers || 0} / ${metrics?.total_drivers || 0}`} color="bg-emerald-500" />
        <MetricCard icon={Package} label="Active Deliveries" value={metrics?.active_deliveries || 0} sub={`${metrics?.today_deliveries || 0} today`} color="bg-orange-500" />
        <MetricCard icon={DollarSign} label="Today's Revenue" value={`₹${(metrics?.today_revenue || 0).toLocaleString()}`} sub={`₹${(metrics?.total_revenue || 0).toLocaleString()} total`} color="bg-purple-500" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Revenue Chart */}
        <div className="xl:col-span-2 bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Revenue (Last 14 Days)</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={revenueData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip
                cursor={false}
                formatter={(value: number) => [`₹${value.toFixed(2)}`, 'Revenue']}
              />
              <Bar dataKey="revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Live Events Feed */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            Live Events
          </h2>
          <div className="space-y-2 overflow-y-auto max-h-56">
            {liveEvents.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-8">Waiting for events...</p>
            ) : (
              liveEvents.map((event, i) => (
                <div key={i} className="flex items-start gap-2 text-xs p-2 bg-gray-50 rounded-lg">
                  <span className="text-gray-400 whitespace-nowrap">{event.time}</span>
                  <span className="text-gray-700">
                    {event.type === 'location_update'
                      ? `Driver ${event.driver_id?.slice(0, 8)} updated location`
                      : event.type
                    }
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span className="text-sm font-medium text-gray-700">Completed Deliveries</span>
          </div>
          <p className="text-3xl font-bold text-gray-900">{metrics?.completed_deliveries?.toLocaleString() || 0}</p>
        </div>
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-blue-500" />
            <span className="text-sm font-medium text-gray-700">Total Revenue</span>
          </div>
          <p className="text-3xl font-bold text-gray-900">₹{(metrics?.total_revenue || 0).toLocaleString()}</p>
        </div>
      </div>
    </div>
  )
}
