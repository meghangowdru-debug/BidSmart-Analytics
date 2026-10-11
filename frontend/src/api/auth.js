import apiClient from './client';

export const authApi = {
  // Login with username or email + password
  login: async (credentials) => {
    const response = await apiClient.post('/auth/login', {
      username_or_email: credentials.username_or_email,
      password: credentials.password,
    });
    return response.data;
  },

  // Register a new BUYER or SELLER
  register: async (userData) => {
    const response = await apiClient.post('/auth/register', {
      username: userData.username,
      email: userData.email,
      password: userData.password,
      full_name: userData.full_name,
      phone: userData.phone || undefined,
      role: userData.role || 'BUYER',
    });
    return response.data;
  },

  // Refresh access token
  refreshToken: async (refreshToken) => {
    const response = await apiClient.post('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  // Get current user profile
  getMe: async () => {
    const response = await apiClient.get('/users/me');
    return response.data;
  },
};
