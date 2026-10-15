import apiClient from './client';

export const paymentsApi = {
  listWonAuctions: async (params = {}) => {
    const response = await apiClient.get('/payments/me/won-auctions', { params });
    return response.data;
  },
  createOrder: async (auctionId) => {
    const response = await apiClient.post(`/payments/auctions/${auctionId}/orders`);
    return response.data;
  },
  verifyPayment: async (payment) => {
    const response = await apiClient.post('/payments/verify', payment);
    return response.data;
  },
  listMyTransactions: async (params = {}) => {
    const response = await apiClient.get('/payments/me/transactions', { params });
    return response.data;
  },
  listMySellerTransactions: async (params = {}) => {
    const response = await apiClient.get('/payments/me/seller-transactions', { params });
    return response.data;
  },
  listAdminTransactions: async (params = {}) => {
    const response = await apiClient.get('/payments/admin/transactions', { params });
    return response.data;
  },
};
