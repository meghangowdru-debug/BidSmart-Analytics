import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { BrowserRouter, MemoryRouter, Route, Routes } from 'react-router-dom';
import { WonAuctionsPanel } from '../components/dashboard/WonAuctionsPanel';
import { PaymentCheckoutPage } from '../pages/PaymentCheckoutPage';

const {
  listWonAuctions,
  createOrder,
  verifyPayment,
  loadRazorpayCheckout,
} = vi.hoisted(() => ({
  listWonAuctions: vi.fn(),
  createOrder: vi.fn(),
  verifyPayment: vi.fn(),
  loadRazorpayCheckout: vi.fn(),
}));

vi.mock('../api/payments', () => ({
  paymentsApi: { listWonAuctions, createOrder, verifyPayment },
}));

vi.mock('../api/client', () => ({
  getErrorMessage: (error) => error.message || 'Request failed',
}));

vi.mock('../utils/razorpay', () => ({ loadRazorpayCheckout }));

const pendingAuction = {
  auction_id: 41,
  product_title: 'Vintage Camera',
  product_image_url: 'https://example.test/camera.png',
  auction_status: 'COMPLETED',
  start_time: '2026-04-01T10:00:00Z',
  end_time: '2026-04-02T10:00:00Z',
  amount: '125.50',
  payment_status: 'SETTLEMENT_PENDING_DEMO',
  payment_required: true,
  payment_verified: false,
};

const pageResponse = (auction) => ({
  items: auction ? [auction] : [],
  total: auction ? 1 : 0,
  page: 1,
  page_size: 100,
  pages: 1,
});

const renderCheckout = () => render(
  <MemoryRouter initialEntries={['/checkout/41']}>
    <Routes>
      <Route path="/checkout/:auctionId" element={<PaymentCheckoutPage />} />
    </Routes>
  </MemoryRouter>,
);

