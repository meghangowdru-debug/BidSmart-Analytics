import apiClient from './client';

export const usersApi = {
  // Current user profile
  getMe: async () => {
    const response = await apiClient.get('/users/me');
    return response.data;
  },

  // Update current user profile and/or password
  updateMe: async (userData) => {
    const response = await apiClient.put('/users/me', userData);
    return response.data;
  },

  // Admin: list users with search and pagination
  listUsers: async (page = 1, pageSize = 20, role = null, status = null) => {
    const params = { page, page_size: pageSize };
    if (role) params.role = role;
    if (status) params.status = status;
    const response = await apiClient.get('/users', { params });
    return response.data;
  },

  // Admin: update user role
  updateUserRole: async (userId, roleName) => {
    const response = await apiClient.patch(`/users/${userId}/role`, { role: roleName });
    return response.data;
  },

  // Admin: update user status (ACTIVE / SUSPENDED)
  updateUserStatus: async (userId, userStatus) => {
    const response = await apiClient.patch(`/users/${userId}/status`, { status: userStatus });
    return response.data;
  },

  // Role portal checks
  checkBuyerPortal: async () => {
    const response = await apiClient.get('/users/portal/buyer-only');
    return response.data;
  },

  checkSellerPortal: async () => {
    const response = await apiClient.get('/users/portal/seller-only');
    return response.data;
  },

  checkAdminPortal: async () => {
    const response = await apiClient.get('/users/portal/admin-only');
    return response.data;
  },
};
