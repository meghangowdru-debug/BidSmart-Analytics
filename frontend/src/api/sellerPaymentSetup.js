import apiClient from './client';

export const sellerPaymentSetupApi = {
  getStatus: async () => {
    const response = await apiClient.get('/sellers/me/payment-setup');
    return response.data;
  },
  completeDemoSetup: async () => {
    const response = await apiClient.post('/sellers/me/payment-setup/demo', {
      acknowledge_simulated: true,
    });
    return response.data;
  },
};
