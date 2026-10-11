import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';

const WatchlistContext = createContext(null);

export const WatchlistProvider = ({ children }) => {
  const { user } = useAuth();
  const userId = user?.id || 'guest';
  const storageKey = `bidsmart_watchlist_${userId}`;

  const [watchlistIds, setWatchlistIds] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Reload watchlist whenever active user changes
  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      setWatchlistIds(saved ? JSON.parse(saved) : []);
    } catch {
      setWatchlistIds([]);
    }
  }, [storageKey]);

  // Persist changes to localStorage
  const persistWatchlist = (ids) => {
    setWatchlistIds(ids);
    try {
      localStorage.setItem(storageKey, JSON.stringify(ids));
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
      const numId = Number(auctionId);
      if (!watchlistIds.includes(numId)) {
        persistWatchlist([...watchlistIds, numId]);
      }
    },
    [watchlistIds, storageKey]
  );

  const removeFromWatchlist = useCallback(
    (auctionId) => {
      const numId = Number(auctionId);
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
