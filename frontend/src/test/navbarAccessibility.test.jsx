import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Navbar } from '../components/common/Navbar';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }));
vi.mock('../context/NotificationContext', () => ({ useNotifications: vi.fn() }));

const CurrentPath = () => {
  const location = useLocation();
  return <output aria-label="Current page">{location.pathname}</output>;
};

const renderNavbar = () =>
  render(
    <MemoryRouter initialEntries={['/']}>
      <Navbar />
      <CurrentPath />
    </MemoryRouter>,
  );

describe('Navbar mobile navigation accessibility', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
      role: null,
      logout: vi.fn(),
      isBuyer: false,
      isSeller: false,
      isAdmin: false,
    });
    useNotifications.mockReturnValue({ unreadCount: 0 });
  });

  it('associates the toggle with a labelled menu and exposes its collapsed state', () => {
    renderNavbar();

    const toggle = screen.getByRole('button', { name: 'Toggle navigation menu' });
    const menu = document.getElementById('mobile-navigation');

    expect(toggle).toHaveAttribute('aria-controls', 'mobile-navigation');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(menu.tagName).toBe('NAV');
    expect(menu).toHaveAttribute('aria-label', 'Mobile navigation');
    expect(menu).toHaveAttribute('id', 'mobile-navigation');
    expect(menu).toHaveAttribute('hidden');
    expect(toggle.tagName).toBe('BUTTON');
    expect(toggle.tabIndex).toBe(0);
  });

  it('opens the mobile menu and exposes the expanded state', () => {
    renderNavbar();

    const toggle = screen.getByRole('button', { name: 'Toggle navigation menu' });
    fireEvent.click(toggle);

    const menu = screen.getByRole('navigation', { name: 'Mobile navigation' });
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(menu).toBeVisible();
    expect(within(menu).getByRole('link', { name: 'Catalog' })).toBeVisible();
  });

  it('keeps native links keyboard-focusable and closes the menu after selecting a destination', () => {
    renderNavbar();

    const toggle = screen.getByRole('button', { name: 'Toggle navigation menu' });
    toggle.focus();
    expect(document.activeElement).toBe(toggle);
    fireEvent.click(toggle);

    const menu = screen.getByRole('navigation', { name: 'Mobile navigation' });
    const catalogLink = within(menu).getByRole('link', { name: 'Catalog' });
    catalogLink.focus();
    expect(document.activeElement).toBe(catalogLink);
    expect(catalogLink.tabIndex).toBe(0);

    fireEvent.click(catalogLink);

    expect(screen.getByLabelText('Current page')).toHaveTextContent('/catalog');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(menu).toHaveAttribute('hidden');
  });
});
