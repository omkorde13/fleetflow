import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2, Truck, ArrowLeft, CheckCircle, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import { authApi } from '../../services/api';

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get('token');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    if (password !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    if (!token) return;

    setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      setDone(true);
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Failed to reset password');
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

        {!token ? (
          <div className="text-center py-6">
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Invalid reset link</h3>
            <p className="text-sm text-gray-500 mb-6">
              This password reset link is missing or invalid. Please request a new one.
            </p>
            <Link to="/forgot-password" className="btn-primary inline-flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" /> Request new link
            </Link>
          </div>
        ) : done ? (
          <div className="text-center py-6">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Password reset</h3>
            <p className="text-sm text-gray-500 mb-6">
              Your password has been updated. You can now sign in with your new password.
            </p>
            <button onClick={() => navigate('/login')} className="btn-primary inline-flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" /> Back to Login
            </button>
          </div>
        ) : (
          <>
            <h2 className="text-xl font-bold text-gray-800 mb-1">Reset Password</h2>
            <p className="text-sm text-gray-500 mb-6">
              Enter a new password for your account.
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
                <input type="password" required minLength={8} value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field" placeholder="••••••••" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
                <input type="password" required minLength={8} value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="input-field" placeholder="••••••••" />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                {loading ? 'Resetting...' : 'Reset Password'}
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
