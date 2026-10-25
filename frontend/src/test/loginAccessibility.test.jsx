import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LoginPage } from '../pages/LoginPage';
import { useAuth } from '../context/AuthContext';

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }));

describe('LoginPage accessibility', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({ login: vi.fn() });
  });

  const renderLoginPage = () =>
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

  it('associates each login label with its input', () => {
    renderLoginPage();

    expect(screen.getByLabelText('Username or Email Address')).toHaveAttribute(
      'id',
      'username-or-email',
    );
    expect(screen.getByLabelText('Password')).toHaveAttribute('id', 'password');
  });

  it('provides browser autocomplete hints for username and current password', () => {
    renderLoginPage();

    expect(screen.getByLabelText('Username or Email Address')).toHaveAttribute(
      'autocomplete',
      'username',
    );
    expect(screen.getByLabelText('Password')).toHaveAttribute(
      'autocomplete',
      'current-password',
    );
  });
});
