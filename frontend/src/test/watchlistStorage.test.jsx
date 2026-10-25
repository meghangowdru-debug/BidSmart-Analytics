import React from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { WatchlistProvider, useWatchlist } from '../context/WatchlistContext';
import { useAuth } from '../context/AuthContext';

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }));

const STORAGE_KEY = 'bidsmart_watchlist_7';

const WatchlistConsumer = () => {
  const { watchlistIds, addToWatchlist, removeFromWatchlist } = useWatchlist();

  return (
    <div>
      <output data-testid="watchlist-ids">{JSON.stringify(watchlistIds)}</output>
      <button onClick={() => addToWatchlist('12')}>Add 12</button>
      <button onClick={() => addToWatchlist('invalid')}>Add invalid ID</button>
      <button onClick={() => removeFromWatchlist('invalid')}>Remove invalid ID</button>
    </div>
  );
};

const renderWatchlist = () =>
  render(
    <WatchlistProvider>
      <WatchlistConsumer />
    </WatchlistProvider>,
  );

describe('WatchlistContext storage', () => {
  beforeEach(() => {
    localStorage.clear();
    useAuth.mockReturnValue({ user: { id: 7 } });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('normalizes saved IDs to unique positive safe integers', () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(['12', 12, 0, -3, 'not-an-id', '', 2.5, true, Number.MAX_SAFE_INTEGER + 1, 4]),
    );

    renderWatchlist();

    expect(screen.getByTestId('watchlist-ids')).toHaveTextContent('[12,4]');
  });

  it('uses an empty watchlist for malformed JSON and non-array saved values', () => {
    localStorage.setItem(STORAGE_KEY, '{invalid json');
    const { unmount } = renderWatchlist();
    expect(screen.getByTestId('watchlist-ids')).toHaveTextContent('[]');

    unmount();
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ id: 12 }));
    renderWatchlist();

    expect(screen.getByTestId('watchlist-ids')).toHaveTextContent('[]');
  });

  it('falls back to an empty watchlist when storage cannot be read', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('Storage unavailable');
    });

    renderWatchlist();

    expect(screen.getByTestId('watchlist-ids')).toHaveTextContent('[]');
  });

  it('ignores invalid additions and removals while persisting normalized IDs', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(['3', 3, -1]));
    renderWatchlist();

    fireEvent.click(screen.getByRole('button', { name: 'Add invalid ID' }));
    fireEvent.click(screen.getByRole('button', { name: 'Remove invalid ID' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add 12' }));

    expect(screen.getByTestId('watchlist-ids')).toHaveTextContent('[3,12]');
    expect(localStorage.getItem(STORAGE_KEY)).toBe('[3,12]');
  });

  it('keeps in-memory updates when storage writes fail', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('Storage unavailable');
    });
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    renderWatchlist();

    act(() => fireEvent.click(screen.getByRole('button', { name: 'Add 12' })));

    expect(screen.getByTestId('watchlist-ids')).toHaveTextContent('[12]');
    expect(console.warn).toHaveBeenCalledWith(
      'Failed to persist watchlist to local storage:',
      expect.any(Error),
    );
  });
});
