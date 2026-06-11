import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '../../context/authStore';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import toast from 'react-hot-toast';

export default function OAuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { setUser } = useAuthStore();

  useEffect(() => {
    const token = params.get('access_token');
    const refresh = params.get('refresh_token');
    const error = params.get('error');

    if (error) {
      toast.error('Google login failed. Please try again.');
      navigate('/login');
      return;
    }

    if (token && refresh) {
      localStorage.setItem('access_token', token);
      localStorage.setItem('refresh_token', refresh);
      // Fetch user profile
      fetch('/api/v1/users/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => r.json())
        .then((user) => {
          setUser(user);
          const role = user.role as string;
          if (role === 'ADMIN') navigate('/admin');
          else if (role === 'DRIVER') navigate('/driver/dashboard');
          else navigate('/dashboard');
        })
        .catch(() => {
          toast.error('Login error. Please try again.');
          navigate('/login');
        });
    } else {
      navigate('/login');
    }
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <LoadingSpinner size="lg" text="Completing sign-in..." />
    </div>
  );
}
