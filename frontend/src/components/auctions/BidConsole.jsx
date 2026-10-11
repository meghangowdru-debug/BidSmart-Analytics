import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Gavel, AlertCircle, CheckCircle, ShieldAlert, Zap, TrendingUp } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { bidsApi } from '../../api/bids';
import { getErrorMessage } from '../../api/client';
import { parseAuctionDateMs } from '../../utils/auctionActions';

export const BidConsole = ({ auction, onBidSuccess }) => {
  const { isAuthenticated, user, isBuyer, isSeller, isAdmin } = useAuth();
  const [bidAmount, setBidAmount] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successInfo, setSuccessInfo] = useState(null);

  const isExpired = auction.seconds_remaining <= 0 || parseAuctionDateMs(auction.end_time) <= Date.now();
  const isActive = auction.status === 'ACTIVE' && !isExpired;
  const isOwnListing = user && auction.product && auction.product.seller_id === user.id;

  // Calculate minimum valid next bid
  const currentHighest = auction.current_highest_bid !== null && auction.current_highest_bid !== undefined
    ? Number(auction.current_highest_bid)
    : null;
  const startingPrice = Number(auction.starting_price || 0);
  const minIncrement = Number(auction.minimum_increment || 1);

  const minNextBid = currentHighest !== null
    ? currentHighest + minIncrement
    : startingPrice;

  // Set default bid input to minNextBid when changed
  const handleQuickAdd = (increment) => {
    const base = Number(bidAmount) || minNextBid;
    setBidAmount((base + increment).toFixed(2));
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessInfo(null);

    const amountNum = Number(bidAmount);
    if (isNaN(amountNum) || amountNum <= 0) {
      setError('Please enter a valid positive numeric bid amount.');
      return;
    }

    if (amountNum < minNextBid) {
      setError(`Bid must be at least $${minNextBid.toFixed(2)}.`);
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await bidsApi.submitBid(auction.id, amountNum);
      setSuccessInfo({
        bidAmount: response.bid_amount,
        antiSnipe: response.anti_snipe_extended,
        newEndTime: response.new_end_time,
      });
      setBidAmount('');
      if (onBidSuccess) {
        onBidSuccess(response);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Case 1: Unauthenticated
  if (!isAuthenticated) {
    return (
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 text-center">
        <Gavel className="w-8 h-8 text-indigo-600 mx-auto mb-2" />
        <h4 className="text-base font-semibold text-slate-900 mb-1">Place a Verified Bid</h4>
        <p className="text-sm text-slate-500 mb-4 max-w-sm mx-auto">
          Sign in to your verified Buyer account to place atomic bids with anti-sniping protection.
        </p>
        <Link
          to="/login"
          className="inline-flex items-center justify-center px-4 py-2.5 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm transition-colors"
        >
          Sign In as Buyer
        </Link>
      </div>
    );
  }

  // Case 2: Auction is not active or has expired
  if (!isActive) {
    return (
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 text-center">
        <ShieldAlert className="w-8 h-8 text-slate-400 mx-auto mb-2" />
        <h4 className="text-base font-semibold text-slate-800 mb-1">Bidding Closed</h4>
        <p className="text-sm text-slate-500">
          This auction is currently <span className="font-semibold">{auction.status}</span> and cannot accept new bids.
        </p>
      </div>
    );
  }

  // Case 3: Anti-Self-Bidding Restriction
  if (isOwnListing) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-center">
        <ShieldAlert className="w-8 h-8 text-amber-600 mx-auto mb-2" />
        <h4 className="text-base font-semibold text-amber-900 mb-1">Anti-Self-Bidding Protection</h4>
        <p className="text-xs text-amber-700 max-w-md mx-auto">
          Marketplace compliance rules prohibit sellers from bidding on their own listings to manipulate final valuation.
        </p>
      </div>
    );
  }

  // Case 4: Non-buyer role restriction (Admins & Sellers prohibited from bidding)
  if (!isBuyer) {
    return (
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 text-center">
        <ShieldAlert className="w-8 h-8 text-indigo-600 mx-auto mb-2" />
        <h4 className="text-base font-semibold text-slate-900 mb-1">Buyer Role Required</h4>
        <p className="text-xs text-slate-600 max-w-md mx-auto mb-3">
          Your current account role is <span className="font-bold">{user?.role}</span>. To maintain marketplace integrity, only authenticated active <span className="font-bold text-indigo-600">BUYER</span> accounts may place bids.
        </p>
        <span className="inline-block text-xs text-slate-400 bg-white px-3 py-1 rounded border border-slate-200 font-mono">
          Seller & Admin bidding is strictly prohibited by backend engine
        </span>
      </div>
    );
  }

  // Case 5: Authenticated Buyer Console
  return (
    <div className="bg-white border-2 border-indigo-100 rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
        <div>
          <span className="text-xs uppercase tracking-wider text-slate-400 font-bold block">
            Minimum Next Bid
          </span>
          <div className="text-2xl font-black text-indigo-600">
            ${minNextBid.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        <div className="text-right">
          <span className="text-xs text-slate-400 font-medium block">Increment Step</span>
          <span className="text-xs font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
            +${minIncrement.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Success Banner */}
      {successInfo && (
        <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-start space-x-2">
          <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Bid Placed Successfully!</span>
            <p>Your bid of ${Number(successInfo.bidAmount).toFixed(2)} is now the highest active bid.</p>
            {successInfo.antiSnipe && (
              <p className="mt-1 font-semibold text-amber-700 flex items-center">
                <Zap className="w-3.5 h-3.5 mr-1" />
                Anti-Sniping Active: Deadline automatically extended by 60 seconds!
              </p>
            )}
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-start space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
          <span className="leading-relaxed">{error}</span>
        </div>
      )}

      {/* Bid Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="bidAmountInput" className="block text-xs font-semibold text-slate-700 mb-1.5">
            Your Bid Amount ($ USD)
          </label>
          <div className="relative rounded-lg shadow-sm">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400 font-bold">
              $
            </div>
            <input
              id="bidAmountInput"
              type="number"
              step="0.01"
              min={minNextBid}
              value={bidAmount}
              onChange={(e) => setBidAmount(e.target.value)}
              placeholder={minNextBid.toFixed(2)}
              required
              className="block w-full pl-8 pr-4 py-2.5 rounded-lg border border-slate-300 text-slate-900 font-mono text-base focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Quick Increment Buttons */}
        <div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center">
            <TrendingUp className="w-3 h-3 mr-1" />
            Quick Increments
          </div>
          <div className="grid grid-cols-4 gap-2">
            {[5, 10, 25, 50].map((inc) => (
              <button
                key={inc}
                type="button"
                onClick={() => handleQuickAdd(inc)}
                className="py-1 px-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 rounded-md transition-colors border border-slate-200"
              >
                +${inc}
              </button>
            ))}
          </div>
        </div>

        {/* Submit Bid Button */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full inline-flex items-center justify-center space-x-2 py-3 px-4 rounded-lg text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed shadow transition-all active:scale-[0.99]"
        >
          <Gavel className="w-4 h-4" />
          <span>{isSubmitting ? 'Placing Atomic Bid...' : 'Place Bid Now'}</span>
        </button>

        {/* Anti-Sniping Guarantee Footnote */}
        <div className="pt-2 flex items-center justify-center text-[11px] text-slate-400 space-x-1.5">
          <Zap className="w-3 h-3 text-amber-500" />
          <span>Anti-sniping engine auto-extends 60s if bid in final 30s.</span>
        </div>
      </form>
    </div>
  );
};
