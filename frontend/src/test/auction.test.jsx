import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { AuctionCard } from '../components/auctions/AuctionCard';
import { BidConsole } from '../components/auctions/BidConsole';
import { BidHistoryTable } from '../components/auctions/BidHistoryTable';
import { canCloseAuction, canCancelAuction } from '../utils/auctionActions';
import { AuthProvider } from '../context/AuthContext';
import { WatchlistProvider } from '../context/WatchlistContext';

const mockAuction = {
  id: 101,
  starting_price: 50.0,
  current_highest_bid: 75.0,
  minimum_increment: 5.0,
  total_bids: 3,
  status: 'ACTIVE',
  end_time: new Date(Date.now() + 86400000).toISOString(),
  seconds_remaining: 86400,
  product: {
    id: 1,
    title: 'Vintage Chronograph Watch',
    condition_status: 'LIKE_NEW',
    category: { name: 'Horology' },
    image_url: 'https://example.com/watch.jpg',
    seller_id: 10,
  },
};

describe('Auction Feature Components', () => {
  describe('auction detail management eligibility', () => {
    it('only lets sellers close expired active auctions while admins can force-close active auctions', () => {
      const activeFutureAuction = {
        status: 'ACTIVE',
        is_expired: false,
        seconds_remaining: 3600,
        end_time: new Date(Date.now() + 3600000).toISOString(),
      };
      const activeExpiredAuction = {
        ...activeFutureAuction,
        is_expired: true,
        seconds_remaining: 0,
      };

      expect(canCloseAuction(activeFutureAuction, false)).toBe(false);
      expect(canCloseAuction(activeExpiredAuction, false)).toBe(true);
      expect(canCloseAuction(activeFutureAuction, true)).toBe(true);
    });

    it('keeps seller cancellation aligned with the zero-bid rule', () => {
      const activeWithoutBids = { status: 'ACTIVE', total_bids: 0 };
      const activeWithBids = { status: 'ACTIVE', total_bids: 2 };

      expect(canCancelAuction(activeWithoutBids, false)).toBe(true);
      expect(canCancelAuction(activeWithBids, false)).toBe(false);
      expect(canCancelAuction(activeWithBids, true)).toBe(true);
    });
  });

  describe('AuctionCard', () => {
    it('renders auction card with product title, category, and price', () => {
      render(
        <BrowserRouter>
          <AuthProvider>
            <WatchlistProvider>
              <AuctionCard auction={mockAuction} />
            </WatchlistProvider>
          </AuthProvider>
        </BrowserRouter>
      );

      expect(screen.getByText('Vintage Chronograph Watch')).toBeInTheDocument();
      expect(screen.getByText('Horology')).toBeInTheDocument();
      expect(screen.getByText('$75.00')).toBeInTheDocument();
      expect(screen.getByText(/3 bids/i)).toBeInTheDocument();
    });
  });

  describe('BidConsole', () => {
    it('prompts unauthenticated users to sign in to place a bid', () => {
      render(
        <BrowserRouter>
          <AuthProvider>
            <BidConsole auction={mockAuction} onBidSuccess={vi.fn()} />
          </AuthProvider>
        </BrowserRouter>
      );

      expect(screen.getByText(/Sign In as Buyer/i)).toBeInTheDocument();
    });
  });

  describe('BidHistoryTable', () => {
    it('displays empty state when no bids exist', () => {
      render(<BidHistoryTable bids={[]} total={0} />);
      expect(screen.getByText(/No bids placed yet/i)).toBeInTheDocument();
    });

    it('renders anonymized bidder and formatted amounts', () => {
      const bids = [
        {
          id: 1,
          bid_amount: 75.0,
          bid_time: new Date().toISOString(),
          is_winning_bid: true,
          bidder_username: 'b***r',
          is_own_bid: false,
        },
        {
          id: 2,
          bid_amount: 60.0,
          bid_time: new Date().toISOString(),
          is_winning_bid: false,
          bidder_username: 'e***r',
          is_own_bid: true,
        },
      ];

      render(<BidHistoryTable bids={bids} total={2} />);
      expect(screen.getByText('b***r')).toBeInTheDocument();
      expect(screen.getByText('$75.00')).toBeInTheDocument();
      expect(screen.getByText(/Highest Bid/i)).toBeInTheDocument();
      expect(screen.getByText(/You/i)).toBeInTheDocument();
    });
  });
});
