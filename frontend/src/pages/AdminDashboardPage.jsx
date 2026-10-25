import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldCheck,
  Users,
  Gavel,
  Layers,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Zap,
  TrendingUp,
  RefreshCw,
  Search,
  ExternalLink,
} from 'lucide-react';
import { auctionsApi } from '../api/auctions';
import { usersApi } from '../api/users';
import { categoriesApi } from '../api/categories';
import { StatsCard } from '../components/dashboard/StatsCard';
import { StatusBadge, RoleBadge } from '../components/common/Badge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { SuccessAlert } from '../components/common/SuccessAlert';
import { getErrorMessage } from '../api/client';

export const AdminDashboardPage = () => {
  const [activeTab, setActiveTab] = useState('auctions'); // 'auctions' | 'users' | 'categories' | 'security'
  const [auctions, setAuctions] = useState([]);
  const [users, setUsers] = useState([]);
  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Filters
  const [auctionFilter, setAuctionFilter] = useState('ALL');
  const [userSearch, setUserSearch] = useState('');

  const loadAdminData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [aucRes, usersRes, catRes] = await Promise.all([
        auctionsApi.listAuctions({ status_filter: 'ALL', page_size: 50, sort_by: 'newest' }),
        usersApi.listUsers(1, 50),
        categoriesApi.listCategories(),
      ]);
      setAuctions(aucRes.items || []);
      setUsers(usersRes.items || usersRes || []);
      setCategories(catRes || []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAdminData();
  }, [loadAdminData]);

  // Admin Sweep All Expired Lots
  const handleUniversalSweep = async () => {
    setIsProcessing(true);
    setError(null);
    try {
      const result = await auctionsApi.batchCloseExpired();
      setSuccess(
        `Universal sweep completed: Evaluated ${result.evaluated_count} expired auctions across all sellers. Closed: ${result.closed_count}, Unsold: ${result.unsold_count}.`
      );
      loadAdminData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsProcessing(false);
    }
  };

  // Force close single auction
  const handleForceClose = async (auctionId) => {
    if (!window.confirm(`Administrative Force Close: Close auction #${auctionId} and settle current highest bidder?`)) {
      return;
    }
    setIsProcessing(true);
    setError(null);
    try {
      const res = await auctionsApi.closeAuction(auctionId, true);
      setSuccess(`Auction #${auctionId} force-closed successfully. Status: ${res.status}.`);
      loadAdminData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsProcessing(false);
    }
  };

  // Admin Cancel Auction
  const handleAdminCancel = async (auctionId) => {
    if (!window.confirm(`Administrative Cancel: Cancel auction #${auctionId}?`)) {
      return;
    }
    setIsProcessing(true);
    setError(null);
    try {
      await auctionsApi.cancelAuction(auctionId);
      setSuccess(`Auction #${auctionId} cancelled by administrator.`);
      loadAdminData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsProcessing(false);
    }
  };

  // User Role Update
  const handleRoleChange = async (userId, newRole) => {
    setIsProcessing(true);
    setError(null);
    try {
      await usersApi.updateUserRole(userId, newRole);
      setSuccess(`User #${userId} role updated to ${newRole}.`);
      loadAdminData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsProcessing(false);
    }
  };

  // User Status Toggle (ACTIVE / SUSPENDED)
  const handleStatusToggle = async (userId, currentStatus) => {
    const newStatus = currentStatus === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE';
    setIsProcessing(true);
    setError(null);
    try {
      await usersApi.updateUserStatus(userId, newStatus);
      setSuccess(`User #${userId} status set to ${newStatus}.`);
      loadAdminData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsProcessing(false);
    }
  };

  // Filtered lists
  const filteredAuctions = auctions.filter((a) => {
    if (auctionFilter === 'ALL') return true;
    return a.status === auctionFilter;
  });

  const filteredUsers = users.filter((u) => {
    if (!userSearch) return true;
    const q = userSearch.toLowerCase();
    return (
      u.username?.toLowerCase().includes(q) ||
      u.email?.toLowerCase().includes(q) ||
      u.full_name?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-md bg-rose-100 text-rose-800 text-[11px] font-bold uppercase tracking-wider mb-1">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Administrator Security Clearance</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Admin Governance Center</h1>
          <p className="text-xs text-slate-500">
            System health oversight, cross-seller auction closing, user role promotion, and audit verification.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadAdminData}
            className="p-2 border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-600 transition-colors"
            title="Refresh datasets"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            onClick={handleUniversalSweep}
            disabled={isProcessing}
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold transition-colors shadow-sm disabled:opacity-50"
          >
            <Clock className="w-4 h-4" />
            <span>Universal Expired Sweep</span>
          </button>
        </div>
      </div>

      {success && <SuccessAlert message={success} onClose={() => setSuccess(null)} />}
      {error && <ErrorAlert message={error} onClose={() => setError(null)} />}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Auctions"
          value={auctions.length}
          subtitle={`${auctions.filter((a) => a.status === 'ACTIVE').length} currently active`}
          icon={Gavel}
          color="indigo"
        />
        <StatsCard
          title="Registered Users"
          value={users.length}
          subtitle="Governed accounts"
          icon={Users}
          color="purple"
        />
        <StatsCard
          title="Category Taxonomies"
          value={categories.length}
          subtitle="Curated classifications"
          icon={Layers}
          color="emerald"
        />
        <StatsCard
          title="Platform Concurrency"
          value="Pessimistic"
          subtitle="Zero front-running guarantee"
          icon={Lock}
          color="amber"
        />
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="border-b border-slate-200 flex space-x-6 px-6 pt-4">
          <button
            onClick={() => setActiveTab('auctions')}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'auctions'
                ? 'border-rose-600 text-rose-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Auctions Oversight ({auctions.length})
          </button>

          <button
            onClick={() => setActiveTab('users')}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'users'
                ? 'border-rose-600 text-rose-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            User Governance & RBAC ({users.length})
          </button>

          <button
            onClick={() => setActiveTab('categories')}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'categories'
                ? 'border-rose-600 text-rose-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Category Taxonomies ({categories.length})
          </button>

          <button
            onClick={() => setActiveTab('security')}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'security'
                ? 'border-rose-600 text-rose-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Security & Compliance
          </button>
        </div>

        {/* Tab 1: Auctions Oversight */}
        {activeTab === 'auctions' && (
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-500 font-semibold">Status Filter:</span>
                {['ALL', 'ACTIVE', 'COMPLETED', 'CANCELLED'].map((st) => (
                  <button
                    key={st}
                    onClick={() => setAuctionFilter(st)}
                    className={`px-2.5 py-1 rounded text-xs font-semibold ${
                      auctionFilter === st ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>

            {isLoading ? (
              <LoadingSpinner message="Loading all platform auctions..." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-400 font-bold uppercase border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">ID</th>
                      <th className="py-3 px-4">Lot Title</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Starting</th>
                      <th className="py-3 px-4">Admin Reserve</th>
                      <th className="py-3 px-4">Highest Bid</th>
                      <th className="py-3 px-4">Bids</th>
                      <th className="py-3 px-4 text-right">Admin Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredAuctions.map((auc) => (
                      <tr key={auc.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4 font-mono font-bold text-slate-500">#{auc.id}</td>
                        <td className="py-3 px-4 font-semibold text-slate-900 max-w-xs truncate">
                          <Link to={`/auctions/${auc.id}`} className="hover:text-indigo-600">
                            {auc.product?.title || `Auction #${auc.id}`}
                          </Link>
                        </td>
                        <td className="py-3 px-4">
                          <StatusBadge status={auc.status} />
                        </td>
                        <td className="py-3 px-4 font-mono">${Number(auc.starting_price).toFixed(2)}</td>
                        <td className="py-3 px-4 font-mono text-purple-700 font-bold">
                          {auc.reserve_price !== null ? `$${Number(auc.reserve_price).toFixed(2)}` : 'None'}
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-slate-900">
                          {auc.current_highest_bid !== null ? `$${Number(auc.current_highest_bid).toFixed(2)}` : '—'}
                        </td>
                        <td className="py-3 px-4 font-mono">{auc.total_bids || 0}</td>
                        <td className="py-3 px-4 text-right space-x-2">
                          <Link to={`/auctions/${auc.id}`} className="text-indigo-600 hover:text-indigo-800 font-bold">
                            View
                          </Link>
                          {auc.status === 'ACTIVE' && (
                            <>
                              <button
                                onClick={() => handleForceClose(auc.id)}
                                disabled={isProcessing}
                                className="text-emerald-600 hover:text-emerald-800 font-bold"
                                title="Force close early and settle winner"
                              >
                                Force Close
                              </button>
                              <button
                                onClick={() => handleAdminCancel(auc.id)}
                                disabled={isProcessing}
                                className="text-rose-600 hover:text-rose-800 font-bold"
                                title="Cancel auction"
                              >
                                Cancel
                              </button>
                            </>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: User Governance & RBAC */}
        {activeTab === 'users' && (
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="relative max-w-xs w-full">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Filter users by username or email..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-300"
                />
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-400 font-bold uppercase border-b border-slate-200">
                  <tr>
                    <th className="py-3 px-4">User</th>
                    <th className="py-3 px-4">Email</th>
                    <th className="py-3 px-4">Role</th>
                    <th className="py-3 px-4">Account Status</th>
                    <th className="py-3 px-4">Registered Date</th>
                    <th className="py-3 px-4 text-right">RBAC Governance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredUsers.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-900">{u.username}</div>
                        <div className="text-[11px] text-slate-400">{u.full_name}</div>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-600">{u.email}</td>
                      <td className="py-3 px-4">
                        <RoleBadge role={u.role} />
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold ${
                            u.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                          }`}
                        >
                          {u.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        {/* Role selector */}
                        <select
                          value={u.role}
                          onChange={(e) => handleRoleChange(u.id, e.target.value)}
                          disabled={isProcessing}
                          className="text-[11px] border border-slate-300 rounded px-2 py-1 bg-white font-medium"
                        >
                          <option value="BUYER">BUYER</option>
                          <option value="SELLER">SELLER</option>
                          <option value="ADMIN">ADMIN</option>
                        </select>

                        {/* Status toggle */}
                        <button
                          onClick={() => handleStatusToggle(u.id, u.status)}
                          disabled={isProcessing}
                          className={`text-[11px] font-bold px-2 py-1 rounded transition-colors ${
                            u.status === 'ACTIVE'
                              ? 'text-rose-600 hover:bg-rose-50 border border-rose-200'
                              : 'text-emerald-600 hover:bg-emerald-50 border border-emerald-200'
                          }`}
                        >
                          {u.status === 'ACTIVE' ? 'Suspend' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 3: Categories */}
        {activeTab === 'categories' && (
          <div className="p-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {categories.map((c) => (
                <div key={c.id} className="p-4 rounded-xl border border-slate-200 bg-white">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-sm text-slate-900">{c.name}</span>
                    <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">
                      {c.item_count || 0} items
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mb-2">{c.description || 'General taxonomy classification.'}</p>
                  <span className="text-[10px] font-mono text-slate-400">slug: {c.slug}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 4: Security & Compliance */}
        {activeTab === 'security' && (
          <div className="p-6 space-y-6 text-xs text-slate-700">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <h4 className="text-sm font-bold text-slate-900 flex items-center">
                <Lock className="w-4 h-4 text-indigo-600 mr-2" />
                Pessimistic Concurrency Model
              </h4>
              <p className="text-slate-600 leading-relaxed">
                Atomic bid submissions execute under row-level database locks (`SELECT FOR UPDATE`). Race conditions and concurrent double-highest-bids are structurally impossible.
              </p>
            </div>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <h4 className="text-sm font-bold text-slate-900 flex items-center">
                <Zap className="w-4 h-4 text-amber-500 mr-2" />
                Anti-Sniping Countdown Policy
              </h4>
              <p className="text-slate-600 leading-relaxed">
                If a valid bid is recorded when the auction deadline has fewer than 30 seconds remaining, the database triggers an automatic 60-second deadline extension to give human bidders a fair opportunity to counter.
              </p>
            </div>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <h4 className="text-sm font-bold text-slate-900 flex items-center">
                <ShieldCheck className="w-4 h-4 text-emerald-600 mr-2" />
                Zero-Trust Reserve Masking
              </h4>
              <p className="text-slate-600 leading-relaxed">
                Reserve prices and reserve-met calculations are strictly stripped (`null`) across all public catalog, detail, and outbid notification endpoints unless the caller holds an authenticated ADMIN role or owns the auction listing.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
