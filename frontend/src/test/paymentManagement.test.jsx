import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { PaymentHistoryPage } from '../pages/PaymentHistoryPage';
import { AdminTransactionsPage } from '../pages/AdminTransactionsPage';
import { SellerPaymentsPanel } from '../components/dashboard/SellerPaymentsPanel';

const { listMyTransactions, listMySellerTransactions, listAdminTransactions } = vi.hoisted(() => ({
  listMyTransactions: vi.fn(),
  listMySellerTransactions: vi.fn(),
  listAdminTransactions: vi.fn(),
}));

vi.mock('../api/payments', () => ({
  paymentsApi: { listMyTransactions, listMySellerTransactions, listAdminTransactions },
}));

vi.mock('../api/client', () => ({
  getErrorMessage: (error) => error.message || 'Request failed',
}));

const transaction = {
  transaction_id: 8,
  auction_id: 71,
  product_title: 'Oak Writing Desk',
  amount: '240.00',
  currency: 'USD',
  payment_status: 'SETTLEMENT_COMPLETED_DEMO',
  payment_verified: true,
  created_at: '2026-10-01T12:00:00Z',
  settled_at: '2026-10-03T14:30:00Z',
  buyer_id: 12,
  seller_id: 4,
};

const pageResult = (items, page = 1, pages = 1) => ({
  items,
  total: items.length,
  page,
  page_size: 20,
  pages,
});

const renderInRouter = (element) => render(
  <MemoryRouter>{element}</MemoryRouter>,
);

describe('Payment history and admin monitoring', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows buyer-owned transaction fields and paid only with server verification', async () => {
    listMyTransactions.mockResolvedValue(pageResult([
      transaction,
      { ...transaction, transaction_id: 9, auction_id: 72, payment_verified: false },
    ]));
    renderInRouter(<PaymentHistoryPage />);

    expect((await screen.findAllByText('Oak Writing Desk')).length).toBeGreaterThan(0);
    expect(screen.getByText('Paid (verified)')).toBeInTheDocument();
    expect(screen.getByText('Verification unavailable')).toBeInTheDocument();
    expect(screen.getAllByText('$240.00')).toHaveLength(2);
    expect(listMyTransactions).toHaveBeenCalledWith({ page: 1, page_size: 20 });
  });

  it('supports buyer history empty, failure, retry, and pagination states', async () => {
    listMyTransactions
      .mockRejectedValueOnce(new Error('History unavailable'))
      .mockResolvedValueOnce(pageResult([], 1, 1));
    renderInRouter(<PaymentHistoryPage />);

    expect(await screen.findByText('History unavailable')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('No payment history yet')).toBeInTheDocument();
    expect(listMyTransactions).toHaveBeenCalledTimes(2);
  });

  it('applies admin status, identity, and date filters and renders safe monitoring fields', async () => {
    listAdminTransactions.mockResolvedValue(pageResult([transaction]));
    renderInRouter(<AdminTransactionsPage />);
    expect(await screen.findByText('Transaction Monitoring')).toBeInTheDocument();
    expect(screen.getByText('Paid (verified)')).toBeInTheDocument();
    expect(screen.getByText('#12')).toBeInTheDocument();
    expect(screen.getByText('#4')).toBeInTheDocument();
    expect(screen.queryByText(/rzp_|pay_test|provider_payment_id|payment_reference/i)).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Payment status'), {
      target: { value: 'SETTLEMENT_COMPLETED_DEMO' },
    });
    fireEvent.change(screen.getByLabelText('Buyer ID'), { target: { value: '12' } });
    fireEvent.change(screen.getByLabelText('Auction ID'), { target: { value: '71' } });
    fireEvent.change(screen.getByLabelText('Created from'), { target: { value: '2026-10-01' } });
    fireEvent.change(screen.getByLabelText('Created through'), { target: { value: '2026-10-03' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply filters' }));

    await waitFor(() => {
      expect(listAdminTransactions).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 20,
        payment_status: 'SETTLEMENT_COMPLETED_DEMO',
        buyer_id: '12',
        auction_id: '71',
        created_from: '2026-10-01',
        created_to: '2026-10-03',
      });
    });
  });

  it('shows admin monitoring errors with retry and supports pagination', async () => {
    listAdminTransactions
      .mockRejectedValueOnce(new Error('Monitoring API unavailable'))
      .mockResolvedValueOnce(pageResult([transaction], 1, 2))
      .mockResolvedValueOnce(pageResult([transaction], 2, 2));
    renderInRouter(<AdminTransactionsPage />);

    expect(await screen.findByText('Monitoring API unavailable')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('Transaction Monitoring')).toBeInTheDocument();
    await waitFor(() => expect(listAdminTransactions).toHaveBeenCalledTimes(2));
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    await waitFor(() => expect(listAdminTransactions).toHaveBeenLastCalledWith({
      page: 2,
      page_size: 20,
    }));
  });

  it('shows seller-scoped actual totals and does not imply a real payout', async () => {
    listMySellerTransactions.mockResolvedValue({
      ...pageResult([
        {
          ...transaction,
          settlement_type: 'SIMULATED_DEMO',
        },
        {
          ...transaction,
          transaction_id: 9,
          auction_id: 72,
          payment_status: 'SETTLEMENT_PENDING_DEMO',
          payment_verified: false,
          settled_at: null,
          settlement_type: 'SIMULATED_DEMO',
        },
      ]),
      summary: {
        total_sales: '240.00',
        verified_payment_total: '240.00',
        simulated_settlement_total: '240.00',
        pending_settlements: '125.00',
        completed_settlements: '240.00',
        transaction_count: 2,
      },
    });
    renderInRouter(<SellerPaymentsPanel />);

    expect(await screen.findByText('Payments & Earnings')).toBeInTheDocument();
    expect(screen.getAllByText('$240.00')).toHaveLength(4);
    expect(screen.getByText('$125.00')).toBeInTheDocument();
    expect(screen.getByText('Transactions')).toBeInTheDocument();
    expect(screen.getByText('Payment verified (demo)')).toBeInTheDocument();
    expect(screen.getByText('Payment pending')).toBeInTheDocument();
    expect(screen.getByText('Completed (simulated)')).toBeInTheDocument();
    expect(screen.getByText('Pending (simulated)')).toBeInTheDocument();
    expect(screen.getAllByText(/SIMULATED_DEMO · no payout/)).toHaveLength(2);
    expect(screen.getByText(/do not represent real money received or a seller payout/i)).toBeInTheDocument();
    expect(listMySellerTransactions).toHaveBeenCalledWith({ page: 1, page_size: 20 });
  });

  it('shows seller payment errors, retries, and renders an empty state', async () => {
    listMySellerTransactions
      .mockRejectedValueOnce(new Error('Seller history unavailable'))
      .mockResolvedValueOnce({
        ...pageResult([]),
        summary: {
          total_sales: '0.00',
          verified_payment_total: '0.00',
          simulated_settlement_total: '0.00',
          pending_settlements: '0.00',
          completed_settlements: '0.00',
          transaction_count: 0,
        },
      });
    renderInRouter(<SellerPaymentsPanel />);

    expect(await screen.findByText('Seller history unavailable')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('No seller transactions yet')).toBeInTheDocument();
    expect(listMySellerTransactions).toHaveBeenCalledTimes(2);
  });
});
