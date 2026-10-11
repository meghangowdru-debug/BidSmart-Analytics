import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatusBadge, RoleBadge, ConditionBadge } from '../components/common/Badge';
import { CountdownTimer } from '../components/common/CountdownTimer';
import { StatsCard } from '../components/dashboard/StatsCard';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { SuccessAlert } from '../components/common/SuccessAlert';

describe('Common UI Components', () => {
  describe('StatusBadge', () => {
    it('renders ACTIVE badge correctly', () => {
      render(<StatusBadge status="ACTIVE" />);
      expect(screen.getByText('Active')).toBeInTheDocument();
    });

    it('renders COMPLETED badge correctly', () => {
      render(<StatusBadge status="COMPLETED" />);
      expect(screen.getByText('Completed')).toBeInTheDocument();
    });

    it('renders RESERVE_NOT_MET badge correctly', () => {
      render(<StatusBadge status="RESERVE_NOT_MET" />);
      expect(screen.getByText('Reserve Not Met')).toBeInTheDocument();
    });
  });

  describe('RoleBadge', () => {
    it('renders BUYER role', () => {
      render(<RoleBadge role="BUYER" />);
      expect(screen.getByText('BUYER')).toBeInTheDocument();
    });

    it('renders SELLER role', () => {
      render(<RoleBadge role="SELLER" />);
      expect(screen.getByText('SELLER')).toBeInTheDocument();
    });

    it('renders ADMIN role', () => {
      render(<RoleBadge role="ADMIN" />);
      expect(screen.getByText('ADMIN')).toBeInTheDocument();
    });
  });

  describe('ConditionBadge', () => {
    it('renders NEW condition', () => {
      render(<ConditionBadge condition="NEW" />);
      expect(screen.getByText('Brand New')).toBeInTheDocument();
    });

    it('renders VINTAGE condition', () => {
      render(<ConditionBadge condition="VINTAGE" />);
      expect(screen.getByText('Vintage / Collectible')).toBeInTheDocument();
    });
  });

  describe('CountdownTimer', () => {
    it('shows expired message when end time has passed', () => {
      const pastTime = new Date(Date.now() - 10000).toISOString();
      render(<CountdownTimer endTime={pastTime} />);
      expect(screen.getByText(/Auction Ended/i)).toBeInTheDocument();
    });

    it('renders active timer for future end time', () => {
      const futureTime = new Date(Date.now() + 3600000).toISOString(); // 1 hour
      render(<CountdownTimer endTime={futureTime} />);
      expect(screen.getByText('h')).toBeInTheDocument();
      expect(screen.getByText('m')).toBeInTheDocument();
    });
  });

  describe('StatsCard', () => {
    it('renders title, value, and subtitle', () => {
      render(
        <StatsCard
          title="Total Bids"
          value={42}
          subtitle="All recorded bids"
        />
      );
      expect(screen.getByText('Total Bids')).toBeInTheDocument();
      expect(screen.getByText('42')).toBeInTheDocument();
      expect(screen.getByText('All recorded bids')).toBeInTheDocument();
    });
  });

  describe('Alerts and Spinners', () => {
    it('renders LoadingSpinner with custom message', () => {
      render(<LoadingSpinner message="Testing spinner..." />);
      expect(screen.getByText('Testing spinner...')).toBeInTheDocument();
    });

    it('renders EmptyState with title and description', () => {
      render(<EmptyState title="Nothing here" description="Empty description text" />);
      expect(screen.getByText('Nothing here')).toBeInTheDocument();
      expect(screen.getByText('Empty description text')).toBeInTheDocument();
    });

    it('renders ErrorAlert with message', () => {
      render(<ErrorAlert message="Test failure notice" />);
      expect(screen.getByText('Test failure notice')).toBeInTheDocument();
    });

    it('renders SuccessAlert with message', () => {
      render(<SuccessAlert message="Operation accomplished" />);
      expect(screen.getByText('Operation accomplished')).toBeInTheDocument();
    });
  });
});
