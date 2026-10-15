import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { SellerPaymentSetupPanel } from '../components/dashboard/SellerPaymentSetupPanel';
import { SellerDashboardPage } from '../pages/SellerDashboardPage';
import { RegisterPage } from '../pages/RegisterPage';

const mocks = vi.hoisted(() => ({
  getStatus: vi.fn(),
  completeDemoSetup: vi.fn(),
  listMyAuctions: vi.fn(),
  listMyProducts: vi.fn(),
  listCategories: vi.fn(),
}));

vi.mock('../api/sellerPaymentSetup', () => ({
  sellerPaymentSetupApi: { getStatus: mocks.getStatus, completeDemoSetup: mocks.completeDemoSetup },
}));
vi.mock('../api/auctions', () => ({
  auctionsApi: { listMyAuctions: mocks.listMyAuctions },
}));
vi.mock('../api/products', () => ({
  productsApi: { listMyProducts: mocks.listMyProducts },
}));
vi.mock('../api/categories', () => ({
  categoriesApi: { listCategories: mocks.listCategories },
}));
vi.mock('../api/payments', () => ({
  paymentsApi: { listMySellerTransactions: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20, pages: 1 }) },
}));
vi.mock('../api/client', () => ({
  getErrorMessage: (error) => error.message || 'Request failed',
}));
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 3, role: 'SELLER' }, register: vi.fn() }),
}));

const notStarted = { status: 'NOT_STARTED', can_list: false, required: true, message: 'x' };
const done = { status: 'DEMO_COMPLETED', can_list: true, required: true, message: 'x' };

describe('SellerPaymentSetupPanel', () => {
  it('requires acknowledgement and labels the setup as simulated', () => {
    const onComplete = vi.fn();
    render(
      <SellerPaymentSetupPanel setup={notStarted} onComplete={onComplete} onRetry={vi.fn()} />,
    );
    expect(screen.getByText('Simulated demo')).toBeTruthy();
    expect(screen.queryByLabelText(/account number|ifsc|routing/i)).toBeNull();
    const button = screen.getByRole('button', { name: /complete simulated setup/i });
    expect(button.disabled).toBe(true);
    fireEvent.click(screen.getByRole('checkbox'));
    expect(button.disabled).toBe(false);
    fireEvent.click(button);
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('shows completed state without claiming payouts are enabled', () => {
    render(<SellerPaymentSetupPanel setup={done} onRetry={vi.fn()} />);
    expect(screen.getByText(/demo payment setup complete/i)).toBeTruthy();
    expect(screen.getByText(/no real payouts are enabled/i)).toBeTruthy();
  });

  it('shows an error with retry', () => {
    const onRetry = vi.fn();
    render(<SellerPaymentSetupPanel error="Setup unavailable" onRetry={onRetry} />);
    expect(screen.getByText('Setup unavailable')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(onRetry).toHaveBeenCalled();
  });
});

describe('Seller dashboard gating', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.listMyAuctions.mockResolvedValue({ items: [] });
    mocks.listMyProducts.mockResolvedValue({ items: [] });
    mocks.listCategories.mockResolvedValue([]);
  });

  it('blocks the catalog button and opens Payment Setup when setup is incomplete', async () => {
    mocks.getStatus.mockResolvedValue(notStarted);
    render(<MemoryRouter><SellerDashboardPage /></MemoryRouter>);
    await screen.findByText(/Payment Setup required/i);
    fireEvent.click(screen.getAllByRole('button', { name: /catalog new product/i })[0]);
    expect(screen.queryByRole('heading', { name: 'Catalog New Product' })).toBeNull();
    expect(await screen.findByRole('button', { name: /complete simulated setup/i })).toBeTruthy();
  });

  it('completes setup and then allows cataloging', async () => {
    mocks.getStatus.mockResolvedValue(notStarted);
    mocks.completeDemoSetup.mockResolvedValue(done);
    render(<MemoryRouter><SellerDashboardPage /></MemoryRouter>);
    await screen.findByText(/Payment Setup required/i);
    fireEvent.click(screen.getByRole('button', { name: /^Payment Setup/ }));
    fireEvent.click(await screen.findByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: /complete simulated setup/i }));
    await waitFor(() => expect(mocks.completeDemoSetup).toHaveBeenCalled());
    await waitFor(() => expect(screen.queryByText(/Payment Setup required/i)).toBeNull());
    fireEvent.click(screen.getAllByRole('button', { name: /catalog new product/i })[0]);
    expect(await screen.findByRole('heading', { name: 'Catalog New Product' })).toBeTruthy();
  });
});

describe('Register page seller notice', () => {
  it('explains mandatory simulated payment setup only for sellers', () => {
    render(<MemoryRouter><RegisterPage /></MemoryRouter>);
    expect(screen.queryByTestId('seller-payment-setup-notice')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /^seller/i }));
    expect(screen.getByTestId('seller-payment-setup-notice').textContent).toMatch(/simulated/i);
  });
});
