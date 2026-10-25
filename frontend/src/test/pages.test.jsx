import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { LoginPage } from '../pages/LoginPage';
import { RegisterPage } from '../pages/RegisterPage';
import { NotFoundPage } from '../pages/NotFoundPage';
import { AuthProvider } from '../context/AuthContext';

describe('Page Components', () => {
  describe('NotFoundPage', () => {
    it('renders 404 header and catalog link', () => {
      render(
        <BrowserRouter>
          <NotFoundPage />
        </BrowserRouter>
      );

      expect(screen.getByText('404')).toBeInTheDocument();
      expect(screen.getByText(/Page or Auction Lot Not Found/i)).toBeInTheDocument();
      expect(screen.getByText(/Browse Catalog/i)).toBeInTheDocument();
    });
  });

  describe('LoginPage', () => {
    it('renders login form inputs and demo fill buttons', () => {
      render(
        <BrowserRouter>
          <AuthProvider>
            <LoginPage />
          </AuthProvider>
        </BrowserRouter>
      );

      expect(screen.getByText(/Sign In to BidSmart/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/e\.g\. buyer_elena/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();

      // Quick demo fillers
      expect(screen.getByText('Buyer')).toBeInTheDocument();
      expect(screen.getByText('Seller')).toBeInTheDocument();
      expect(screen.getByText('Admin')).toBeInTheDocument();
    });
  });

  describe('RegisterPage', () => {
    it('renders role selector for BUYER and SELLER', () => {
      render(
        <BrowserRouter>
          <AuthProvider>
            <RegisterPage />
          </AuthProvider>
        </BrowserRouter>
      );

      expect(screen.getByText(/Create Your Account/i)).toBeInTheDocument();
      expect(screen.getByText('Buyer')).toBeInTheDocument();
      expect(screen.getByText('Seller')).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/collector_dan/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/dan@example\.com/i)).toBeInTheDocument();
    });
  });
});
