import React, { useState, useEffect } from 'react';
import { Clock } from 'lucide-react';
import { parseAuctionDateMs } from '../../utils/auctionActions';

export const CountdownTimer = ({ endTime, onExpire, compact = false, expiredLabel = 'Auction Ended' }) => {
  const [timeLeft, setTimeLeft] = useState(() => calculateTimeLeft(endTime));

  function calculateTimeLeft(target) {
    if (!target) return { totalSeconds: 0, days: 0, hours: 0, minutes: 0, seconds: 0, isExpired: true };

    const end = parseAuctionDateMs(target);
    const now = Date.now();
    const diff = Math.max(0, end - now);

    const totalSeconds = Math.floor(diff / 1000);
    const days = Math.floor(totalSeconds / (3600 * 24));
    const hours = Math.floor((totalSeconds % (3600 * 24)) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    return {
      totalSeconds,
      days,
      hours,
      minutes,
      seconds,
      isExpired: totalSeconds <= 0,
    };
  }

  useEffect(() => {
    // Initial calculate
    const initial = calculateTimeLeft(endTime);
    setTimeLeft(initial);

    if (initial.isExpired) {
      if (onExpire) onExpire();
      return;
    }

    const timer = setInterval(() => {
      const remaining = calculateTimeLeft(endTime);
      setTimeLeft(remaining);

      if (remaining.isExpired) {
        clearInterval(timer);
        if (onExpire) onExpire();
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [endTime, onExpire]);

  if (timeLeft.isExpired) {
    return (
      <span className="inline-flex items-center text-rose-600 font-semibold text-xs tracking-wide">
        <Clock className="w-3.5 h-3.5 mr-1" />
        {expiredLabel}
      </span>
    );
  }

  const isUrgent = timeLeft.totalSeconds <= 300; // < 5 minutes
  const isCritical = timeLeft.totalSeconds <= 60; // < 60s (Anti-sniping zone)

  const pad = (n) => String(n).padStart(2, '0');

  if (compact) {
    let formatted = '';
    if (timeLeft.days > 0) {
      formatted = `${timeLeft.days}d ${timeLeft.hours}h left`;
    } else if (timeLeft.hours > 0) {
      formatted = `${timeLeft.hours}h ${pad(timeLeft.minutes)}m left`;
    } else {
      formatted = `${pad(timeLeft.minutes)}m ${pad(timeLeft.seconds)}s left`;
    }

    return (
      <span
        className={`inline-flex items-center text-xs font-semibold ${
          isCritical
            ? 'text-rose-600 animate-pulse'
            : isUrgent
            ? 'text-amber-600'
            : 'text-slate-600'
        }`}
      >
        <Clock className="w-3.5 h-3.5 mr-1" />
        {formatted}
      </span>
    );
  }

  return (
    <div
      className={`flex items-center space-x-1.5 p-2 rounded-lg border text-sm font-mono ${
        isCritical
          ? 'bg-rose-50 border-rose-300 text-rose-700 animate-pulse'
          : isUrgent
          ? 'bg-amber-50 border-amber-300 text-amber-700'
          : 'bg-slate-50 border-slate-200 text-slate-700'
      }`}
    >
      <Clock className="w-4 h-4 mr-0.5" />
      {timeLeft.days > 0 && (
        <>
          <span className="font-bold">{timeLeft.days}</span>
          <span className="text-xs text-slate-500">d</span>
        </>
      )}
      <span className="font-bold">{pad(timeLeft.hours)}</span>
      <span className="text-xs text-slate-500">h</span>
      <span>:</span>
      <span className="font-bold">{pad(timeLeft.minutes)}</span>
      <span className="text-xs text-slate-500">m</span>
      <span>:</span>
      <span className="font-bold">{pad(timeLeft.seconds)}</span>
      <span className="text-xs text-slate-500">s</span>
      {isCritical && (
        <span className="ml-2 text-xs font-sans font-medium text-rose-600 bg-rose-100 px-1.5 py-0.5 rounded">
          Snipe Buffer Active
        </span>
      )}
    </div>
  );
};
