import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { LoadingSpinner } from './LoadingSpinner';

export const ProtectedRoute = ({ children, allowedRoles = [] }) => {
  const { isAuthenticated, user, role, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <LoadingSpinner message="Verifying session credentials..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles.length > 0 && !allowedRoles.includes(role)) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-8 bg-rose-50 border border-rose-200 rounded-xl text-center">
        <h2 className="text-xl font-bold text-rose-800 mb-2">Access Denied (HTTP 403 Forbidden)</h2>
        <p className="text-rose-600 mb-6">
          Your current account role is <span className="font-semibold">{role}</span>, which lacks authorization
          to access this workspace. This resource requires: {allowedRoles.join(' or ')}.
        </p>
        <div className="flex justify-center space-x-4">
          <Navigate to="/" replace />
        </div>
      </div>
    );
  }

  return children;
};
