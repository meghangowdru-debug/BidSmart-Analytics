import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  BarChart3,
  Boxes,
  CircleDollarSign,
  Gavel,
  ShoppingBag,
  Users,
} from 'lucide-react';
import { analyticsApi } from '../api/analytics';
import { categoriesApi } from '../api/categories';
import { getErrorMessage } from '../api/client';
import { StatsCard } from '../components/dashboard/StatsCard';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

const STATUS_COLORS = ['#4f46e5', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#64748b', '#06b6d4'];

const utcDateInputValue = (date) => date.toISOString().slice(0, 10);

const currency = (amount) => new Intl.NumberFormat(undefined, {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 2,
}).format(Number(amount || 0));

const countFormat = (value) => new Intl.NumberFormat().format(Number(value || 0));

const localDateLabel = (utcDate) => {
  if (!utcDate) return '';
  const [year, month, day] = utcDate.split('-').map(Number);
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' })
    .format(new Date(Date.UTC(year, month - 1, day)));
};

const formatStatus = (value) => (value || 'No auction').replaceAll('_', ' ').toLowerCase()
  .replace(/\b\w/g, (character) => character.toUpperCase());

const chartCard = 'bg-white rounded-xl border border-slate-200 p-5 shadow-sm';
const tooltipStyle = {
  backgroundColor: '#0f172a',
  border: 0,
  borderRadius: '8px',
  color: '#fff',
  fontSize: '12px',
};
const EMPTY_RANKINGS = [];
const ANALYTICS_REFRESH_INTERVAL_MS = 12000;

export const AnalyticsPage = () => {
  const [categories, setCategories] = useState([]);
  const [startDate, setStartDate] = useState(() => {
    const start = new Date();
    start.setUTCDate(start.getUTCDate() - 29);
    return utcDateInputValue(start);
  });
  const [endDate, setEndDate] = useState(() => utcDateInputValue(new Date()));
  const [categoryId, setCategoryId] = useState('');
  const [trendMode, setTrendMode] = useState('daily');
  const [tableMode, setTableMode] = useState('auctions');
  const [sortBy, setSortBy] = useState('valid_bids');
  const [sortDirection, setSortDirection] = useState('desc');
  const [requestState, setRequestState] = useState(null);
  const [categoryError, setCategoryError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const requestInFlightRef = useRef(false);
  const queuedRefreshRef = useRef(false);
  const mountedRef = useRef(true);
  const filterKeyRef = useRef(null);
  const analyticsRequestRef = useRef(null);
  const filterKey = `${startDate}|${endDate}|${categoryId}`;
  const dateRangeError = !startDate || !endDate || startDate > endDate
    ? 'Choose a valid date range. The end date must be on or after the start date.'
    : null;
  const requestAnalytics = useCallback(async (queueIfBusy = false) => {
    if (dateRangeError) return;
    if (requestInFlightRef.current) {
      if (queueIfBusy) queuedRefreshRef.current = true;
      return;
    }

    requestInFlightRef.current = true;
    const requestKey = filterKey;
    const filters = {
      start_date: startDate,
      end_date: endDate,
      ...(categoryId ? { category_id: Number(categoryId) } : {}),
    };
    try {
      const result = await analyticsApi.getAnalytics(filters);
      if (mountedRef.current && filterKeyRef.current === requestKey) {
        setRequestState({ key: requestKey, data: result, error: null });
        setLastUpdated(new Date());
      }
    } catch (requestError) {
      if (mountedRef.current && filterKeyRef.current === requestKey) {
        setRequestState((current) => ({
          key: requestKey,
          data: current?.key === requestKey ? current.data : null,
          error: getErrorMessage(requestError),
        }));
      }
    } finally {
      requestInFlightRef.current = false;
      if (queuedRefreshRef.current) {
        queuedRefreshRef.current = false;
        if (mountedRef.current && !document.hidden) {
          window.setTimeout(() => analyticsRequestRef.current?.(), 0);
        }
      }
    }
  }, [categoryId, dateRangeError, endDate, filterKey, startDate]);

  useEffect(() => {
    let mounted = true;
    categoriesApi.listCategories()
      .then((rows) => {
        if (mounted) setCategories(rows || []);
      })
      .catch((requestError) => {
        if (mounted) setCategoryError(getErrorMessage(requestError));
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    filterKeyRef.current = filterKey;
    analyticsRequestRef.current = requestAnalytics;
  }, [filterKey, requestAnalytics]);

  useEffect(() => {
    if (dateRangeError) return undefined;

    const refreshIfVisible = (queueIfBusy = false) => {
      if (!document.hidden) requestAnalytics(queueIfBusy);
    };
    const handleVisibilityChange = () => {
      if (!document.hidden) refreshIfVisible(true);
    };
    const handleFocus = () => refreshIfVisible(true);

    refreshIfVisible(true);
    const intervalId = window.setInterval(
      () => refreshIfVisible(false),
      ANALYTICS_REFRESH_INTERVAL_MS,
    );
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleFocus);

    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleFocus);
    };
  }, [dateRangeError, requestAnalytics]);

  const currentRequest = requestState?.key === filterKey ? requestState : null;
  const visibleData = dateRangeError ? null : currentRequest?.data;
  const isLoading = !dateRangeError && !currentRequest;
  const error = dateRangeError || currentRequest?.error;
  const kpis = visibleData?.kpis;
  const settlementMetricsAvailable = visibleData?.settlement_metrics_available !== false;
  const rankings = tableMode === 'products'
    ? visibleData?.product_rankings || EMPTY_RANKINGS
    : visibleData?.auction_rankings || EMPTY_RANKINGS;
  const trendData = trendMode === 'monthly'
    ? visibleData?.monthly_trends || EMPTY_RANKINGS
    : visibleData?.daily_trends || EMPTY_RANKINGS;
  const sortedRankings = useMemo(() => [...rankings].sort((left, right) => {
    const a = left[sortBy];
    const b = right[sortBy];
    const result = typeof a === 'string'
      ? String(a || '').localeCompare(String(b || ''))
      : Number(a || 0) - Number(b || 0);
    return sortDirection === 'asc' ? result : -result;
  }), [rankings, sortBy, sortDirection]);

  const cards = useMemo(() => {
    if (!kpis) return [];
    if (visibleData.scope === 'admin') {
      return [
        ['Registered users', countFormat(kpis.registered_users), `Selected period · ${countFormat(kpis.buyers)} buyers · ${countFormat(kpis.sellers)} sellers`, Users, 'purple'],
        ['Products', countFormat(kpis.total_products), 'Created in the selected period', Boxes, 'indigo'],
        ['Auctions', countFormat(kpis.total_auctions), `${countFormat(kpis.active_auctions)} active · ${countFormat(kpis.upcoming_auctions)} upcoming`, Gavel, 'amber'],
        ['Completed / cancelled', `${countFormat(kpis.completed_auctions)} / ${countFormat(kpis.cancelled_auctions)}`, 'Current status, filtered by listing date', Gavel, 'rose'],
        ['Recorded bids', countFormat(kpis.recorded_bids), `${countFormat(kpis.valid_bids)} not flagged as anomalous`, BarChart3, 'indigo'],
        ['Settled transactions (demo)', settlementMetricsAvailable ? countFormat(kpis.settled_transactions) : 'Unavailable', settlementMetricsAvailable ? 'Completed demo settlements only' : 'Payment-attempt schema unavailable', ShoppingBag, 'emerald'],
        ['Settlement value (demo)', settlementMetricsAvailable ? currency(kpis.settled_sales_value) : 'Unavailable', 'Not real seller payouts', CircleDollarSign, 'emerald'],
        ['Average settlement (demo)', settlementMetricsAvailable ? currency(kpis.average_settled_selling_price) : 'Unavailable', 'Not real seller payouts', CircleDollarSign, 'purple'],
      ];
    }
    if (visibleData.scope === 'seller') {
      return [
        ['Products', countFormat(kpis.total_products), 'Your products created in this period', Boxes, 'indigo'],
        ['Auctions', countFormat(kpis.total_auctions), `${countFormat(kpis.active_auctions)} active · ${countFormat(kpis.upcoming_auctions)} upcoming`, Gavel, 'amber'],
        ['Completed / cancelled', `${countFormat(kpis.completed_auctions)} / ${countFormat(kpis.cancelled_auctions)}`, 'Your auction records', Gavel, 'rose'],
        ['Valid bids received', countFormat(kpis.valid_bids), 'Anomaly-flagged bids excluded', BarChart3, 'purple'],
        ['Settled transactions (demo)', settlementMetricsAvailable ? countFormat(kpis.settled_transactions) : 'Unavailable', settlementMetricsAvailable ? 'Completed demo settlements only' : 'Payment-attempt schema unavailable', ShoppingBag, 'emerald'],
        ['Settlement value (demo)', settlementMetricsAvailable ? currency(kpis.settled_sales_value) : 'Unavailable', 'Not real seller payouts', CircleDollarSign, 'emerald'],
        ['Average settlement (demo)', settlementMetricsAvailable ? currency(kpis.average_settled_selling_price) : 'Unavailable', 'Not real seller payouts', CircleDollarSign, 'purple'],
      ];
    }
    return [
      ['Valid bids placed', countFormat(kpis.valid_bids), 'Anomaly-flagged bids excluded', BarChart3, 'indigo'],
      ['Auctions participated in', countFormat(kpis.auctions_participated), 'Distinct auctions with valid bids', Gavel, 'amber'],
      ['Auctions won', countFormat(kpis.auctions_won), 'Based on completed auction winner records', Gavel, 'purple'],
      ['Purchases (demo)', settlementMetricsAvailable ? countFormat(kpis.purchases) : 'Unavailable', settlementMetricsAvailable ? 'Completed demo settlement records only' : 'Payment-attempt schema unavailable', ShoppingBag, 'emerald'],
      ['Spending (demo)', settlementMetricsAvailable ? currency(kpis.spending) : 'Unavailable', 'Not actual buyer spending', CircleDollarSign, 'emerald'],
      ['Watchlist items', countFormat(kpis.watchlist_items), 'Your watchlist in the selected period', Boxes, 'rose'],
    ];
  }, [visibleData, kpis, settlementMetricsAvailable]);

  const toggleSort = (key) => {
    if (sortBy === key) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(key);
      setSortDirection(key === 'product_title' || key === 'auction_status' ? 'asc' : 'desc');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-indigo-600">Data from your BidSmart records</p>
          <h1 className="text-2xl font-black tracking-tight text-slate-900">Analytics</h1>
          <p className="mt-1 text-sm text-slate-500">
            {visibleData?.scope === 'admin' ? 'Marketplace-wide performance' : visibleData?.scope === 'seller' ? 'Your selling performance' : 'Your bidding and purchase activity'}
            {' · '}Trend dates are grouped in UTC. Currency is USD.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:min-w-[520px]">
          <label className="text-xs font-semibold text-slate-600">
            From (UTC)
            <input type="date" value={startDate} max={endDate} onChange={(event) => setStartDate(event.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm" />
          </label>
          <label className="text-xs font-semibold text-slate-600">
            To (UTC)
            <input type="date" value={endDate} min={startDate} onChange={(event) => setEndDate(event.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm" />
          </label>
          <label className="text-xs font-semibold text-slate-600">
            Category
            <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
              <option value="">All categories</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>{category.name}</option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {error && (
        <ErrorAlert
          message={error}
          onClose={dateRangeError ? undefined : () => setRequestState((current) => (
            current?.key === filterKey ? { ...current, error: null } : current
          ))}
        />
      )}
      {categoryError && <ErrorAlert message={`Category filters unavailable: ${categoryError}`} />}
      {lastUpdated && (
        <p className="text-right text-xs text-slate-500" aria-live="polite">
          Last updated {new Intl.DateTimeFormat(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short',
          }).format(lastUpdated)}
        </p>
      )}
      {isLoading && !dateRangeError ? (
        <LoadingSpinner message="Loading analytics from recorded activity..." />
      ) : visibleData ? (
        <>
          <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4" aria-label="Analytics key metrics">
            {cards.map(([title, value, subtitle, Icon, color]) => (
              <StatsCard key={title} title={title} value={value} subtitle={subtitle} icon={Icon} color={color} />
            ))}
          </section>
          {!settlementMetricsAvailable && (
            <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              Verified settlement analytics are unavailable because the payment-attempt database table is missing. Auction and bid analytics remain available; settlement totals are not shown as zero.
            </p>
          )}

          <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            <div className={`${chartCard} xl:col-span-2`}>
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-bold text-slate-800">
                  {trendMode === 'monthly' ? 'Monthly activity' : 'Daily activity'}
                </h2>
                <select aria-label="Trend interval" value={trendMode}
                  onChange={(event) => setTrendMode(event.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs">
                  <option value="daily">Daily</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              <p className="mb-3 text-xs text-slate-500">
                Auctions created, bids placed, and successful settlements per UTC {trendMode === 'monthly' ? 'month' : 'day'}.
              </p>
              {trendData.length ? (
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trendData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="period" tickFormatter={trendMode === 'daily' ? localDateLabel : undefined} minTickGap={18} />
                      <YAxis allowDecimals={false} />
                      <Tooltip labelFormatter={trendMode === 'daily' ? localDateLabel : undefined} contentStyle={tooltipStyle} />
                      <Line type="monotone" dataKey="auctions" name="Auctions" stroke="#4f46e5" strokeWidth={2} />
                      <Line type="monotone" dataKey="bids" name="Bids" stroke="#0ea5e9" strokeWidth={2} />
                      {settlementMetricsAvailable && (
                        <Line type="monotone" dataKey="settlements" name="Demo settlements" stroke="#10b981" strokeWidth={2} />
                      )}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : <p className="py-16 text-center text-sm text-slate-400">No activity in this date range.</p>}
            </div>

            <div className={chartCard}>
              <h2 className="text-sm font-bold text-slate-800">Auction status distribution</h2>
              <p className="mb-3 text-xs text-slate-500">Current status of matching auction records.</p>
              {visibleData.auction_status_distribution.length ? (
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={visibleData.auction_status_distribution} dataKey="count" nameKey="status" innerRadius={56} outerRadius={94} paddingAngle={3}>
                        {visibleData.auction_status_distribution.map((entry, index) => (
                          <Cell key={entry.status} fill={STATUS_COLORS[index % STATUS_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => countFormat(value)} contentStyle={tooltipStyle} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : <p className="py-16 text-center text-sm text-slate-400">No auctions match these filters.</p>}
            </div>
          </section>

          <section className={chartCard}>
            <h2 className="text-sm font-bold text-slate-800">Category performance</h2>
            <p className="mb-3 text-xs text-slate-500">Counts and bid activity from the selected scope and date range.</p>
            {visibleData.category_performance.length ? (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={visibleData.category_performance}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="category_name" />
                    <YAxis allowDecimals={false} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="auctions" name="Auctions" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="bids" name="Bids" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : <p className="py-16 text-center text-sm text-slate-400">No category activity for these filters.</p>}
            {visibleData.category_performance.length > 0 && (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-left text-xs">
                  <thead className="border-b border-slate-200 text-slate-500">
                    <tr>
                      <th className="py-2 pr-3">Category</th>
                      <th className="px-2 py-2 text-right">Products</th>
                      <th className="px-2 py-2 text-right">Settlements</th>
                      <th className="py-2 pl-2 text-right">Settled sales</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleData.category_performance.map((item) => (
                      <tr key={item.category_id} className="border-b border-slate-100 last:border-0">
                        <td className="py-2 pr-3 text-slate-700">{item.category_name}</td>
                        <td className="px-2 py-2 text-right tabular-nums">{countFormat(item.products)}</td>
                        <td className="px-2 py-2 text-right tabular-nums">{settlementMetricsAvailable ? countFormat(item.settled_transactions) : '—'}</td>
                        <td className="py-2 pl-2 text-right tabular-nums">{settlementMetricsAvailable ? currency(item.settled_sales_value) : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-800">Product and auction rankings</h2>
                <p className="text-xs text-slate-500">Top 10 by valid bid count, then settled sales value.</p>
              </div>
              <div className="flex gap-2">
                <select aria-label="Ranking type" value={tableMode} onChange={(event) => setTableMode(event.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs">
                  <option value="auctions">Auctions</option>
                  <option value="products">Products</option>
                </select>
                <select aria-label="Sort rankings" value={`${sortBy}:${sortDirection}`} onChange={(event) => {
                  const [key, direction] = event.target.value.split(':');
                  setSortBy(key);
                  setSortDirection(direction);
                }} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs">
                  <option value="valid_bids:desc">Most valid bids</option>
                  {settlementMetricsAvailable && <option value="settled_sales_value:desc">Highest demo settlements</option>}
                  {settlementMetricsAvailable && <option value="settled_sales_value:asc">Lowest demo settlements</option>}
                  <option value="product_title:asc">Product title</option>
                  <option value="auction_status:asc">Auction status</option>
                </select>
              </div>
            </div>
            {sortedRankings.length ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-100 text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      {[
                        ['Product', 'product_title'],
                        ['Category', null],
                        ['Status', 'auction_status'],
                        ['Valid bids', 'valid_bids'],
                        ['Demo settlements', settlementMetricsAvailable ? 'settled_transactions' : null],
                        ['Demo settlement value', settlementMetricsAvailable ? 'settled_sales_value' : null],
                      ].map(([label, key]) => (
                        <th key={label} className="px-4 py-3">
                          {key ? (
                            <button type="button" onClick={() => toggleSort(key)} className="font-bold hover:text-indigo-600">
                              {label}{sortBy === key ? (sortDirection === 'asc' ? ' ↑' : ' ↓') : ''}
                            </button>
                          ) : label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {sortedRankings.map((item) => (
                      <tr key={`${item.product_id}-${item.auction_id || 'product'}`} className="hover:bg-slate-50">
                        <td className="px-4 py-3 font-semibold text-slate-800">{item.product_title}</td>
                        <td className="px-4 py-3 text-slate-600">{item.category_name}</td>
                        <td className="px-4 py-3 text-slate-600">{formatStatus(item.auction_status)}</td>
                        <td className="px-4 py-3 tabular-nums">{countFormat(item.valid_bids)}</td>
                        <td className="px-4 py-3 tabular-nums">{settlementMetricsAvailable ? countFormat(item.settled_transactions) : '—'}</td>
                        <td className="px-4 py-3 tabular-nums">{settlementMetricsAvailable ? currency(item.settled_sales_value) : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p className="p-8 text-center text-sm text-slate-400">No products or auctions match these filters.</p>}
          </section>

          {!visibleData.daily_trends.length && !visibleData.category_performance.some((item) => item.auctions || item.bids) && (
            <p className="rounded-xl border border-dashed border-slate-300 bg-white p-5 text-center text-sm text-slate-500">
              No recorded activity matches this date range and category. KPI totals show zero where no records are available.
            </p>
          )}
        </>
      ) : !error ? (
        <p className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
          Analytics are unavailable for this request.
        </p>
      ) : null}
    </div>
  );
};
