import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Gavel,
  Trophy,
  Heart,
  Clock,
  Bell,
  ArrowRight,
  TrendingUp,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { bidsApi } from '../api/bids';
import { auctionsApi } from '../api/auctions';
import { useAuth } from '../context/AuthContext';
import { useWatchlist } from '../context/WatchlistContext';
import { useNotifications } from '../context/NotificationContext';
import { StatsCard } from '../components/dashboard/StatsCard';
import { ActivityChart } from '../components/dashboard/ActivityChart';
import { StatusBadge } from '../components/common/Badge';
import { CountdownTimer } from '../components/common/CountdownTimer';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { EmptyState } from '../components/common/EmptyState';

export const BuyerDashboardPage = () => {
  const { user } = useAuth();
  const { watchlistIds, removeFromWatchlist } = useWatchlist();
  const { notifications } = useNotifications();

  const [activeTab, setActiveTab] = useState('bids'); // 'bids' | 'watchlist' | 'alerts'
  const [bids, setBids] = useState([]);
  const [watchlistAuctions, setWatchlistAuctions] = useState([]);
  const [isLoadingBids, setIsLoadingBids] = useState(true);
  const [isLoadingWatchlist, setIsLoadingWatchlist] = useState(false);

  // Load user's bid activity
  useEffect(() => {
    let isMounted = true;
    const fetchBids = async () => {
      setIsLoadingBids(true);
      try {
        const data = await bidsApi.listMyBids(0, 50);
        if (isMounted) setBids(data || []);
      } catch (err) {
        console.error('Failed to load user bids:', err);
      } finally {
        if (isMounted) setIsLoadingBids(false);
      }
    };
    fetchBids();
    return () => {
      isMounted = false;
    };
  }, []);

  // Load details for watchlisted items
  useEffect(() => {
    let isMounted = true;
    let refreshTimer;
    const fetchWatchlistItems = async (showLoading = false) => {
      if (watchlistIds.length === 0) {
        setWatchlistAuctions([]);
        return;
      }
      if (showLoading) setIsLoadingWatchlist(true);
      try {
        const promises = watchlistIds.map((id) =>
          auctionsApi.getAuction(id).catch(() => null)
        );
        const results = await Promise.all(promises);
        if (isMounted) {
          setWatchlistAuctions(results.filter(Boolean));
        }
      } catch (err) {
        console.error('Failed to load watchlist details:', err);
      } finally {
        if (isMounted && showLoading) setIsLoadingWatchlist(false);
      }
    };

    if (activeTab === 'watchlist') {
      fetchWatchlistItems(true);
      refreshTimer = setInterval(() => fetchWatchlistItems(), 30000);
    }
    return () => {
      isMounted = false;
      clearInterval(refreshTimer);
    };
  }, [watchlistIds, activeTab]);

  // Compute metrics
  const totalBidsCount = bids.length;
  const winningBidsCount = bids.filter((b) => b.is_winning_bid && b.auction_status === 'ACTIVE').length;
  const wonAuctionsCount = bids.filter((b) => b.is_winning_bid && b.auction_status === 'COMPLETED').length;

  // Build chart data: aggregate bids by date
  const chartDataMap = {};
  bids.forEach((b) => {
    const dateStr = new Date(b.bid_time).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    chartDataMap[dateStr] = (chartDataMap[dateStr] || 0) + 1;
  });
  const chartData = Object.keys(chartDataMap).map((k) => ({
    name: k,
    bids: chartDataMap[k],
  }));

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Buyer Hub</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Welcome back, <span className="font-semibold text-slate-800">{user?.full_name || user?.username}</span>. Monitor your active bids, saved watchlists, and settlement updates.
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Bids Placed"
          value={totalBidsCount}
          subtitle="Lifetime submissions"
          icon={Gavel}
          color="indigo"
        />
        <StatsCard
          title="Active High Bids"
          value={winningBidsCount}
          subtitle="Currently leading active lots"
          icon={TrendingUp}
          color="emerald"
        />
        <StatsCard
          title="Auctions Won"
          value={wonAuctionsCount}
          subtitle="Completed winning settlements"
          icon={Trophy}
          color="purple"
        />
        <StatsCard
          title="Watchlist Items"
          value={watchlistIds.length}
          subtitle="Saved for monitoring"
          icon={Heart}
          color="amber"
        />
      </div>

      {/* Optional Activity Trend Chart if user has bids */}
      {chartData.length > 0 && (
        <ActivityChart
          data={chartData}
          type="line"
          dataKey="bids"
          xKey="name"
          title="Recent Bidding Momentum"
        />
      )}

      {/* Tabs & Content */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Tab Navigation */}
        <div className="border-b border-slate-200 flex space-x-6 px-6 pt-4">
          <button
            onClick={() => setActiveTab('bids')}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'bids'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            My Bidding Activity ({bids.length})
          </button>

          <button
            onClick={() => setActiveTab('watchlist')}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'watchlist'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Saved Watchlist ({watchlistIds.length})
          </button>

          <button
            onClick={() => setActiveTab('alerts')}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'alerts'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Notification Alerts ({notifications.length})
          </button>
        </div>

        {/* Tab 1: Bidding Activity */}
        {activeTab === 'bids' && (
          <div className="p-6">
            {isLoadingBids ? (
              <LoadingSpinner message="Loading your bids..." />
            ) : bids.length === 0 ? (
              <EmptyState
                icon={Gavel}
                title="No bids placed yet"
                description="Explore active auctions in the catalog and place your first atomic bid."
                action={
                  <Link
                    to="/catalog"
                    className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-bold hover:bg-indigo-700 transition-colors"
                  >
                    <span>Browse Catalog</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-1" />
                  </Link>
                }
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-400 font-bold uppercase border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">Item Title</th>
                      <th className="py-3 px-4">Your Bid</th>
                      <th className="py-3 px-4">Highest Bid</th>
                      <th className="py-3 px-4">Auction Status</th>
                      <th className="py-3 px-4">Time Placed</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {bids.map((b) => (
                      <tr key={b.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-3 px-4 font-semibold text-slate-900 max-w-xs truncate">
                          {b.product_title}
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-slate-900">
                          ${Number(b.bid_amount).toFixed(2)}
                          {b.is_winning_bid && (
                            <span className="ml-2 inline-flex items-center text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.2 rounded font-sans font-bold">
                              Leading
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-600">
                          {b.current_highest_bid !== null ? `$${Number(b.current_highest_bid).toFixed(2)}` : '—'}
                        </td>
                        <td className="py-3 px-4">
                          <StatusBadge status={b.auction_status} />
                        </td>
                        <td className="py-3 px-4 text-slate-400">
                          {new Date(b.bid_time).toLocaleDateString(undefined, {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <Link
                            to={`/auctions/${b.auction_id}`}
                            className="inline-flex items-center text-indigo-600 hover:text-indigo-800 font-bold"
                          >
                            <span>View</span>
                            <ExternalLink className="w-3 h-3 ml-1" />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Watchlist */}
        {activeTab === 'watchlist' && (
          <div className="p-6">
            <div className="mb-4 text-xs text-slate-500 bg-slate-50 p-3 rounded-lg border border-slate-200 flex items-center justify-between">
              <span>Saved Watchlist (Synchronized locally for current buyer session)</span>
              <span className="text-[11px] font-mono text-slate-400">Items: {watchlistIds.length}</span>
            </div>

            {isLoadingWatchlist ? (
              <LoadingSpinner message="Loading saved watchlists..." />
            ) : watchlistAuctions.length === 0 ? (
              <EmptyState
                icon={Heart}
                title="Your watchlist is empty"
                description="Click the heart icon on any auction card to bookmark lots and track their countdown."
                action={
                  <Link
                    to="/catalog"
                    className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-bold hover:bg-indigo-700 transition-colors"
                  >
                    <span>Discover Lots</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-1" />
                  </Link>
                }
              />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {watchlistAuctions.map((auc) => (
                  <div
                    key={auc.id}
                    className="p-4 rounded-xl border border-slate-200 bg-white flex flex-col justify-between space-y-3"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <StatusBadge status={auc.status} />
                        <Link
                          to={`/auctions/${auc.id}`}
                          className="font-bold text-sm text-slate-900 hover:text-indigo-600 transition-colors line-clamp-1 mt-1 block"
                        >
                          {auc.product?.title || `Auction #${auc.id}`}
                        </Link>
                      </div>
                      <button
                        onClick={() => removeFromWatchlist(auc.id)}
                        className="p-1 text-slate-400 hover:text-rose-600 transition-colors"
                        title="Remove from watchlist"
                      >
                        <Heart className="w-4 h-4 fill-rose-500 text-rose-500" />
                      </button>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase font-bold block">Current Bid</span>
                        <span className="font-mono font-bold text-slate-900">
                          ${Number(auc.current_highest_bid || auc.starting_price).toFixed(2)}
                        </span>
                      </div>
                      <div className="text-right">
                        <CountdownTimer
                          endTime={auc.status === 'SCHEDULED' ? auc.start_time : auc.end_time}
                          compact
                          expiredLabel={auc.status === 'SCHEDULED' ? 'Auction Starting' : 'Auction Ended'}
                        />
                      </div>
                    </div>

                    <Link
                      to={`/auctions/${auc.id}`}
                      className="w-full text-center py-2 px-3 bg-slate-100 hover:bg-indigo-600 hover:text-white rounded-lg text-xs font-bold text-slate-700 transition-colors"
                    >
                      View & Bid
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Alerts */}
        {activeTab === 'alerts' && (
          <div className="p-6">
            {notifications.length === 0 ? (
              <EmptyState
                icon={Bell}
                title="No notification alerts"
                description="You'll receive alerts when you are outbid or win an auction lot."
              />
            ) : (
              <div className="space-y-3">
                {notifications.slice(0, 10).map((n) => (
                  <div
                    key={n.id}
                    className={`p-4 rounded-xl border text-xs flex items-start justify-between ${
                      n.is_read ? 'bg-white border-slate-200' : 'bg-indigo-50/50 border-indigo-200'
                    }`}
                  >
                    <div>
                      <div className="font-bold text-slate-900 mb-0.5">{n.title}</div>
                      <p className="text-slate-600">{n.message}</p>
                      <span className="text-[10px] text-slate-400 mt-1 block">
                        {new Date(n.created_at).toLocaleString()}
                      </span>
                    </div>

                    {n.link_url && (
                      <Link
                        to={n.link_url}
                        className="ml-4 px-3 py-1 bg-white border border-slate-200 rounded text-[11px] font-bold text-indigo-600 hover:bg-slate-50 transition-colors flex-shrink-0"
                      >
                        View Lot
                      </Link>
                    )}
                  </div>
                ))}
                <div className="text-center pt-2">
                  <Link
                    to="/notifications"
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                  >
                    View All Notifications & Inbox →
                  </Link>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
