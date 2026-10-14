import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { AnalyticsPage } from '../pages/AnalyticsPage';

const { getAnalytics, listCategories } = vi.hoisted(() => ({
  getAnalytics: vi.fn(),
  listCategories: vi.fn(),
}));

vi.mock('../api/analytics', () => ({
  analyticsApi: { getAnalytics },
}));

vi.mock('../api/categories', () => ({
  categoriesApi: { listCategories },
}));

vi.mock('recharts', () => ({
  Bar: () => null,
  BarChart: () => null,
  CartesianGrid: () => null,
  Cell: () => null,
  Line: () => null,
  LineChart: () => null,
  Pie: () => null,
  PieChart: () => null,
  ResponsiveContainer: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}));

const analyticsResponse = {
  scope: 'admin',
  currency: 'USD',
  date_basis: 'UTC',
  filters: { start_date: '2026-01-01', end_date: '2026-01-30', category_id: null },
  kpis: {
    registered_users: 5,
    buyers: 2,
    sellers: 2,
    total_products: 3,
    total_auctions: 3,
    active_auctions: 1,
    upcoming_auctions: 1,
    completed_auctions: 1,
    cancelled_auctions: 0,
    recorded_bids: 4,
    valid_bids: 3,
    auctions_participated: 0,
    auctions_won: 0,
    watchlist_items: 0,
    settled_transactions: 1,
    settled_sales_value: '120.00',
    average_settled_selling_price: '120.00',
    purchases: 0,
    spending: '0.00',
  },
  auction_status_distribution: [],
  category_performance: [],
  product_rankings: [],
  auction_rankings: [],
  daily_trends: [],
  monthly_trends: [],
};

describe('AnalyticsPage', () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it('loads real analytics data and requests updated metrics when filters change', async () => {
    listCategories.mockResolvedValue([{ id: 4, name: 'Electronics' }]);
    getAnalytics.mockResolvedValue(analyticsResponse);

    render(
      <BrowserRouter>
        <AnalyticsPage />
      </BrowserRouter>,
    );

    expect(await screen.findByText(/Marketplace-wide performance/)).toBeInTheDocument();
    expect(screen.getByText('Registered users')).toBeInTheDocument();
    expect(screen.getByText('Electronics')).toBeInTheDocument();
    expect(getAnalytics).toHaveBeenCalledWith(expect.objectContaining({
      start_date: expect.any(String),
      end_date: expect.any(String),
    }));

    fireEvent.change(screen.getByLabelText('Category'), { target: { value: '4' } });

    await waitFor(() => {
      expect(getAnalytics).toHaveBeenLastCalledWith(expect.objectContaining({
        category_id: 4,
      }));
    });

    fireEvent.change(screen.getByLabelText('Trend interval'), { target: { value: 'monthly' } });
    expect(screen.getByText('Monthly activity')).toBeInTheDocument();
  });

  it('shows an API error without replacing it with a category-loading result', async () => {
    listCategories.mockResolvedValue([]);
    getAnalytics.mockRejectedValue(new Error('Analytics request failed'));

    render(
      <BrowserRouter>
        <AnalyticsPage />
      </BrowserRouter>,
    );

    expect(await screen.findByText('Analytics request failed')).toBeInTheDocument();
  });

  it('shows the empty state when the API returns no recorded activity', async () => {
    listCategories.mockResolvedValue([]);
    getAnalytics.mockResolvedValue(analyticsResponse);

    render(
      <BrowserRouter>
        <AnalyticsPage />
      </BrowserRouter>,
    );

    expect(await screen.findByText(/No recorded activity matches this date range/i)).toBeInTheDocument();
  });

  it('refreshes metrics while visible without replacing the page', async () => {
    vi.useFakeTimers();
    listCategories.mockResolvedValue([]);
    getAnalytics
      .mockResolvedValueOnce(analyticsResponse)
      .mockResolvedValueOnce({
        ...analyticsResponse,
        kpis: { ...analyticsResponse.kpis, registered_users: 6 },
      });

    const { container } = render(
      <BrowserRouter>
        <AnalyticsPage />
      </BrowserRouter>,
    );
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByText('5')).toBeInTheDocument();
    const pageHeading = container.querySelector('h1');

    await act(async () => {
      await vi.advanceTimersByTimeAsync(12000);
    });

    expect(screen.getByText('6')).toBeInTheDocument();
    expect(container.querySelector('h1')).toBe(pageHeading);
    expect(screen.getByText(/Last updated/)).toBeInTheDocument();
    expect(getAnalytics).toHaveBeenCalledTimes(2);
  });

  it('pauses polling while hidden and refreshes when the tab becomes visible', async () => {
    const originalHiddenDescriptor = Object.getOwnPropertyDescriptor(document, 'hidden');
    Object.defineProperty(document, 'hidden', { configurable: true, value: true });
    vi.useFakeTimers();
    listCategories.mockResolvedValue([]);
    getAnalytics.mockResolvedValue(analyticsResponse);

    try {
      render(
        <BrowserRouter>
          <AnalyticsPage />
        </BrowserRouter>,
      );
      await act(async () => {
        await vi.advanceTimersByTimeAsync(24000);
      });
      expect(getAnalytics).not.toHaveBeenCalled();

      Object.defineProperty(document, 'hidden', { configurable: true, value: false });
      await act(async () => {
        document.dispatchEvent(new Event('visibilitychange'));
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(getAnalytics).toHaveBeenCalledTimes(1);
    } finally {
      if (originalHiddenDescriptor) {
        Object.defineProperty(document, 'hidden', originalHiddenDescriptor);
      } else {
        delete document.hidden;
      }
    }
  });

  it('does not overlap polling requests and keeps the last data after refresh failure', async () => {
    let finishInitialRequest;
    let rejectRefresh;
    vi.useFakeTimers();
    listCategories.mockResolvedValue([]);
    getAnalytics
      .mockImplementationOnce(() => new Promise((resolve) => {
        finishInitialRequest = resolve;
      }))
      .mockImplementationOnce(() => new Promise((_, reject) => {
        rejectRefresh = reject;
      }));

    render(
      <BrowserRouter>
        <AnalyticsPage />
      </BrowserRouter>,
    );
    expect(getAnalytics).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(12000);
    });
    expect(getAnalytics).toHaveBeenCalledTimes(1);

    await act(async () => {
      finishInitialRequest(analyticsResponse);
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByText('5')).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(12000);
    });
    expect(getAnalytics).toHaveBeenCalledTimes(2);
    await act(async () => {
      rejectRefresh(new Error('Refresh failed'));
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByText('Refresh failed')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });
});