describe('Buyer payment interface', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.Razorpay = class RazorpayMock {
      constructor(options) {
        window.__razorpayOptions = options;
      }

      on(eventName, handler) {
        if (eventName === 'payment.failed') window.__paymentFailed = handler;
      }

      open() {
        window.__razorpayOpened = true;
      }
    };
    loadRazorpayCheckout.mockImplementation(() => Promise.resolve(window.Razorpay));
  });

  afterEach(() => {
    delete window.Razorpay;
    delete window.__razorpayOptions;
  });

  it('shows Pay Now only for wins the backend says still require payment', async () => {
    listWonAuctions.mockResolvedValue({
      items: [
        pendingAuction,
        { ...pendingAuction, auction_id: 42, payment_required: false, payment_verified: true },
      ],
      total: 2,
      page: 1,
      page_size: 100,
      pages: 1,
    });

    render(
      <BrowserRouter>
        <WonAuctionsPanel />
      </BrowserRouter>,
    );

    expect((await screen.findAllByText('Vintage Camera')).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('link', { name: 'Pay Now' })).toHaveLength(1);
    expect(screen.getByText('Paid')).toBeInTheDocument();
  });

  it('shows loading and API error/retry states for won auctions', async () => {
    listWonAuctions.mockRejectedValueOnce(new Error('Payment history unavailable'));
    render(
      <BrowserRouter>
        <WonAuctionsPanel />
      </BrowserRouter>,
    );
    expect(await screen.findByText('Payment history unavailable')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });

  it('creates a server-priced USD order and displays only server-confirmed payment success', async () => {
    listWonAuctions
      .mockResolvedValueOnce(pageResponse(pendingAuction))
      .mockResolvedValueOnce(pageResponse({ ...pendingAuction, payment_required: false, payment_verified: true }));
    createOrder.mockResolvedValue({
      key_id: 'rzp_test_public',
      order_id: 'order_test_123',
      amount: 12550,
      currency: 'USD',
    });
    verifyPayment.mockResolvedValue({ payment_status: 'SETTLEMENT_COMPLETED_DEMO' });

    renderCheckout();
    expect(await screen.findByText('Vintage Camera')).toBeInTheDocument();
    expect(screen.getByText('$125.50')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Pay securely' }));
    await waitFor(() => expect(window.__razorpayOptions).toBeDefined());

    expect(createOrder).toHaveBeenCalledWith(41);
    expect(window.__razorpayOptions.amount).toBe(12550);
    expect(window.__razorpayOptions.currency).toBe('USD');
    await act(async () => {
      await window.__razorpayOptions.handler({
        razorpay_order_id: 'order_test_123',
        razorpay_payment_id: 'pay_test_123',
        razorpay_signature: 'signed-value',
      });
    });

    expect(verifyPayment).toHaveBeenCalledWith({
      order_id: 'order_test_123',
      payment_id: 'pay_test_123',
      signature: 'signed-value',
    });
    expect(await screen.findByText('Verified payment status: Paid')).toBeInTheDocument();
  });

  it('does not show success when backend verification fails and handles checkout cancellation', async () => {
    listWonAuctions.mockResolvedValue(pageResponse(pendingAuction));
    createOrder.mockResolvedValue({
      key_id: 'rzp_test_public',
      order_id: 'order_test_123',
      amount: 12550,
      currency: 'USD',
    });
    verifyPayment.mockRejectedValue(new Error('Signature verification failed'));

    renderCheckout();
    fireEvent.click(await screen.findByRole('button', { name: 'Pay securely' }));
    await waitFor(() => expect(window.__razorpayOptions).toBeDefined());
    await act(async () => {
      await window.__razorpayOptions.handler({
        razorpay_order_id: 'order_test_123',
        razorpay_payment_id: 'pay_test_123',
        razorpay_signature: 'bad-signature',
      });
    });

    expect(await screen.findByText('Signature verification failed')).toBeInTheDocument();
    expect(screen.queryByText('Verified payment status: Paid')).not.toBeInTheDocument();

    delete window.__razorpayOptions;
    fireEvent.click(screen.getByRole('button', { name: 'Pay securely' }));
    await waitFor(() => expect(window.__razorpayOptions).toBeDefined());
    act(() => window.__razorpayOptions.modal.ondismiss());
    expect(await screen.findByText(/Checkout was cancelled/)).toBeInTheDocument();
  });

  it('shows an API error when the authoritative won-auction data cannot load', async () => {
    listWonAuctions.mockRejectedValue(new Error('Could not load buyer wins'));
    renderCheckout();
    expect(await screen.findByText('Could not load buyer wins')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });

  it('keeps a provider-reported failed payment unpaid and allows a retry', async () => {
    listWonAuctions.mockResolvedValue(pageResponse(pendingAuction));
    createOrder.mockResolvedValue({
      key_id: 'rzp_test_public',
      order_id: 'order_test_123',
      amount: 12550,
      currency: 'USD',
    });

    renderCheckout();
    fireEvent.click(await screen.findByRole('button', { name: 'Pay securely' }));
    await waitFor(() => expect(window.__paymentFailed).toBeDefined());
    act(() => window.__paymentFailed({ error: { description: 'Payment declined' } }));

    expect(await screen.findByText(/Payment failed: Payment declined/)).toBeInTheDocument();
    expect(screen.queryByText('Verified payment status: Paid')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Pay securely' })).toBeEnabled();
  });

  it('rejects an order whose amount differs from the server-provided winning amount', async () => {
    listWonAuctions.mockResolvedValue(pageResponse(pendingAuction));
    createOrder.mockResolvedValue({
      key_id: 'rzp_test_public',
      order_id: 'order_test_123',
      amount: 99999,
      currency: 'USD',
    });

    renderCheckout();
    fireEvent.click(await screen.findByRole('button', { name: 'Pay securely' }));

    expect(await screen.findByText(/does not match the authoritative auction amount/)).toBeInTheDocument();
    expect(loadRazorpayCheckout).not.toHaveBeenCalled();
  });
});
