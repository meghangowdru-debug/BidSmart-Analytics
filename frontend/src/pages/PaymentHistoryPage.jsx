import React, { useEffect, useState } from 'react';
import { CreditCard, RefreshCw } from 'lucide-react';
import { paymentsApi } from '../api/payments';
import { getErrorMessage } from '../api/client';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

const PAGE_SIZE = 20;

const formatMoney = (amount, currency = 'USD') => new Intl.NumberFormat(undefined, {
  style: 'currency',
  currency,
}).format(Number(amount));

const formatDate = (value) => (
  value
    ? new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
    : '—'
);

const statusLabel = (transaction) => {
  if (transaction.payment_verified) return 'Paid (verified)';
  switch (transaction.payment_status) {
    case 'SETTLEMENT_PENDING_DEMO': return 'Payment pending';
    case 'SETTLEMENT_FAILED_DEMO': return 'Payment failed';
    case 'CANCELLED': return 'Cancelled';
    case 'SETTLEMENT_COMPLETED_DEMO': return 'Verification unavailable';
    default: return transaction.payment_status;
  }
};

export const PaymentHistoryPage = () => {
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshCount, setRefreshCount] = useState(0);

  useEffect(() => {
    let isCurrentRequest = true;
    paymentsApi.listMyTransactions({ page, page_size: PAGE_SIZE })
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
  }, [page, refreshCount]);

  const reload = () => {
    setIsLoading(true);
    setError('');
    setRefreshCount((current) => current + 1);
  };

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black text-slate-900">Payment History</h1>
          <p className="mt-1 text-sm text-slate-500">
            Your buyer account transactions and verified settlement dates.
          </p>
        </div>
        <button
          type="button"
          onClick={reload}
          disabled={isLoading}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-white disabled:opacity-60"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {isLoading ? (
        <LoadingSpinner message="Loading your payment history..." />
      ) : error ? (
        <section>
          <ErrorAlert message={error} />
          <button
            type="button"
            onClick={reload}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-bold text-white hover:bg-indigo-700"
          >
            Retry
          </button>
        </section>
      ) : result?.items?.length ? (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-bold">Product / Auction</th>
                  <th className="px-5 py-3 font-bold">Amount</th>
                  <th className="px-5 py-3 font-bold">Status</th>
                  <th className="px-5 py-3 font-bold">Created</th>
                  <th className="px-5 py-3 font-bold">Settled</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {result.items.map((transaction) => (
                  <tr key={transaction.transaction_id}>
                    <td className="px-5 py-4">
                      <p className="font-semibold text-slate-900">{transaction.product_title}</p>
                      <p className="mt-1 text-xs text-slate-500">Auction #{transaction.auction_id}</p>
                    </td>
                    <td className="whitespace-nowrap px-5 py-4 font-bold text-slate-900">
                      {formatMoney(transaction.amount, transaction.currency)}
                    </td>
                    <td className="px-5 py-4">
                      <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${
                        transaction.payment_verified
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-slate-100 text-slate-700'
                      }`}>
                        {statusLabel(transaction)}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-5 py-4 text-slate-600">{formatDate(transaction.created_at)}</td>
                    <td className="whitespace-nowrap px-5 py-4 text-slate-600">{formatDate(transaction.settled_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-5 py-4">
            <p className="text-xs text-slate-500">
              Page {result.page} of {result.pages} · {result.total} transactions
            </p>
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
          icon={CreditCard}
          title="No payment history yet"
          description="Transactions for auctions you win will appear here."
        />
      )}
    </main>
  );
};
