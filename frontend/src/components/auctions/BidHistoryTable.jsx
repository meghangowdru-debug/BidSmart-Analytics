import React from 'react';
import { Trophy, User, Clock } from 'lucide-react';

export const BidHistoryTable = ({ bids = [], total = 0 }) => {
  if (!bids || bids.length === 0) {
    return (
      <div className="p-8 text-center text-slate-500 bg-slate-50 rounded-xl border border-dashed border-slate-200">
        <Clock className="w-6 h-6 mx-auto mb-2 text-slate-400" />
        <p className="text-sm font-medium">No bids placed yet.</p>
        <p className="text-xs text-slate-400">Be the first to place an opening bid on this auction!</p>
      </div>
    );
  }

  const formatDate = (dateStr) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="overflow-hidden border border-slate-200 rounded-xl bg-white shadow-sm">
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
          Chronological Bid History ({total || bids.length})
        </h4>
        <span className="text-[11px] text-slate-400">Pessimistic Row-Locked Log</span>
      </div>

      <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
        {bids.map((b, index) => (
          <div
            key={b.id || index}
            className={`px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors ${
              b.is_winning_bid ? 'bg-amber-50/50' : ''
            }`}
          >
            {/* Bidder & Tags */}
            <div className="flex items-center space-x-3">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                  b.is_winning_bid
                    ? 'bg-amber-100 text-amber-700'
                    : b.is_own_bid
                    ? 'bg-indigo-100 text-indigo-700'
                    : 'bg-slate-100 text-slate-600'
                }`}
              >
                {b.is_winning_bid ? <Trophy className="w-4 h-4" /> : <User className="w-4 h-4" />}
              </div>

              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-semibold text-slate-800 font-mono">
                    {b.bidder_username || 'Anonymous'}
                  </span>
                  {b.is_own_bid && (
                    <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-indigo-100 text-indigo-700">
                      You
                    </span>
                  )}
                  {b.is_winning_bid && (
                    <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 flex items-center">
                      <Trophy className="w-2.5 h-2.5 mr-0.5" />
                      Highest Bid
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-400">{formatDate(b.bid_time)}</div>
              </div>
            </div>

            {/* Amount */}
            <div className="text-right">
              <span className="text-sm font-bold font-mono text-slate-900">
                ${Number(b.bid_amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
