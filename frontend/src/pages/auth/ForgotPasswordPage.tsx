import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, Truck, ArrowLeft, CheckCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { authApi } from '../../services/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await authApi.forgotPassword(email);
      setSent(true);
    } catch {
      toast.error('Something went wrong. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-8">
        <div className="flex items-center gap-2 justify-center mb-6">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
            <Truck className="w-6 h-6 text-white" />
          </div>
          <span className="text-2xl font-bold text-gray-900">FleetFlow</span>
        </div>

        {sent ? (
          <div className="text-center py-6">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Check your email</h3>
            <p className="text-sm text-gray-500 mb-6">
              We sent a password reset link to <strong>{email}</strong>.
              Check your inbox and spam folder.
            </p>
            <Link to="/login" className="btn-primary inline-flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" /> Back to Login
            </Link>
          </div>
        ) : (
          <>
            <h2 className="text-xl font-bold text-gray-800 mb-1">Forgot Password</h2>
            <p className="text-sm text-gray-500 mb-6">
              Enter your email and we'll send a reset link.
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                  className="input-field" placeholder="you@example.com" />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                {loading ? 'Sending...' : 'Send Reset Link'}
              </button>
            </form>
            <p className="text-center text-sm text-gray-500 mt-6">
              <Link to="/login" className="text-blue-600 hover:underline inline-flex items-center gap-1">
                <ArrowLeft className="w-3 h-3" /> Back to Login
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
