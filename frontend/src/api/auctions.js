import apiClient from './client';

export const auctionsApi = {
  // Public catalog browsing with search, filter, and sort
  listAuctions: async (params = {}) => {
    const response = await apiClient.get('/auctions', { params });
    return response.data;
  },

  // Get single auction details (reserve price unmasked only for owner/admin)
  getAuction: async (auctionId) => {
    const response = await apiClient.get(`/auctions/${auctionId}`);
    return response.data;
  },

  // Seller: list auctions owned by authenticated seller
  listMyAuctions: async (params = {}) => {
    const response = await apiClient.get('/auctions/seller/me', { params });
    return response.data;
  },

  // Seller: create auction for existing product
  createAuction: async (payload) => {
    const response = await apiClient.post('/auctions', payload);
    return response.data;
  },

  // Seller: update scheduled/active auction parameters
  updateAuction: async (auctionId, payload) => {
    const response = await apiClient.put(`/auctions/${auctionId}`, payload);
    return response.data;
  },

  // Seller/Admin: cancel an auction
  cancelAuction: async (auctionId) => {
    const response = await apiClient.post(`/auctions/${auctionId}/cancel`);
    return response.data;
  },

  // Seller/Admin: close a single auction and settle winner
  closeAuction: async (auctionId, force = false) => {
    const response = await apiClient.post(`/auctions/${auctionId}/close`, null, {
      params: { force },
    });
    return response.data;
  },

  // Seller/Admin: batch close expired auctions
  batchCloseExpired: async (sellerId = null) => {
    const params = sellerId ? { seller_id: sellerId } : {};
    const response = await apiClient.post('/auctions/close-expired', null, { params });
    return response.data;
  },
};
