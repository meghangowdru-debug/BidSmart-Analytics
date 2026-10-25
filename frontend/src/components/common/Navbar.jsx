import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  Gavel,
  Bell,
  User as UserIcon,
  LogOut,
  Menu,
  X,
  LayoutDashboard,
  Store,
  ShieldCheck,
  Compass,
  BarChart3,
  CreditCard,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useNotifications } from '../../context/NotificationContext';
import { RoleBadge } from './Badge';

export const Navbar = () => {
  const { isAuthenticated, user, role, logout, isBuyer, isSeller, isAdmin } = useAuth();
  const { unreadCount } = useNotifications();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3">
            <Link to="/" className="flex items-center space-x-2.5 group">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center text-white shadow-md shadow-indigo-200 group-hover:scale-105 transition-transform">
                <Gavel className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xl font-black tracking-tight text-slate-900 group-hover:text-indigo-600 transition-colors">
                  BidSmart
                </span>
                <span className="hidden sm:inline-block ml-1.5 text-[10px] font-bold uppercase tracking-widest text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">
                  v1.0
                </span>
              </div>
            </Link>
          </div>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1 lg:space-x-2">
            <Link
              to="/catalog"
              className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive('/catalog')
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Compass className="w-4 h-4" />
              <span>Catalog</span>
            </Link>

            {isAuthenticated && (
              <>
                {(isBuyer || isAdmin) && (
                  <Link
                    to="/dashboard/buyer"
                    className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive('/dashboard/buyer')
                        ? 'bg-indigo-50 text-indigo-700'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`}
                  >
                    <LayoutDashboard className="w-4 h-4" />
                    <span>Buyer Hub</span>
                  </Link>
                )}
                {isBuyer && (
                  <Link
                    to="/payments/history"
                    className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive('/payments/history')
                        ? 'bg-indigo-50 text-indigo-700'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`}
                  >
                    <CreditCard className="w-4 h-4" />
                    <span>Payments</span>
                  </Link>
                )}

                {(isSeller || isAdmin) && (
                  <Link
                    to="/dashboard/seller"
                    className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive('/dashboard/seller')
                        ? 'bg-indigo-50 text-indigo-700'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`}
                  >
                    <Store className="w-4 h-4" />
                    <span>Seller Console</span>
                  </Link>
                )}

                {isAdmin && (
                  <Link
                    to="/dashboard/admin"
                    className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive('/dashboard/admin')
                        ? 'bg-rose-50 text-rose-700'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`}
                  >
                    <ShieldCheck className="w-4 h-4 text-rose-600" />
                    <span>Admin Center</span>
                  </Link>
                )}
                {isAdmin && (
                  <Link
                    to="/admin/transactions"
                    className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive('/admin/transactions')
                        ? 'bg-rose-50 text-rose-700'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                    }`}
                  >
                    <CreditCard className="w-4 h-4" />
                    <span>Transactions</span>
                  </Link>
                )}

                <Link
                  to="/dashboard/analytics"
                  className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive('/dashboard/analytics')
                      ? 'bg-emerald-50 text-emerald-700'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  <BarChart3 className="w-4 h-4" />
                  <span>Analytics</span>
                </Link>
              </>
            )}
          </nav>

          {/* Right Action Icons & Auth */}
          <div className="hidden md:flex items-center space-x-3">
            {isAuthenticated ? (
              <>
                {/* Notification Bell with Badge */}
                <Link
                  to="/notifications"
                  className="relative p-2 text-slate-500 hover:text-indigo-600 hover:bg-slate-100 rounded-lg transition-colors"
                  aria-label="View notifications"
                >
                  <Bell className="w-5 h-5" />
                  {unreadCount > 0 && (
                    <span className="absolute top-1.5 right-1.5 flex h-4 min-w-[16px] px-1 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white ring-2 ring-white">
                      {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                  )}
                </Link>

                {/* Profile Pill */}
                <div className="flex items-center space-x-2 pl-2 border-l border-slate-200">
                  <Link
                    to="/profile"
                    className="flex items-center space-x-2 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
                  >
                    <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs uppercase">
                      {user?.username?.substring(0, 2) || 'US'}
                    </div>
                    <div className="text-left hidden lg:block">
                      <div className="text-xs font-semibold text-slate-800 leading-tight">
                        {user?.username}
                      </div>
                      <RoleBadge role={role} />
                    </div>
                  </Link>

                  <button
                    onClick={handleLogout}
                    className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                    title="Sign Out"
                    aria-label="Sign out"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                </div>
              </>
            ) : (
              <div className="flex items-center space-x-2">
                <Link
                  to="/login"
                  className="px-4 py-2 text-sm font-medium text-slate-700 hover:text-indigo-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-colors"
                >
                  Register
                </Link>
              </div>
            )}
          </div>

          {/* Mobile Menu Toggle Button */}
          <div className="flex md:hidden items-center space-x-2">
            {isAuthenticated && (
              <Link
                to="/notifications"
                className="relative p-2 text-slate-600 rounded-lg"
                aria-label="Notifications"
              >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 flex h-4 min-w-[16px] px-1 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white">
                    {unreadCount}
                  </span>
                )}
              </Link>
            )}
            <button
              type="button"
              onClick={() => setMobileMenuOpen((isOpen) => !isOpen)}
              className="p-2 text-slate-600 hover:text-slate-900 rounded-lg"
              aria-label="Toggle navigation menu"
              aria-controls="mobile-navigation"
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      <nav
        id="mobile-navigation"
        aria-label="Mobile navigation"
        hidden={!mobileMenuOpen}
        className="md:hidden border-t border-slate-200 bg-white px-4 pt-3 pb-6 space-y-3"
      >
          <Link
            to="/catalog"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-lg text-base font-medium text-slate-700 hover:bg-slate-100"
          >
            Catalog
          </Link>

          {isAuthenticated ? (
            <>
              {(isBuyer || isAdmin) && (
                <Link
                  to="/dashboard/buyer"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-2 rounded-lg text-base font-medium text-slate-700 hover:bg-slate-100"
                >
                  Buyer Hub
                </Link>
              )}
              {isBuyer && (
                <Link
                  to="/payments/history"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-2 rounded-lg text-base font-medium text-slate-700 hover:bg-slate-100"
                >
                  Payment History
                </Link>
              )}

              {(isSeller || isAdmin) && (
                <Link
                  to="/dashboard/seller"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-2 rounded-lg text-base font-medium text-slate-700 hover:bg-slate-100"
                >
                  Seller Console
                </Link>
              )}

              {isAdmin && (
                <Link
                  to="/dashboard/admin"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-2 rounded-lg text-base font-medium text-rose-700 hover:bg-rose-50"
                >
                  Admin Center
                </Link>
              )}
              {isAdmin && (
                <Link
                  to="/admin/transactions"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-2 rounded-lg text-base font-medium text-rose-700 hover:bg-rose-50"
                >
                  Transactions
                </Link>
              )}

              <Link
                to="/dashboard/analytics"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-lg text-base font-medium text-emerald-700 hover:bg-emerald-50"
              >
                Analytics
              </Link>

              <Link
                to="/profile"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-lg text-base font-medium text-slate-700 hover:bg-slate-100"
              >
                Profile ({user?.username} - {role})
              </Link>

              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleLogout();
                }}
                className="w-full text-left px-3 py-2 rounded-lg text-base font-medium text-rose-600 hover:bg-rose-50"
              >
                Sign Out
              </button>
            </>
          ) : (
            <div className="pt-2 border-t border-slate-100 space-y-2">
              <Link
                to="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="block w-full text-center px-4 py-2.5 rounded-lg text-sm font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                onClick={() => setMobileMenuOpen(false)}
                className="block w-full text-center px-4 py-2.5 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700"
              >
                Register
              </Link>
            </div>
          )}
      </nav>
    </header>
  );
};
