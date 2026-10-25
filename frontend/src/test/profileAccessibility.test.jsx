import React from 'react';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ProfilePage } from '../pages/ProfilePage';
import { useAuth } from '../context/AuthContext';

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }));

describe('ProfilePage accessibility', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({
      user: {
        username: 'buyer1',
        full_name: 'Test Buyer',
        email: 'buyer@example.com',
        phone: '5550100',
        role: 'BUYER',
        status: 'ACTIVE',
        created_at: '2025-01-01T00:00:00Z',
      },
      updateUser: vi.fn(),
    });
  });

  it('associates profile and password labels with their fields', () => {
    render(<ProfilePage />);

    expect(screen.getByLabelText('Full Legal / Display Name')).toHaveAttribute(
      'id',
      'profile-full-name',
    );
    expect(screen.getByLabelText('Phone Number')).toHaveAttribute('id', 'profile-phone');
    expect(screen.getByLabelText('Current Password')).toHaveAttribute(
      'id',
      'profile-current-password',
    );
    expect(screen.getByLabelText('New Password (Min 8 chars)')).toHaveAttribute(
      'id',
      'profile-new-password',
    );
  });

  it('provides appropriate browser autocomplete hints', () => {
    render(<ProfilePage />);

    expect(screen.getByLabelText('Full Legal / Display Name')).toHaveAttribute('autocomplete', 'name');
    expect(screen.getByLabelText('Phone Number')).toHaveAttribute('autocomplete', 'tel');
    expect(screen.getByLabelText('Current Password')).toHaveAttribute(
      'autocomplete',
      'current-password',
    );
    expect(screen.getByLabelText('New Password (Min 8 chars)')).toHaveAttribute(
      'autocomplete',
      'new-password',
    );
  });
});
