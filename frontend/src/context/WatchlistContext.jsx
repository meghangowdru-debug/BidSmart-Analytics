import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';

const WatchlistContext = createContext(null);

const toAuctionId = (value) => {
  if (typeof value !== 'number' && typeof value !== 'string') return null;
  if (typeof value === 'string' && value.trim() === '') return null;

  const id = Number(value);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
};

const normalizeWatchlistIds = (value) => {
  if (!Array.isArray(value)) return [];

  return [...new Set(value.map(toAuctionId).filter((id) => id !== null))];
};

const readWatchlist = (storageKey) => {
  try {
    const saved = localStorage.getItem(storageKey);
    return saved ? normalizeWatchlistIds(JSON.parse(saved)) : [];
  } catch {
    return [];
  }
};

export const WatchlistProvider = ({ children }) => {
  const { user } = useAuth();
  const userId = user?.id || 'guest';
  const storageKey = `bidsmart_watchlist_${userId}`;

  const [watchlistIds, setWatchlistIds] = useState(() => readWatchlist(storageKey));

  // Reload watchlist whenever active user changes
  useEffect(() => {
    setWatchlistIds(readWatchlist(storageKey));
  }, [storageKey]);

  // Persist changes to localStorage
  const persistWatchlist = (ids) => {
    const normalizedIds = normalizeWatchlistIds(ids);
    setWatchlistIds(normalizedIds);
    try {
      localStorage.setItem(storageKey, JSON.stringify(normalizedIds));
    } catch (e) {
      console.warn('Failed to persist watchlist to local storage:', e);
    }
  };

  const isWatchlisted = useCallback(
    (auctionId) => {
      const numId = Number(auctionId);
      return watchlistIds.includes(numId);
    },
    [watchlistIds]
  );

  const addToWatchlist = useCallback(
    (auctionId) => {
      const numId = toAuctionId(auctionId);
      if (numId !== null && !watchlistIds.includes(numId)) {
        persistWatchlist([...watchlistIds, numId]);
      }
    },
    [watchlistIds, storageKey]
  );

  const removeFromWatchlist = useCallback(
    (auctionId) => {
      const numId = toAuctionId(auctionId);
      if (numId === null) return;
      persistWatchlist(watchlistIds.filter((id) => id !== numId));
    },
    [watchlistIds, storageKey]
  );

  const toggleWatchlist = useCallback(
    (auctionId) => {
      const numId = Number(auctionId);
      if (watchlistIds.includes(numId)) {
        removeFromWatchlist(numId);
      } else {
        addToWatchlist(numId);
      }
    },
    [watchlistIds, addToWatchlist, removeFromWatchlist]
  );

  const value = {
    watchlistIds,
    isWatchlisted,
    addToWatchlist,
    removeFromWatchlist,
    toggleWatchlist,
  };

  return <WatchlistContext.Provider value={value}>{children}</WatchlistContext.Provider>;
};

export const useWatchlist = () => {
  const context = useContext(WatchlistContext);
  if (!context) {
    throw new Error('useWatchlist must be used within a WatchlistProvider');
  }
  return context;
};
