import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, Clock3, CreditCard, RefreshCw, Trophy } from 'lucide-react';
import { paymentsApi } from '../../api/payments';
import { getErrorMessage } from '../../api/client';
import { EmptyState } from '../common/EmptyState';
import { ErrorAlert } from '../common/ErrorAlert';
import { LoadingSpinner } from '../common/LoadingSpinner';

const formatMoney = (amount) => (
  amount == null
    ? 'Amount unavailable'
    : new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: 'USD',
    }).format(Number(amount))
);

const formatDate = (value) => new Date(value).toLocaleString(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
});

const paymentLabel = (auction) => {
  if (auction.payment_verified) return 'Paid';
  if (auction.payment_status === 'SETTLEMENT_FAILED_DEMO') return 'Payment failed';
  if (auction.payment_status === 'CANCELLED') return 'Payment cancelled';
  if (auction.payment_status === 'SETTLEMENT_PENDING_DEMO') return 'Payment pending';
  return 'Payment record unavailable';
};

export const WonAuctionsPanel = () => {
  const [auctions, setAuctions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const loadWonAuctions = useCallback(async () => {
    setIsLoading(true);
    setError('');
    try {
      const firstPage = await paymentsApi.listWonAuctions({ page: 1, page_size: 100 });
      const allItems = [...(firstPage.items || [])];
      for (let page = 2; page <= (firstPage.pages || 1); page += 1) {
        const response = await paymentsApi.listWonAuctions({ page, page_size: 100 });
        allItems.push(...(response.items || []));
      }
      setAuctions(allItems);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWonAuctions();
  }, [loadWonAuctions]);

  if (isLoading) return <LoadingSpinner message="Loading your won auctions..." />;

  return (
    <section className="p-4 sm:p-6" aria-labelledby="won-auctions-title">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="won-auctions-title" className="text-lg font-bold text-slate-900">
            Won Auctions
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Completed auctions awarded to your buyer account.
          </p>
        </div>
        <button
          type="button"
          onClick={loadWonAuctions}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div>
          <ErrorAlert message={error} />
          <button
            type="button"
            onClick={loadWonAuctions}
            className="mb-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
          >
            Retry
          </button>
        </div>
      )}

      {!error && auctions.length === 0 ? (
        <EmptyState
          icon={Trophy}
          title="No completed wins yet"
          description="Auctions you win will appear here with their verified payment status."
        />
      ) : auctions.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {auctions.map((auction) => {
            const paid = auction.payment_verified === true;
            const needsPayment = auction.payment_required === true;
            return (
              <article
                key={auction.auction_id}
                className="flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm sm:flex-row"
              >
                <img
                  src={auction.product_image_url}
                  alt=""
                  className="h-44 w-full bg-slate-100 object-cover sm:h-auto sm:w-36"
                />
                <div className="flex min-w-0 flex-1 flex-col p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <h3 className="font-bold text-slate-900">{auction.product_title}</h3>
                    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ${
                      paid
                        ? 'bg-emerald-50 text-emerald-700'
                        : needsPayment
                          ? 'bg-amber-50 text-amber-700'
                          : 'bg-slate-100 text-slate-600'
                    }`}>
                      {paid ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Clock3 className="h-3.5 w-3.5" />}
                      {paymentLabel(auction)}
                    </span>
                  </div>
                  <p className="mt-3 text-xl font-black text-slate-900">
                    {formatMoney(auction.amount)}
                  </p>
                  <p className="mt-2 text-xs text-slate-500">
                    Auction completed {formatDate(auction.end_time)}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Status: {auction.auction_status}
                  </p>
                  {needsPayment && (
                    <Link
                      to={`/checkout/${auction.auction_id}`}
                      className="mt-4 inline-flex w-fit items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-bold text-white transition-colors hover:bg-indigo-700"
                    >
                      <CreditCard className="h-4 w-4" />
                      Pay Now
                    </Link>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      ) : null}
    </section>
  );
};
