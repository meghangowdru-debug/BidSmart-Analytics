import React, { useState } from 'react';
import { CheckCircle2, ShieldAlert, RefreshCw } from 'lucide-react';
import { ErrorAlert } from '../common/ErrorAlert';
import { LoadingSpinner } from '../common/LoadingSpinner';

export const PAYMENT_SETUP_REQUIRED_MESSAGE =
  'Complete Payment Setup before cataloging products or creating auctions.';

export const SellerPaymentSetupPanel = ({
  setup,
  isLoading,
  error,
  isSubmitting,
  onRetry,
  onComplete,
}) => {
  const [acknowledged, setAcknowledged] = useState(false);
  const completed = setup?.status === 'DEMO_COMPLETED';

  return (
    <section className="space-y-5" aria-labelledby="seller-payment-setup-title">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="seller-payment-setup-title" className="text-lg font-bold text-slate-900">
            Payment Setup
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Required before you can catalog products or create auctions.
          </p>
        </div>
        <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-amber-800">
          Simulated demo
        </span>
      </div>

      {isLoading ? (
        <LoadingSpinner message="Checking payment setup..." />
      ) : error ? (
        <div>
          <ErrorAlert message={error} />
          <button
            type="button"
            onClick={onRetry}
            className="mt-3 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-bold text-white hover:bg-indigo-700"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </button>
        </div>
      ) : setup?.status === 'NOT_REQUIRED' ? (
        <p className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          {setup.message}
        </p>
      ) : completed ? (
        <div className="space-y-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <p className="flex items-center gap-2 text-sm font-bold text-emerald-800">
            <CheckCircle2 className="h-5 w-5" />
            Demo payment setup complete
          </p>
          <p className="text-sm text-emerald-900">
            You can catalog products and create auctions. This setup is simulated:
            no bank details were collected and no real payouts are enabled.
          </p>
        </div>
      ) : (
        <div className="space-y-4 rounded-xl border border-amber-200 bg-amber-50/60 p-4">
          <p className="flex items-center gap-2 text-sm font-bold text-amber-900">
            <ShieldAlert className="h-5 w-5" />
            Payment setup not completed
          </p>
          <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-700">
            <li>Read the demo notice below.</li>
            <li>Confirm you understand this is a simulation.</li>
            <li>Select &ldquo;Complete simulated setup&rdquo;.</li>
          </ol>
          <p className="text-sm text-slate-700">
            This platform runs in demo mode. Setup here is a simulation: BidSmart does
            not collect real bank details and does not enable real payouts. Verified
            payment-provider onboarding for real payouts is not available yet.
          </p>
          <label className="flex items-start gap-2 text-sm text-slate-800">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(event) => setAcknowledged(event.target.checked)}
              className="mt-0.5"
            />
            <span>I understand this is a simulated demo setup and no real payouts are enabled.</span>
          </label>
          <button
            type="button"
            onClick={onComplete}
            disabled={!acknowledged || isSubmitting}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-bold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {isSubmitting ? 'Completing...' : 'Complete simulated setup'}
          </button>
        </div>
      )}
    </section>
  );
};
