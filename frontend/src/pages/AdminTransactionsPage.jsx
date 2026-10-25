import React, { useEffect, useState } from 'react';
import { RefreshCw, ShieldCheck } from 'lucide-react';
import { paymentsApi } from '../api/payments';
import { getErrorMessage } from '../api/client';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

const PAGE_SIZE = 20;
const PAYMENT_STATUSES = [
  'SETTLEMENT_PENDING_DEMO',
  'SETTLEMENT_COMPLETED_DEMO',
  'SETTLEMENT_FAILED_DEMO',
  'CANCELLED',
];

const formatDate = (value) => (
  value
    ? new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
    : '—'
);

const formatMoney = (amount, currency) => new Intl.NumberFormat(undefined, {
  style: 'currency',
  currency,
}).format(Number(amount));

export const AdminTransactionsPage = () => {
  const [filters, setFilters] = useState({
    payment_status: '',
    buyer_id: '',
    auction_id: '',
    created_from: '',
    created_to: '',
  });
  const [appliedFilters, setAppliedFilters] = useState({});
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshCount, setRefreshCount] = useState(0);

  useEffect(() => {
    let isCurrentRequest = true;
    const params = { page, page_size: PAGE_SIZE };
    Object.entries(appliedFilters).forEach(([key, value]) => {
      if (value !== '') params[key] = value;
    });
    paymentsApi.listAdminTransactions(params)
      .then((data) => {
        if (isCurrentRequest) {
          setResult(data);
          setError('');
        }
      })
      .catch((requestError) => {
        if (isCurrentRequest) setError(getErrorMessage(requestError));
      })
      .finally(() => {
        if (isCurrentRequest) setIsLoading(false);
      });
    return () => {
      isCurrentRequest = false;
    };
  }, [appliedFilters, page, refreshCount]);

  const reload = () => {
    setIsLoading(true);
    setError('');
    setRefreshCount((current) => current + 1);
  };

  const submitFilters = (event) => {
    event.preventDefault();
    setIsLoading(true);
    setError('');
    setPage(1);
    setAppliedFilters({ ...filters });
  };

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-rose-700">
            <ShieldCheck className="h-4 w-4" />
            Administrator only
          </p>
          <h1 className="mt-1 text-2xl font-black text-slate-900">Transaction Monitoring</h1>
          <p className="mt-1 text-sm text-slate-500">
            Monitor transaction states and verified settlement dates. Provider secrets and signatures are not exposed.
          </p>
        </div>
        <button
          type="button"
          onClick={reload}
          disabled={isLoading}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 disabled:opacity-60"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </header>

      <form onSubmit={submitFilters} className="grid grid-cols-1 gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <label className="text-xs font-semibold text-slate-600">
          Payment status
          <select
            value={filters.payment_status}
            onChange={(event) => setFilters((current) => ({ ...current, payment_status: event.target.value }))}
            className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            {PAYMENT_STATUSES.map((status) => <option key={status} value={status}>{status.replaceAll('_', ' ')}</option>)}
          </select>
        </label>
        <label className="text-xs font-semibold text-slate-600">
          Buyer ID
          <input
            type="number"
            min="1"
            value={filters.buyer_id}
            onChange={(event) => setFilters((current) => ({ ...current, buyer_id: event.target.value }))}
            className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="text-xs font-semibold text-slate-600">
          Auction ID
          <input
            type="number"
            min="1"
            value={filters.auction_id}
            onChange={(event) => setFilters((current) => ({ ...current, auction_id: event.target.value }))}
            className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="text-xs font-semibold text-slate-600">
          Created from
          <input
            type="date"
            value={filters.created_from}
            onChange={(event) => setFilters((current) => ({ ...current, created_from: event.target.value }))}
            className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="text-xs font-semibold text-slate-600">
          Created through
          <input
            type="date"
            value={filters.created_to}
            onChange={(event) => setFilters((current) => ({ ...current, created_to: event.target.value }))}
            className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <div className="flex items-end gap-2">
          <button type="submit" className="w-full rounded-lg bg-rose-600 px-3 py-2 text-sm font-bold text-white hover:bg-rose-700">
            Apply filters
          </button>
          <button
            type="button"
            onClick={() => {
              const cleared = { payment_status: '', buyer_id: '', auction_id: '', created_from: '', created_to: '' };
              setFilters(cleared);
              setIsLoading(true);
              setError('');
              setAppliedFilters(cleared);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            Clear
          </button>
        </div>
      </form>

      {isLoading ? (
        <LoadingSpinner message="Loading transactions..." />
      ) : error ? (
        <section>
          <ErrorAlert message={error} />
          <button
            type="button"
            onClick={reload}
            className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-bold text-white hover:bg-rose-700"
          >
            Retry
          </button>
        </section>
      ) : result?.items?.length ? (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1120px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-bold">Transaction</th>
                  <th className="px-4 py-3 font-bold">Auction / Product</th>
                  <th className="px-4 py-3 font-bold">Buyer</th>
                  <th className="px-4 py-3 font-bold">Seller</th>
                  <th className="px-4 py-3 font-bold">Amount</th>
                  <th className="px-4 py-3 font-bold">Status</th>
                  <th className="px-4 py-3 font-bold">Created</th>
                  <th className="px-4 py-3 font-bold">Settled</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {result.items.map((transaction) => (
                  <tr key={transaction.transaction_id}>
                    <td className="whitespace-nowrap px-4 py-4 font-semibold text-slate-900">#{transaction.transaction_id}</td>
                    <td className="px-4 py-4">
                      <p className="font-semibold text-slate-900">{transaction.product_title}</p>
                      <p className="text-xs text-slate-500">Auction #{transaction.auction_id}</p>
                    </td>
                    <td className="px-4 py-4">#{transaction.buyer_id}</td>
                    <td className="px-4 py-4">#{transaction.seller_id}</td>
                    <td className="whitespace-nowrap px-4 py-4 font-bold">{formatMoney(transaction.amount, transaction.currency)}</td>
                    <td className="px-4 py-4">
                      <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${
                        transaction.payment_verified ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-700'
                      }`}>
                        {transaction.payment_verified ? 'Paid (verified)' : transaction.payment_status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-4 text-slate-600">{formatDate(transaction.created_at)}</td>
                    <td className="whitespace-nowrap px-4 py-4 text-slate-600">{formatDate(transaction.settled_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-4 py-4">
            <p className="text-xs text-slate-500">Page {result.page} of {result.pages} · {result.total} transactions</p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  setIsLoading(true);
                  setPage((current) => Math.max(1, current - 1));
                }}
                disabled={page <= 1}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsLoading(true);
                  setPage((current) => Math.min(result.pages, current + 1));
                }}
                disabled={page >= result.pages}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </section>
      ) : (
        <EmptyState
          icon={ShieldCheck}
          title="No transactions match these filters"
          description="Change or clear the filters to inspect other marketplace transactions."
        />
      )}
    </main>
  );
};
