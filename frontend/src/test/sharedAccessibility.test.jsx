import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { SuccessAlert } from '../components/common/SuccessAlert';
import { Pagination } from '../components/common/Pagination';
import { AuctionFilters } from '../components/auctions/AuctionFilters';

describe('shared control accessibility', () => {
  it('announces loading state and uses a fallback name when there is no message', () => {
    const { rerender } = render(<LoadingSpinner message="Loading auctions" />);

    expect(screen.getByRole('status')).toHaveTextContent('Loading auctions');
    expect(screen.getByRole('status')).toHaveAttribute('aria-busy', 'true');

    rerender(<LoadingSpinner message={null} />);
    expect(screen.getByRole('status', { name: 'Loading' })).toBeInTheDocument();
  });

  it('announces errors assertively and success messages politely', () => {
    const { rerender } = render(<ErrorAlert message="Unable to load auctions" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Unable to load auctions');

    rerender(<SuccessAlert message="Auction saved" />);
    expect(screen.getByRole('status')).toHaveTextContent('Auction saved');
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  });

  it('provides a labeled pagination landmark and named page controls', () => {
    const onPageChange = vi.fn();
    render(<Pagination currentPage={2} totalPages={3} onPageChange={onPageChange} />);

    expect(screen.getByRole('navigation', { name: 'Pagination' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Previous page' }));
    fireEvent.click(screen.getByRole('button', { name: 'Next page' }));
    expect(onPageChange).toHaveBeenNthCalledWith(1, 1);
    expect(onPageChange).toHaveBeenNthCalledWith(2, 3);
  });

  it('gives every auction filter an accessible name and exposes condition selection', () => {
    const onFilterChange = vi.fn();
    render(
      <AuctionFilters
        filters={{ condition: 'USED' }}
        categories={[{ id: 1, name: 'Collectibles' }]}
        onFilterChange={onFilterChange}
        onReset={vi.fn()}
      />
    );

    expect(screen.getByLabelText('Search auctions')).toBeInTheDocument();
    expect(screen.getByLabelText('Category')).toBeInTheDocument();
    expect(screen.getByLabelText('Auction status')).toBeInTheDocument();
    expect(screen.getByLabelText('Sort auctions')).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Condition' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'USED' })).toHaveAttribute('aria-pressed', 'true');

    fireEvent.click(screen.getByRole('button', { name: 'NEW' }));
    expect(onFilterChange).toHaveBeenCalledWith({ condition: 'NEW', page: 1 });
  });
});
