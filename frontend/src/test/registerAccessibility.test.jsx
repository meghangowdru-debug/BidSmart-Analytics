import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RegisterPage } from '../pages/RegisterPage';
import { useAuth } from '../context/AuthContext';

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }));

describe('RegisterPage accessibility', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({ register: vi.fn() });
  });

  const renderRegisterPage = () =>
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    );

  it('associates all registration labels with their inputs', () => {
    renderRegisterPage();

    expect(screen.getByLabelText('Username')).toHaveAttribute('id', 'register-username');
    expect(screen.getByLabelText('Full Name')).toHaveAttribute('id', 'register-full-name');
    expect(screen.getByLabelText('Email Address')).toHaveAttribute('id', 'register-email');
    expect(screen.getByLabelText('Phone (Optional)')).toHaveAttribute('id', 'register-phone');
    expect(screen.getByLabelText('Password')).toHaveAttribute('id', 'register-password');
  });

  it('provides appropriate browser autocomplete hints', () => {
    renderRegisterPage();

    expect(screen.getByLabelText('Username')).toHaveAttribute('autocomplete', 'username');
    expect(screen.getByLabelText('Full Name')).toHaveAttribute('autocomplete', 'name');
    expect(screen.getByLabelText('Email Address')).toHaveAttribute('autocomplete', 'email');
    expect(screen.getByLabelText('Phone (Optional)')).toHaveAttribute('autocomplete', 'tel');
    expect(screen.getByLabelText('Password')).toHaveAttribute('autocomplete', 'new-password');
  });

  it('exposes Buyer and Seller as a keyboard-operable radio group with selected state', () => {
    renderRegisterPage();

    const group = screen.getByRole('group', { name: 'Select Your Account Type' });
    const buyer = within(group).getByRole('radio', { name: /Buyer/ });
    const seller = within(group).getByRole('radio', { name: /Seller/ });

    expect(buyer).toBeChecked();
    expect(seller).not.toBeChecked();
    expect(buyer.name).toBe('role');
    expect(seller.name).toBe('role');

    seller.focus();
    expect(document.activeElement).toBe(seller);
    fireEvent.click(seller);

    expect(seller).toBeChecked();
    expect(buyer).not.toBeChecked();
    expect(screen.getByTestId('seller-payment-setup-notice')).toBeVisible();
  });
});
