import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'

// Auth Pages
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import OAuthCallbackPage from '@/pages/auth/OAuthCallbackPage'
import ForgotPasswordPage from '@/pages/auth/ForgotPasswordPage'
import ResetPasswordPage from '@/pages/auth/ResetPasswordPage'

// Client Pages
import ClientDashboard from '@/pages/client/ClientDashboard'
import CreateDeliveryPage from '@/pages/client/CreateDeliveryPage'
import TrackDeliveryPage from '@/pages/client/TrackDeliveryPage'
import DeliveryHistoryPage from '@/pages/client/DeliveryHistoryPage'
import PaymentPage from '@/pages/client/PaymentPage'
import OffersPage from '@/pages/client/OffersPage'

// Driver Pages
import DriverDashboard from '@/pages/driver/DriverDashboard'
import DriverDeliveryPage from '@/pages/driver/DriverDeliveryPage'
import DriverProfilePage from '@/pages/driver/DriverProfilePage'

// Admin Pages
import AdminDashboard from '@/pages/admin/AdminDashboard'
import AdminUsers from '@/pages/admin/AdminUsers'
import AdminDrivers from '@/pages/admin/AdminDrivers'
import AdminDeliveries from '@/pages/admin/AdminDeliveries'
import AdminOffers from '@/pages/admin/AdminOffers'
import AdminFleetMap from '@/pages/admin/AdminFleetMap'

// Layout
import ProtectedRoute from '@/components/common/ProtectedRoute'
import AppLayout from '@/components/common/AppLayout'

function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: { fontFamily: 'Inter, sans-serif' },
        }}
      />
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/auth/callback" element={<OAuthCallbackPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

        {/* Client Routes */}
        <Route element={<ProtectedRoute allowedRoles={['CLIENT']} />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<ClientDashboard />} />
            <Route path="/create-delivery" element={<CreateDeliveryPage />} />
            <Route path="/track/:deliveryId" element={<TrackDeliveryPage />} />
            <Route path="/deliveries" element={<DeliveryHistoryPage />} />
            <Route path="/payment/:deliveryId" element={<PaymentPage />} />
            <Route path="/offers" element={<OffersPage />} />
          </Route>
        </Route>

        {/* Driver Routes */}
        <Route element={<ProtectedRoute allowedRoles={['DRIVER']} />}>
          <Route element={<AppLayout />}>
            <Route path="/driver/dashboard" element={<DriverDashboard />} />
            <Route path="/driver/delivery/:id" element={<DriverDeliveryPage />} />
            <Route path="/driver/profile" element={<DriverProfilePage />} />
          </Route>
        </Route>

        {/* Admin Routes */}
        <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
          <Route element={<AppLayout />}>
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/users" element={<AdminUsers />} />
            <Route path="/admin/drivers" element={<AdminDrivers />} />
            <Route path="/admin/deliveries" element={<AdminDeliveries />} />
            <Route path="/admin/offers" element={<AdminOffers />} />
            <Route path="/admin/fleet" element={<AdminFleetMap />} />
          </Route>
        </Route>

        {/* Redirect root */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
