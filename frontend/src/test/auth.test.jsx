import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { AuthProvider, useAuth } from '../context/AuthContext';

const ConsumerComponent = () => {
  const { isAuthenticated, user, role, logout } = useAuth();
  return (
    <div>
      <span data-testid="auth-status">{isAuthenticated ? 'LOGGED_IN' : 'GUEST'}</span>
      <span data-testid="user-role">{role || 'NONE'}</span>
      <button onClick={logout}>Log Out</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('initializes as guest when local storage has no token', () => {
    render(
      <AuthProvider>
        <ConsumerComponent />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth-status')).toHaveTextContent('GUEST');
    expect(screen.getByTestId('user-role')).toHaveTextContent('NONE');
  });

  it('restores user from local storage when available', () => {
    localStorage.setItem('token', 'fake_jwt_token');
    localStorage.setItem(
      'user',
      JSON.stringify({ id: 1, username: 'testbuyer', role: 'BUYER' })
    );

    render(
      <AuthProvider>
        <ConsumerComponent />
      </AuthProvider>
    );

    expect(screen.getByTestId('user-role')).toHaveTextContent('BUYER');
  });
});
