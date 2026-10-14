import apiClient from './client';

export const analyticsApi = {
  getAnalytics: async (filters = {}) => {
    const response = await apiClient.get('/analytics', { params: filters });
    return response.data;
  },
};
