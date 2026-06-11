import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Loader2, Truck } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuthStore } from '../../context/authStore';

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    full_name: '', email: '', phone: '', password: '', confirm_password: '', role: 'CLIENT',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password !== form.confirm_password) {
      toast.error('Passwords do not match');
      return;
    }
    setLoading(true);
    try {
      await register({
        full_name: form.full_name,
        email: form.email,
        phone: form.phone,
        password: form.password,
        role: form.role,
      });
      toast.success('Account created! Please login.');
      navigate('/login');
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-8">
        {/* Logo */}
        <div className="flex items-center gap-2 justify-center mb-6">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
            <Truck className="w-6 h-6 text-white" />
          </div>
          <span className="text-2xl font-bold text-gray-900">FleetFlow</span>
        </div>
        <h2 className="text-center text-gray-500 text-sm mb-8">Create your account</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
            <input name="full_name" type="text" required value={form.full_name}
              onChange={handleChange} className="input-field" placeholder="John Doe" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input name="email" type="email" required value={form.email}
              onChange={handleChange} className="input-field" placeholder="john@example.com" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
            <input name="phone" type="tel" value={form.phone}
              onChange={handleChange} className="input-field" placeholder="+91 98765 43210" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">I am a</label>
            <select name="role" value={form.role} onChange={handleChange} className="input-field">
              <option value="CLIENT">Customer</option>
              <option value="DRIVER">Driver / Delivery Partner</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input name="password" type="password" required minLength={8} value={form.password}
              onChange={handleChange} className="input-field" placeholder="Min 8 characters" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
            <input name="confirm_password" type="password" required value={form.confirm_password}
              onChange={handleChange} className="input-field" placeholder="Repeat password" />
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full mt-2 flex items-center justify-center gap-2">
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 hover:underline font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
