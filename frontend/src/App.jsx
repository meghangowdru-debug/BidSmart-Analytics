import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { WatchlistProvider } from './context/WatchlistContext';
import { Navbar } from './components/common/Navbar';
import { Footer } from './components/common/Footer';
import { ProtectedRoute } from './components/common/ProtectedRoute';

// Pages
import { HomePage } from './pages/HomePage';
import { CatalogPage } from './pages/CatalogPage';
import { AuctionDetailPage } from './pages/AuctionDetailPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { BuyerDashboardPage } from './pages/BuyerDashboardPage';
import { SellerDashboardPage } from './pages/SellerDashboardPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { ProfilePage } from './pages/ProfilePage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { PaymentCheckoutPage } from './pages/PaymentCheckoutPage';
import { PaymentHistoryPage } from './pages/PaymentHistoryPage';
import { AdminTransactionsPage } from './pages/AdminTransactionsPage';
import { NotFoundPage } from './pages/NotFoundPage';

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NotificationProvider>
          <WatchlistProvider>
            <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans antialiased selection:bg-indigo-500 selection:text-white">
              <Navbar />
              <main className="flex-1">
                <Routes>
                  {/* Public routes */}
                  <Route path="/" element={<HomePage />} />
                  <Route path="/catalog" element={<CatalogPage />} />
                  <Route path="/auctions/:id" element={<AuctionDetailPage />} />
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />

                  <Route
                    path="/checkout/:auctionId"
                    element={
                      <ProtectedRoute allowedRoles={['BUYER']}>
                        <PaymentCheckoutPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/payments/history"
                    element={
                      <ProtectedRoute allowedRoles={['BUYER']}>
                        <PaymentHistoryPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/admin/transactions"
                    element={
                      <ProtectedRoute allowedRoles={['ADMIN']}>
                        <AdminTransactionsPage />
                      </ProtectedRoute>
                    }
                  />

                  {/* Protected Role-Gated Dashboards */}
                  <Route
                    path="/dashboard/buyer"
                    element={
                      <ProtectedRoute allowedRoles={['BUYER', 'ADMIN']}>
                        <BuyerDashboardPage />
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/dashboard/seller"
                    element={
                      <ProtectedRoute allowedRoles={['SELLER', 'ADMIN']}>
                        <SellerDashboardPage />
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/dashboard/admin"
                    element={
                      <ProtectedRoute allowedRoles={['ADMIN']}>
                        <AdminDashboardPage />
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/dashboard/analytics"
                    element={
                      <ProtectedRoute allowedRoles={['BUYER', 'SELLER', 'ADMIN']}>
                        <AnalyticsPage />
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/notifications"
                    element={
                      <ProtectedRoute>
                        <NotificationsPage />
                      </ProtectedRoute>
                    }
                  />

                  <Route
                    path="/profile"
                    element={
                      <ProtectedRoute>
                        <ProfilePage />
                      </ProtectedRoute>
                    }
                  />

                  {/* 404 Catch-All */}
                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </main>
              <Footer />
            </div>
          </WatchlistProvider>
        </NotificationProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
