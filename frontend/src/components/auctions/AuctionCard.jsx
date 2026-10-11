import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Heart, Tag, Eye } from 'lucide-react';
import { StatusBadge, ConditionBadge } from '../common/Badge';
import { CountdownTimer } from '../common/CountdownTimer';
import { useWatchlist } from '../../context/WatchlistContext';
import { useAuth } from '../../context/AuthContext';

export const AuctionCard = ({ auction }) => {
  const { isBuyer } = useAuth();
  const { isWatchlisted, toggleWatchlist } = useWatchlist();
  const [imageError, setImageError] = useState(false);

  const product = auction.product || {};
  const currentPrice = auction.current_highest_bid !== null && auction.current_highest_bid !== undefined
    ? Number(auction.current_highest_bid)
    : Number(auction.starting_price || 0);

  const watchlisted = isWatchlisted(auction.id);

  // Fallback image URL placeholder
  const fallbackImg =
    'https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?auto=format&fit=crop&w=600&q=80';
  const displayImage = imageError || !product.image_url ? fallbackImg : product.image_url;

  return (
    <div className="group bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md hover:border-indigo-200 transition-all flex flex-col h-full">
      {/* Product Image & Badges Header */}
      <div className="relative aspect-4/3 w-full bg-slate-100 overflow-hidden">
        <img
          src={displayImage}
          alt={product.title || 'Auction lot'}
          onError={() => setImageError(true)}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          loading="lazy"
        />

        {/* Status Badge in Top Left */}
        <div className="absolute top-2.5 left-2.5">
          <StatusBadge status={auction.status} />
        </div>

        {/* Watchlist Heart Button in Top Right (Buyer Only) */}
        {isBuyer && (
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              toggleWatchlist(auction.id);
            }}
            className={`absolute top-2.5 right-2.5 p-2 rounded-full backdrop-blur-md transition-transform active:scale-90 ${
              watchlisted
                ? 'bg-rose-50 text-rose-600 shadow-sm'
                : 'bg-white/80 text-slate-500 hover:text-rose-600 hover:bg-white'
            }`}
            title={watchlisted ? 'Remove from Watchlist' : 'Add to Watchlist'}
            aria-label="Toggle watchlist"
          >
            <Heart className={`w-4 h-4 ${watchlisted ? 'fill-current' : ''}`} />
          </button>
        )}

        {/* Category Pill in Bottom Left */}
        {product.category && (
          <div className="absolute bottom-2.5 left-2.5">
            <span className="inline-flex items-center text-[11px] font-medium px-2 py-0.5 rounded-md bg-slate-900/70 backdrop-blur text-white">
              <Tag className="w-3 h-3 mr-1" />
              {product.category.name}
            </span>
          </div>
        )}
      </div>

      {/* Content Section */}
      <div className="p-4 flex flex-col flex-1">
        {/* Title & Condition */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <Link
            to={`/auctions/${auction.id}`}
            className="font-semibold text-slate-900 text-sm hover:text-indigo-600 transition-colors line-clamp-2 leading-snug flex-1"
          >
            {product.title || `Auction #${auction.id}`}
          </Link>
          {product.condition_status && (
            <div className="flex-shrink-0">
              <ConditionBadge condition={product.condition_status} />
            </div>
          )}
        </div>

        {/* Pricing Info */}
        <div className="mt-auto pt-3 border-t border-slate-100 flex items-end justify-between">
          <div>
            <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold block">
              {auction.total_bids > 0 ? 'Current Bid' : 'Starting Price'}
            </span>
            <div className="text-lg font-bold text-slate-900">
              ${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>

          <div className="text-right">
            <span className="text-xs text-slate-500 font-medium block">
              {auction.total_bids || 0} {auction.total_bids === 1 ? 'bid' : 'bids'}
            </span>
            <CountdownTimer endTime={auction.end_time} compact />
          </div>
        </div>

        {/* View Details CTA */}
        <Link
          to={`/auctions/${auction.id}`}
          className="mt-3.5 w-full inline-flex items-center justify-center space-x-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-800 hover:bg-indigo-600 hover:text-white transition-colors"
        >
          <Eye className="w-3.5 h-3.5" />
          <span>View Auction Details</span>
        </Link>
      </div>
    </div>
  );
};
