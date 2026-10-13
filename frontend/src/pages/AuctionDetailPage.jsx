import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Shield,
  ArrowLeft,
  Share2,
  AlertTriangle,
  Lock,
  Trophy,
  RefreshCw,
} from 'lucide-react';
import { auctionsApi } from '../api/auctions';
import { bidsApi } from '../api/bids';
import { useAuth } from '../context/AuthContext';
import { StatusBadge, ConditionBadge } from '../components/common/Badge';
import { CountdownTimer } from '../components/common/CountdownTimer';
import { BidConsole } from '../components/auctions/BidConsole';
import { BidHistoryTable } from '../components/auctions/BidHistoryTable';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { SuccessAlert } from '../components/common/SuccessAlert';
import { getErrorMessage } from '../api/client';
import { canCloseAuction, canCancelAuction } from '../utils/auctionActions';

// Documented polling interval: 8 seconds for live auction updates without WebSockets
const AUCTION_POLL_INTERVAL_MS = 8000;

export const AuctionDetailPage = () => {
  const { id } = useParams();
  const { user, isAdmin } = useAuth();

  const [auction, setAuction] = useState(null);
  const [bidsData, setBidsData] = useState({ items: [], total: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);
  const [isProcessingAction, setIsProcessingAction] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  const fetchAuctionAndBids = useCallback(
    async (showLoading = false) => {
      if (showLoading) setIsLoading(true);
      setError(null);
      try {
        const [auctionRes, bidsRes] = await Promise.all([
          auctionsApi.getAuction(id),
          bidsApi.getAuctionBids(id, 0, 50),
        ]);
        setAuction(auctionRes);
        setBidsData(bidsRes);
      } catch (err) {
        setError(getErrorMessage(err) || 'Failed to retrieve auction details.');
      } finally {
        if (showLoading) setIsLoading(false);
      }
    },
    [id]
  );

  useEffect(() => {
    fetchAuctionAndBids(true);

    // Setup live polling interval for auctions whose timing can change state
    const interval = setInterval(() => {
      // Poll quietly while timing can change the visible lifecycle state.
      if (['ACTIVE', 'SCHEDULED'].includes(auction?.status)) {
        fetchAuctionAndBids(false);
      }
    }, AUCTION_POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [fetchAuctionAndBids, auction?.status]);

  const handleBidPlaced = () => {
    // Refresh immediately to sync highest bid and countdown
    fetchAuctionAndBids(false);
  };

  const handleShare = () => {
    navigator.clipboard?.writeText(window.location.href);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  // Privileged actions for owning seller or administrator
  const isOwner = user && auction?.product && auction.product.seller_id === user.id;
  const canManage = isOwner || isAdmin;
  const showCloseAuction = canManage && canCloseAuction(auction, isAdmin);
  const showCancelAuction = canManage && canCancelAuction(auction, isAdmin);

  const handleCloseAuction = async () => {
    if (!window.confirm('Are you sure you want to close this auction and settle the final winner?')) {
      return;
    }
    setIsProcessingAction(true);
    setError(null);
    try {
      const result = await auctionsApi.closeAuction(auction.id, isAdmin);
      setActionSuccess(`Auction closed successfully! Status: ${result.status}. Final price: $${result.final_price || '0.00'}`);
      fetchAuctionAndBids(false);
    } catch (err) {
      setError(getErrorMessage(err) || 'Failed to close auction.');
    } finally {
      setIsProcessingAction(false);
    }
  };

  const handleCancelAuction = async () => {
    if (!window.confirm('Are you sure you want to cancel this auction? This action cannot be undone.')) {
      return;
    }
    setIsProcessingAction(true);
    setError(null);
    try {
      await auctionsApi.cancelAuction(auction.id);
      setActionSuccess('Auction has been cancelled.');
      fetchAuctionAndBids(false);
    } catch (err) {
      setError(getErrorMessage(err) || 'Failed to cancel auction.');
    } finally {
      setIsProcessingAction(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <LoadingSpinner message="Loading auction details..." />
      </div>
    );
  }

  if (error && !auction) {
    return (
      <div className="max-w-3xl mx-auto my-12 p-8 bg-white rounded-xl border border-rose-200 text-center">
        <AlertTriangle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-slate-800 mb-2">Auction Not Found</h2>
        <p className="text-sm text-slate-600 mb-6">{error}</p>
        <Link
          to="/catalog"
          className="inline-flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Catalog</span>
        </Link>
      </div>
    );
  }

  const product = auction?.product || {};
  const countdownTarget = auction.status === 'SCHEDULED' ? auction.start_time : auction.end_time;
  const countdownLabel = auction.status === 'SCHEDULED' ? 'Starts In' : 'Time Remaining';
  const currentPrice = auction.current_highest_bid !== null && auction.current_highest_bid !== undefined
    ? Number(auction.current_highest_bid)
    : Number(auction.starting_price || 0);

  const fallbackImg =
    'https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?auto=format&fit=crop&w=1200&q=80';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Breadcrumb & Navigation */}
      <div className="flex items-center justify-between">
        <Link
          to="/catalog"
          className="inline-flex items-center text-xs font-semibold text-slate-500 hover:text-indigo-600 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          Back to Catalog
        </Link>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => fetchAuctionAndBids(false)}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
            title="Refresh auction"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleShare}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <Share2 className="w-3.5 h-3.5" />
            <span>{copiedLink ? 'Copied Link!' : 'Share'}</span>
          </button>
        </div>
      </div>

      {actionSuccess && <SuccessAlert message={actionSuccess} onClose={() => setActionSuccess(null)} />}
      {error && <ErrorAlert message={error} onClose={() => setError(null)} />}

      {/* Privileged Seller / Admin Management Banner */}
      {canManage && (
        <div className="bg-slate-900 text-white rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4 border border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-indigo-400">
                {isAdmin ? 'Platform Administration Controls' : 'Listing Owner Controls'}
              </div>
              <div className="text-xs text-slate-300">
                Reserve Price:{' '}
                <span className="font-mono font-bold text-white">
                  {auction.reserve_price !== null ? `$${Number(auction.reserve_price).toFixed(2)}` : 'None (No Reserve)'}
                </span>{' '}
                {auction.reserve_met !== null && (
                  <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold ${auction.reserve_met ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'}`}>
                    {auction.reserve_met ? 'Reserve Met' : 'Reserve Not Met'}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {(showCloseAuction || showCancelAuction) && (
              <>
                {showCloseAuction && (
                  <button
                    onClick={handleCloseAuction}
                    disabled={isProcessingAction}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-colors disabled:opacity-50"
                  >
                    Close & Settle
                  </button>
                )}
                {showCancelAuction && (
                  <button
                    onClick={handleCancelAuction}
                    disabled={isProcessingAction}
                    className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition-colors disabled:opacity-50"
                  >
                    Cancel Auction
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Main 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Product Showcase & Description (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Main Product Image Container */}
          <div className="relative aspect-4/3 w-full bg-slate-100 rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
            <img
              src={product.image_url || fallbackImg}
              alt={product.title}
              onError={(e) => {
                e.target.src = fallbackImg;
              }}
              className="w-full h-full object-cover"
            />
            <div className="absolute top-4 left-4">
              <StatusBadge status={auction.status} />
            </div>
            {product.condition_status && (
              <div className="absolute top-4 right-4">
                <ConditionBadge condition={product.condition_status} />
              </div>
            )}
          </div>

          {/* Product Description & Attributes */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900 border-b border-slate-100 pb-3">
              Lot Description & Item Provenance
            </h3>
            <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
              {product.description || 'No extended description provided for this listing.'}
            </p>

            {/* Seller & Category Specs */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-4 border-t border-slate-100 text-xs">
              <div>
                <span className="text-slate-400 block font-medium">Category</span>
                <span className="font-semibold text-slate-800">{product.category?.name || 'General'}</span>
              </div>
              <div>
                <span className="text-slate-400 block font-medium">Verified Seller</span>
                <span className="font-semibold text-slate-800">{product.seller?.username || 'Verified Seller'}</span>
              </div>
              <div>
                <span className="text-slate-400 block font-medium">Listing ID</span>
                <span className="font-mono text-slate-600">LOT-{auction.id}</span>
              </div>
            </div>
          </div>

          {/* Bid History Table */}
          <BidHistoryTable bids={bidsData.items} total={bidsData.total} />
        </div>

        {/* Right Column: Pricing & Bid Console (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Auction Status & Current Bid Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-5">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs uppercase font-bold tracking-wider text-slate-400">
                  Auction Title
                </span>
                <span className="text-xs text-slate-400 font-medium">
                  {auction.total_bids} {auction.total_bids === 1 ? 'bid' : 'bids'} recorded
                </span>
              </div>
              <h1 className="text-xl sm:text-2xl font-black text-slate-900 leading-snug">
                {product.title}
              </h1>
            </div>

            {/* Countdown Banner */}
            <div>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                {countdownLabel}
              </span>
              <CountdownTimer endTime={countdownTarget} onExpire={() => fetchAuctionAndBids(false)} />
            </div>

            {/* Pricing Section */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <div className="flex items-baseline justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  {auction.total_bids > 0 ? 'Current Highest Bid' : 'Opening Starting Price'}
                </span>
                <span className="text-3xl font-black text-slate-900 font-mono">
                  ${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-200/60">
                <span>Opening Price: ${Number(auction.starting_price || 0).toFixed(2)}</span>
                <span>Minimum Step: +${Number(auction.minimum_increment || 1).toFixed(2)}</span>
              </div>

              {/* Reserve Price Confidentiality Banner */}
              <div className="flex items-center space-x-1.5 text-[11px] text-slate-500 pt-1">
                <Lock className="w-3.5 h-3.5 text-slate-400" />
                {canManage ? (
                  <span>
                    Reserve: ${auction.reserve_price ? Number(auction.reserve_price).toFixed(2) : 'None'} (Confidential to public)
                  </span>
                ) : (
                  <span>Confidential Reserve Enforced — Masked until closing</span>
                )}
              </div>
            </div>

            {/* Completed Winner Announcement */}
            {auction.status === 'COMPLETED' && auction.winner_username && (
              <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl flex items-start space-x-3">
                <Trophy className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold text-purple-900 uppercase tracking-wider">
                    Official Auction Winner
                  </h4>
                  <p className="text-sm font-semibold text-purple-800">
                    Won by <span className="font-bold underline">{auction.winner_username}</span> for $
                    {Number(auction.current_highest_bid).toFixed(2)}
                  </p>
                  <p className="text-[11px] text-purple-600 mt-1">
                    Demo settlement simulated automatically via platform settlement pipeline.
                  </p>
                </div>
              </div>
            )}

            {/* Bid Console */}
            <BidConsole auction={auction} onBidSuccess={handleBidPlaced} />
          </div>
        </div>
      </div>
    </div>
  );
};
