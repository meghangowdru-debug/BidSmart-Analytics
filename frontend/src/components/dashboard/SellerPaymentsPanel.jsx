import React, { useEffect, useState } from 'react';
import { CreditCard, RefreshCw } from 'lucide-react';
import { paymentsApi } from '../../api/payments';
import { getErrorMessage } from '../../api/client';
import { EmptyState } from '../common/EmptyState';
import { ErrorAlert } from '../common/ErrorAlert';
import { LoadingSpinner } from '../common/LoadingSpinner';

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

const paymentLabel = (transaction) => {
  if (transaction.payment_verified) return 'Payment verified (demo)';
  switch (transaction.payment_status) {
    case 'SETTLEMENT_PENDING_DEMO': return 'Payment pending';
    case 'SETTLEMENT_FAILED_DEMO': return 'Payment failed';
    case 'CANCELLED': return 'Cancelled';
    case 'SETTLEMENT_COMPLETED_DEMO': return 'Verification unavailable';
    default: return 'Status unavailable';
  }
};

const settlementLabel = (transaction) => {
  if (
    transaction.payment_status === 'SETTLEMENT_COMPLETED_DEMO'
    && transaction.payment_verified
    && transaction.settled_at
  ) return 'Completed (simulated)';
  switch (transaction.payment_status) {
    case 'SETTLEMENT_PENDING_DEMO': return 'Pending (simulated)';
    case 'SETTLEMENT_FAILED_DEMO': return 'Failed (simulated)';
    case 'CANCELLED': return 'Cancelled';
    default: return 'Not confirmed';
  }
};

const statusClass = (verified) => (
  verified
    ? 'bg-emerald-50 text-emerald-700'
    : 'bg-amber-50 text-amber-800'
);

export const SellerPaymentsPanel = () => {
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshCount, setRefreshCount] = useState(0);

  useEffect(() => {
    let isCurrentRequest = true;
    paymentsApi.listMySellerTransactions({ page, page_size: PAGE_SIZE })
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
    <section className="space-y-5" aria-labelledby="seller-payments-title">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="seller-payments-title" className="text-lg font-bold text-slate-900">
            Payments &amp; Earnings
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Seller transactions and simulated settlement status. No payouts are initiated here.
          </p>
        </div>
        <button
          type="button"
          onClick={reload}
          disabled={isLoading}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {isLoading ? (
        <LoadingSpinner message="Loading seller settlements..." />
      ) : error ? (
        <div>
          <ErrorAlert message={error} />
          <button
            type="button"
            onClick={reload}
            className="mt-3 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-bold text-white hover:bg-indigo-700"
          >
            Retry
          </button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[
              ['Verified payments (demo)', formatMoney(result?.summary?.verified_payment_total ?? result?.summary?.total_sales ?? 0)],
              ['Pending demo settlements', formatMoney(result?.summary?.pending_settlements || 0)],
              ['Completed simulated settlements', formatMoney(result?.summary?.simulated_settlement_total ?? result?.summary?.completed_settlements ?? 0)],
              ['Transactions', result?.summary?.transaction_count || 0],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
                <p className="mt-2 text-xl font-black text-slate-900">{value}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-500">
            Totals cover all seller transactions. Completed amounts require backend payment verification and a settlement timestamp. SIMULATED_DEMO records do not represent real money received or a seller payout.
          </p>

          {result?.items?.length ? (
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[1050px] text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-4 py-3 font-bold">Product / Auction</th>
                      <th className="px-4 py-3 font-bold">Transaction</th>
                      <th className="px-4 py-3 font-bold">Amount (USD)</th>
                      <th className="px-4 py-3 font-bold">Payment</th>
                      <th className="px-4 py-3 font-bold">Settlement</th>
                      <th className="px-4 py-3 font-bold">Created</th>
                      <th className="px-4 py-3 font-bold">Settled</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {result.items.map((transaction) => (
                      <tr key={transaction.transaction_id}>
                        <td className="px-4 py-4">
                          <p className="font-semibold text-slate-900">{transaction.product_title}</p>
                          <p className="mt-1 text-xs text-slate-500">Auction #{transaction.auction_id}</p>
                        </td>
                        <td className="px-4 py-4 font-mono text-slate-700">#{transaction.transaction_id}</td>
                        <td className="whitespace-nowrap px-4 py-4 font-bold text-slate-900">
                          {formatMoney(transaction.amount, transaction.currency)}
                        </td>
                        <td className="px-4 py-4">
                          <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${statusClass(transaction.payment_verified)}`}>
                            {paymentLabel(transaction)}
                          </span>
                        </td>
                        <td className="px-4 py-4">
                          <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${
                            transaction.payment_verified && transaction.settled_at
                              ? 'bg-emerald-50 text-emerald-700'
                              : 'bg-slate-100 text-slate-700'
                          }`}>
                            {settlementLabel(transaction)}
                          </span>
                          <p className="mt-1 text-[11px] text-slate-500">
                            {transaction.settlement_type === 'SIMULATED_DEMO'
                              ? 'SIMULATED_DEMO · no payout'
                              : transaction.settlement_type}
                          </p>
                        </td>
                        <td className="whitespace-nowrap px-4 py-4 text-slate-600">{formatDate(transaction.created_at)}</td>
                        <td className="whitespace-nowrap px-4 py-4 text-slate-600">{formatDate(transaction.settled_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-4 py-3">
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
            </div>
          ) : (
            <EmptyState
              icon={CreditCard}
              title="No seller transactions yet"
              description="Transactions for completed auctions associated with your seller account will appear here."
            />
          )}
        </>
      )}
    </section>
  );
};
