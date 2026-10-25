import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '../api/auth';
import { getErrorMessage } from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem('token') || null);
  const [user, setUser] = useState(() => {
    try {
      const savedUser = localStorage.getItem('user');
      return savedUser ? JSON.parse(savedUser) : null;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState(true);

  // Synchronize user profile on mount if token exists
  useEffect(() => {
    let isMounted = true;
    const fetchCurrentUser = async () => {
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        const freshUser = await authApi.getMe();
        if (isMounted) {
          setUser(freshUser);
          localStorage.setItem('user', JSON.stringify(freshUser));
        }
      } catch (err) {
        if (isMounted) {
          // Token is likely expired or invalid
          setToken(null);
          setUser(null);
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchCurrentUser();

    // Listen for global 401 unauthorized events
    const handleUnauthorized = () => {
      setToken(null);
      setUser(null);
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);

    return () => {
      isMounted = false;
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, [token]);

  const login = useCallback(async (credentials) => {
    try {
      const data = await authApi.login(credentials);
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token);
      }
      setToken(data.access_token);
      setUser(data.user);
      return { success: true, user: data.user };
    } catch (err) {
      return {
        success: false,
        error: getErrorMessage(err),
      };
    }
  }, []);

  const register = useCallback(async (userData) => {
    try {
      const newUser = await authApi.register(userData);
      // Automatically attempt login after successful registration
      return await login({
        username_or_email: userData.username,
        password: userData.password,
      });
    } catch (err) {
      return {
        success: false,
        error: getErrorMessage(err),
      };
    }
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('refresh_token');
    setToken(null);
    setUser(null);
  }, []);

  const updateUser = useCallback((updatedUserData) => {
    setUser(updatedUserData);
    localStorage.setItem('user', JSON.stringify(updatedUserData));
  }, []);

  const role = user?.role ? user.role.toUpperCase() : null;
  const isBuyer = role === 'BUYER';
  const isSeller = role === 'SELLER';
  const isAdmin = role === 'ADMIN';

  const value = {
    token,
    user,
    role,
    isAuthenticated: !!token && !!user,
    isBuyer,
    isSeller,
    isAdmin,
    isLoading,
    login,
    register,
    logout,
    updateUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
