import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { notificationsApi } from '../api/notifications';
import { useAuth } from './AuthContext';

const NotificationContext = createContext(null);

// Documented polling interval: 30 seconds for live notification indicator updates
// (BidSmart uses REST polling; no persistent WebSockets required)
const NOTIFICATION_POLL_INTERVAL_MS = 30000;

export const NotificationProvider = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchUnreadCount = useCallback(async () => {
    if (!isAuthenticated) {
      setUnreadCount(0);
      return;
    }
    try {
      const data = await notificationsApi.getUnreadCount();
      setUnreadCount(data.unread_count || 0);
    } catch (err) {
      // Suppress background polling error from crashing UI
      console.warn('Notification poll skipped:', err.message);
    }
  }, [isAuthenticated]);

  const fetchNotifications = useCallback(async (page = 1, pageSize = 20, unreadOnly = false) => {
    if (!isAuthenticated) return { items: [], total: 0, unread_count: 0 };
    setIsLoading(true);
    try {
      const data = await notificationsApi.listNotifications(page, pageSize, unreadOnly);
      setNotifications(data.items || []);
      setUnreadCount(data.unread_count || 0);
      return data;
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
      return { items: [], total: 0, unread_count: 0 };
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  const markAsRead = useCallback(async (notificationId) => {
    try {
      await notificationsApi.markAsRead(notificationId);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notificationId ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
      return true;
    } catch (err) {
      console.error('Failed to mark notification as read:', err);
      return false;
    }
  }, []);

  const markAllAsRead = useCallback(async () => {
    try {
      await notificationsApi.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
      return true;
    } catch (err) {
      console.error('Failed to mark all as read:', err);
      return false;
    }
  }, []);

  // Set up background polling
  useEffect(() => {
    if (!isAuthenticated) {
      setUnreadCount(0);
      setNotifications([]);
      return;
    }

    // Initial check
    fetchUnreadCount();

    // 30-second polling interval
    const intervalId = setInterval(() => {
      fetchUnreadCount();
    }, NOTIFICATION_POLL_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [isAuthenticated, fetchUnreadCount]);

  const value = {
    unreadCount,
    notifications,
    isLoading,
    fetchUnreadCount,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
  };

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
};

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};
