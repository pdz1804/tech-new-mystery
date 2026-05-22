'use client';

import { useState, useEffect } from 'react';
import { useAuthStore } from '@/lib/stores/authStore';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api/client';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { AppLoadingState } from '@/components/ui/AppLoadingState';
import { Shield, Loader2, Users } from 'lucide-react';

interface User {
  user_id: string;
  username: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string | number;
}

function formatCreatedAt(value: string | number) {
  const raw = String(value || '').trim();
  if (!raw) return '-';

  const numeric = Number(raw);
  const date = Number.isFinite(numeric)
    ? new Date(numeric < 10_000_000_000 ? numeric * 1000 : numeric)
    : new Date(raw);

  if (Number.isNaN(date.getTime())) return '-';

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date);
}

export default function AdminUsersPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const isHydrated = useAuthStore((s) => s.isHydrated);

  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggleLoading, setToggleLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Protect route - redirect if not admin
    if (isHydrated && !user?.is_admin) {
      router.push('/');
      return;
    }
  }, [isHydrated, user?.is_admin, router]);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoading(true);
        setError(null);

        const { data: response } = await apiClient.get('/admin/users');

        if (response.success) {
          setUsers(response.data);
        } else {
          setError('Failed to load users');
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(message);
        console.error('Error fetching users:', err);
      } finally {
        setLoading(false);
      }
    };

    if (isHydrated) {
      fetchUsers();
    }
  }, [isHydrated]);

  const toggleAdminStatus = async (userId: string, currentStatus: boolean) => {
    try {
      setToggleLoading(userId);
      const { data } = await apiClient.put(`/admin/users/${userId}/toggle-admin`);

      if (data.success) {
        setUsers(
          users.map((u) =>
            u.user_id === userId ? { ...u, is_admin: !currentStatus } : u
          )
        );
      } else {
        setError('Failed to update user');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      console.error('Error toggling admin:', err);
    } finally {
      setToggleLoading(null);
    }
  };

  if (!isHydrated) {
    return <AppLoadingState variant="profile" />;
  }

  const adminCount = users.filter((u) => u.is_admin).length;
  const activeCount = users.filter((u) => u.is_active).length;

  return (
    <main className="search-stage app-page-shell min-h-screen" id="main-content">
      <div className="app-page-container">
        <section className="app-hero-panel mb-8 p-5 sm:p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <span className="text-label mb-3 block text-blue-600">Admin</span>
              <h1 className="font-sans text-3xl font-bold text-black sm:text-4xl">User Management</h1>
              <p className="mt-2 text-sm text-black/60">
                View users and grant or revoke admin access.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="rounded-xl border border-black/10 bg-white/55 px-4 py-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.85)] backdrop-blur-xl">
                <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-black/45">Users</p>
                <p className="text-lg font-bold text-black">{users.length}</p>
              </div>
              <div className="rounded-xl border border-black/10 bg-white/55 px-4 py-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.85)] backdrop-blur-xl">
                <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-black/45">Admins</p>
                <p className="text-lg font-bold text-black">{adminCount}</p>
              </div>
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-[0_12px_30px_rgba(37,99,235,0.28)]">
                <Users size={22} aria-hidden="true" />
              </div>
            </div>
          </div>
        </section>

        {/* Error Message */}
        {error && (
          <div className="glass-panel mb-6 border-red-200 bg-red-50/80 p-4 text-red-700">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="glass-panel p-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-3 w-48" />
                  </div>
                  <Skeleton className="h-8 w-20" />
                </div>
              </div>
            ))}
          </div>
        ) : users.length === 0 ? (
          <div className="apple-empty-state p-8 text-center">
            <p className="text-black/60">No users found</p>
          </div>
        ) : (
          <div className="glass-panel overflow-hidden p-0">
            <div className="flex items-center justify-between border-b border-black/10 px-6 py-4">
              <p className="text-sm font-semibold text-black">
                {activeCount} active user{activeCount === 1 ? '' : 's'}
              </p>
              <p className="text-xs font-medium text-black/45">
                Role changes apply immediately
              </p>
            </div>
            <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-black/10 bg-white/30">
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.12em] text-black/55">
                    Username
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.12em] text-black/55">
                    Email
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.12em] text-black/55">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.12em] text-black/55">
                    Admin
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.12em] text-black/55">
                    Created
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-bold uppercase tracking-[0.12em] text-black/55">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr
                    key={u.user_id}
                    className="border-b border-black/8 transition-colors last:border-b-0 hover:bg-white/35"
                  >
                    <td className="px-6 py-4">
                      <span className="font-semibold text-black">{u.username}</span>
                    </td>
                    <td className="px-6 py-4 text-sm text-black/60">{u.email || '-'}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${
                          u.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {u.is_admin ? (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800">
                          <Shield className="h-3 w-3" />
                          Admin
                        </span>
                      ) : (
                        <span className="text-sm text-black/35">Member</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-black/60">
                      {formatCreatedAt(u.created_at)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Button
                        onClick={() => toggleAdminStatus(u.user_id, u.is_admin)}
                        disabled={toggleLoading === u.user_id}
                        className={`rounded-xl px-4 py-2 text-xs font-bold shadow-[0_10px_22px_rgba(0,0,0,0.10)] ${
                          u.is_admin
                            ? 'bg-red-600 hover:bg-red-700'
                            : 'bg-blue-600 hover:bg-blue-700'
                        }`}
                      >
                        {toggleLoading === u.user_id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : u.is_admin ? (
                          'Revoke Admin'
                        ) : (
                          'Make Admin'
                        )}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
