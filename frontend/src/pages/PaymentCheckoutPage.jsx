import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, CreditCard, ShieldCheck } from 'lucide-react';
import { paymentsApi } from '../api/payments';
import { getErrorMessage } from '../api/client';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { SuccessAlert } from '../components/common/SuccessAlert';
import { loadRazorpayCheckout } from '../utils/razorpay';

const formatMoney = (amount) => new Intl.NumberFormat(undefined, {
  style: 'currency',
  currency: 'USD',
}).format(Number(amount));

const findWonAuction = async (auctionId) => {
  let page = 1;
  let pages = 1;
  do {
    const result = await paymentsApi.listWonAuctions({ page, page_size: 100 });
    const auction = (result.items || []).find(
      (item) => String(item.auction_id) === String(auctionId),
    );
    if (auction) return auction;
    pages = result.pages || 1;
    page += 1;
  } while (page <= pages);
  return null;
};

export const PaymentCheckoutPage = () => {
  const { auctionId } = useParams();
  const navigate = useNavigate();
  const [auction, setAuction] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isPaying, setIsPaying] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [outcome, setOutcome] = useState('');

  const loadAuction = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    setError('');
    try {
      const result = await findWonAuction(auctionId);
      if (!result) {
        setAuction(null);
        setError('This auction is not available in your completed wins.');
        return;
      }
      setAuction(result);
      if (!result.payment_required && !result.payment_verified) {
        setError(
          'Payment is not currently available for this auction.',
        );
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }, [auctionId]);

  useEffect(() => {
    loadAuction();
  }, [loadAuction]);

  const handlePayNow = async () => {
    if (!auction?.payment_required || isPaying) return;
    setIsPaying(true);
    setError('');
    setSuccess('');
    setOutcome('');

    try {
      const order = await paymentsApi.createOrder(auction.auction_id);
      if (!order.key_id?.startsWith('rzp_test_')) {
        throw new Error('Checkout is unavailable because the server is not configured for Razorpay TEST mode.');
      }
      if (
        order.currency !== 'USD'
        || !Number.isSafeInteger(order.amount)
        || order.amount !== Math.round(Number(auction.amount) * 100)
      ) {
        throw new Error('The payment order does not match the authoritative auction amount.');
      }
      const Razorpay = await loadRazorpayCheckout();

      await new Promise((resolve) => {
        let verificationStarted = false;
        const checkout = new Razorpay({
          key: order.key_id,
          amount: order.amount,
          currency: order.currency,
          order_id: order.order_id,
          name: 'BidSmart Analytics',
          description: auction.product_title,
          handler: async (providerResponse) => {
            verificationStarted = true;
            try {
              const verification = await paymentsApi.verifyPayment({
                order_id: providerResponse.razorpay_order_id,
                payment_id: providerResponse.razorpay_payment_id,
                signature: providerResponse.razorpay_signature,
              });
              if (verification.payment_status !== 'SETTLEMENT_COMPLETED_DEMO') {
                throw new Error('The server has not confirmed payment completion.');
              }
              setAuction((current) => current && ({
                ...current,
                payment_status: verification.payment_status,
                payment_required: false,
                payment_verified: true,
              }));
              setSuccess('Payment verified successfully. Your auction is paid.');
              setOutcome('success');
              await loadAuction(false);
            } catch (verificationError) {
              setError(getErrorMessage(verificationError));
              setOutcome('verification-error');
            } finally {
              resolve();
            }
          },
          modal: {
            ondismiss: () => {
              if (!verificationStarted) {
                setOutcome('cancelled');
                setError('Checkout was cancelled. You can retry when ready.');
                resolve();
              }
            },
          },
          theme: { color: '#4f46e5' },
        });
        checkout.on('payment.failed', (failure) => {
          setOutcome('failed');
          setError(
            failure?.error?.description
              ? `Payment failed: ${failure.error.description}`
              : 'Payment failed. No successful payment was recorded.',
          );
          resolve();
        });
        checkout.open();
      });
    } catch (requestError) {
      setOutcome('error');
      setError(getErrorMessage(requestError));
    } finally {
      setIsPaying(false);
    }
  };

  if (isLoading) return <LoadingSpinner message="Loading secure checkout..." />;

  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <Link
        to="/dashboard/buyer"
        className="mb-6 inline-flex items-center gap-2 text-sm font-semibold text-indigo-600 hover:text-indigo-800"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Buyer Hub
      </Link>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 bg-slate-50 px-5 py-5 sm:px-7">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-100 text-indigo-700">
              <CreditCard className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-black text-slate-900">Auction Checkout</h1>
              <p className="mt-1 text-sm text-slate-500">Secure Razorpay TEST-mode payment</p>
            </div>
          </div>
        </div>

        <div className="space-y-5 p-5 sm:p-7">
          {error && (
            <div>
              <ErrorAlert message={error} />
              {!auction && (
                <button
                  type="button"
                  onClick={loadAuction}
                  className="mb-4 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-bold text-white hover:bg-indigo-700"
                >
                  Retry
                </button>
              )}
            </div>
          )}
          {success && <SuccessAlert message={success} />}

          {auction ? (
            <div className="flex flex-col gap-5 rounded-xl border border-slate-200 p-4 sm:flex-row">
              <img
                src={auction.product_image_url}
                alt=""
                className="h-48 w-full rounded-lg bg-slate-100 object-cover sm:h-36 sm:w-44"
              />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                  Completed winning auction
                </p>
                <h2 className="mt-1 text-lg font-bold text-slate-900">{auction.product_title}</h2>
                <p className="mt-3 text-sm text-slate-500">
                  Completed {new Date(auction.end_time).toLocaleString()}
                </p>
                <p className="mt-4 text-3xl font-black text-slate-900">
                  {formatMoney(auction.amount)}
                </p>
                <p className="mt-1 text-xs text-slate-500">Authoritative winning amount · USD</p>
              </div>
            </div>
          ) : (
            !error && <p className="text-sm text-slate-500">Auction details are unavailable.</p>
          )}

          {outcome === 'success' && (
            <div className="rounded-lg bg-emerald-50 p-4 text-sm font-medium text-emerald-800">
              Payment verification completed by the server.
            </div>
          )}
          {outcome === 'cancelled' && (
            <div className="rounded-lg bg-amber-50 p-4 text-sm font-medium text-amber-800">
              No payment was confirmed. You may retry checkout.
            </div>
          )}
          {outcome === 'failed' && (
            <div className="rounded-lg bg-rose-50 p-4 text-sm font-medium text-rose-800">
              The provider reported a failed attempt. The transaction remains unpaid.
            </div>
          )}
          {outcome === 'verification-error' && (
            <div className="rounded-lg bg-amber-50 p-4 text-sm font-medium text-amber-800">
              Payment has not been marked paid. Retry verification later or return to your wins.
            </div>
          )}

          {auction?.payment_verified && (
            <p role="status" className="inline-flex items-center gap-2 font-semibold text-emerald-700">
              <ShieldCheck className="h-5 w-5" />
              Verified payment status: Paid
            </p>
          )}

          {auction?.payment_required && (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="inline-flex items-center gap-2 text-xs text-slate-500">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                Payment is marked successful only after backend verification.
              </p>
              <button
                type="button"
                onClick={handlePayNow}
                disabled={isPaying}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-3 text-sm font-bold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isPaying ? 'Connecting to checkout…' : outcome === 'success' ? 'Payment verified' : 'Pay securely'}
              </button>
            </div>
          )}

          {auction && !auction.payment_required && (
            <button
              type="button"
              onClick={async () => {
                await loadAuction();
                navigate('/dashboard/buyer');
              }}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              Return to Buyer Hub
            </button>
          )}
        </div>
      </section>
    </main>
  );
};
