import apiClient from './client';

export const notificationsApi = {
  // List paginated notifications for current user
  listNotifications: async (page = 1, pageSize = 20, unreadOnly = false) => {
    const response = await apiClient.get('/notifications', {
      params: { page, page_size: pageSize, unread_only: unreadOnly },
    });
    return response.data;
  },

  // Get unread notification count badge
  getUnreadCount: async () => {
    const response = await apiClient.get('/notifications/unread-count');
    return response.data;
  },

  // Mark a single notification as read
  markAsRead: async (notificationId) => {
    const response = await apiClient.patch(`/notifications/${notificationId}/read`);
    return response.data;
  },

  // Mark all notifications as read
  markAllAsRead: async () => {
    const response = await apiClient.post('/notifications/read-all');
    return response.data;
  },
};
