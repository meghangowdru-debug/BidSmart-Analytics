import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ProtectedRoute } from '../components/common/ProtectedRoute';
import { SellerPaymentSetupPanel } from '../components/dashboard/SellerPaymentSetupPanel';
import { apiClient } from '../api/client';

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '../context/AuthContext';

describe('release safety UI', () => {
  it('shows a usable access-denied page for an authenticated disallowed role', () => {
    useAuth.mockReturnValue({
      isAuthenticated: true,
      user: { role: 'BUYER' },
      role: 'BUYER',
      isLoading: false,
    });

    render(
      <MemoryRouter initialEntries={['/dashboard/admin']}>
        <ProtectedRoute allowedRoles={['ADMIN']}>
          <div>Admin workspace</div>
        </ProtectedRoute>
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'Access denied' })).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Return home' }).getAttribute('href')).toBe('/');
    expect(screen.queryByText('Admin workspace')).toBeNull();
  });

  it('explains that disabled seller setup is optional and does not enable payouts', () => {
    render(
      <SellerPaymentSetupPanel
        setup={{
          status: 'DISABLED',
          required: false,
          can_list: true,
          simulated: true,
          payouts_enabled: false,
        }}
      />,
    );

    expect(screen.getByText(/currently disabled and does not block listing/i)).toBeTruthy();
    expect(screen.queryByRole('button', { name: /complete simulated setup/i })).toBeNull();
  });

  it('clears all stored credentials after an unauthorized API response', async () => {
    localStorage.setItem('token', 'expired-access-token');
    localStorage.setItem('user', '{"role":"SELLER"}');
    localStorage.setItem('refresh_token', 'stale-refresh-token');
    const unauthorized = new Event('auth:unauthorized');
    const dispatchEvent = vi.spyOn(window, 'dispatchEvent');
    const originalAdapter = apiClient.defaults.adapter;

    apiClient.defaults.adapter = async (config) => {
      const error = new Error('Unauthorized');
      error.config = config;
      error.response = { status: 401 };
      throw error;
    };

    try {
      await expect(apiClient.get('/test-unauthorized')).rejects.toMatchObject({
        response: { status: 401 },
      });

      expect(localStorage.getItem('token')).toBeNull();
      expect(localStorage.getItem('user')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
      expect(dispatchEvent).toHaveBeenCalledWith(expect.objectContaining({
        type: unauthorized.type,
      }));
    } finally {
      apiClient.defaults.adapter = originalAdapter;
      dispatchEvent.mockRestore();
      localStorage.clear();
    }
  });
});
