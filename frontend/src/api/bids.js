import apiClient from './client';

export const bidsApi = {
  // Buyer: submit atomic bid on active auction
  submitBid: async (auctionId, bidAmount) => {
    const response = await apiClient.post(`/auctions/${auctionId}/bids`, {
      bid_amount: Number(bidAmount),
    });
    return response.data;
  },

  // Chronological bid history for an auction (anonymized for public/buyers)
  getAuctionBids: async (auctionId, skip = 0, limit = 50) => {
    const response = await apiClient.get(`/auctions/${auctionId}/bids`, {
      params: { skip, limit },
    });
    return response.data;
  },

  // Buyer: list authenticated user's bidding history
  listMyBids: async (skip = 0, limit = 50) => {
    const response = await apiClient.get('/bids/me', {
      params: { skip, limit },
    });
    return response.data;
  },
};
