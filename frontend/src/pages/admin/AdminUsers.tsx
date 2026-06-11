import { useState, useEffect } from 'react';
import { adminApi } from '../../services/api';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import { Search, Shield, Ban, CheckCircle, User } from 'lucide-react';
import toast from 'react-hot-toast';

const ROLE_BADGE: Record<string, string> = {
  ADMIN: 'badge-blue', CLIENT: 'badge-green', DRIVER: 'badge-yellow',
};

export default function AdminUsers() {
  const [users, setUsers] = useState<any[]>([]);
  const [filtered, setFiltered] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [updating, setUpdating] = useState<string | null>(null);

  useEffect(() => {
    adminApi.listUsers().then(({ data }) => { setUsers(data.users); setFiltered(data.users); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const q = search.toLowerCase();
    setFiltered(
      q ? users.filter((u) =>
        u.full_name.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        u.role.toLowerCase().includes(q)
      ) : users
    );
  }, [search, users]);

  const toggleActive = async (user: any) => {
    setUpdating(user.id);
    try {
      await adminApi.updateUserStatus(user.id, !user.is_active);
      setUsers((prev) => prev.map((u) => u.id === user.id ? { ...u, is_active: !user.is_active } : u));
      toast.success(`User ${user.is_active ? 'deactivated' : 'activated'}`);
    } catch {
      toast.error('Failed to update user');
    } finally {
      setUpdating(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Users</h1>
        <span className="text-sm text-gray-500">{users.length} total</span>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input placeholder="Search name, email, role..."
          value={search} onChange={(e) => setSearch(e.target.value)}
          className="input-field pl-9" />
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><LoadingSpinner /></div>
      ) : (
        <div className="card p-0 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">User</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Role</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
                <th className="text-left px-4 py-3 text-gray-600 font-medium">Joined</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center shrink-0">
                        {user.avatar_url
                          ? <img src={user.avatar_url} className="w-8 h-8 rounded-full object-cover" />
                          : <User className="w-4 h-4 text-gray-400" />}
                      </div>
                      <div>
                        <p className="font-medium text-gray-800">{user.full_name}</p>
                        <p className="text-xs text-gray-400">{user.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={ROLE_BADGE[user.role] ?? 'badge-gray'}>{user.role}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={user.is_active ? 'badge-green' : 'badge-red'}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(user.created_at).toLocaleDateString('en-IN')}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleActive(user)}
                      disabled={updating === user.id || user.role === 'ADMIN'}
                      className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-40"
                      title={user.is_active ? 'Deactivate' : 'Activate'}
                    >
                      {user.is_active
                        ? <Ban className="w-4 h-4 text-red-400" />
                        : <CheckCircle className="w-4 h-4 text-green-500" />}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <p className="text-center text-gray-400 py-8">No users found</p>
          )}
        </div>
      )}
    </div>
  );
}
