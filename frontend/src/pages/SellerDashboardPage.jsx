import React, { useState, useEffect, useCallback } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Store,
  Package,
  PlusCircle,
  Gavel,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  RefreshCw,
  Clock,
  Layers,
  X,
  CreditCard,
} from 'lucide-react';
import { auctionsApi } from '../api/auctions';
import { productsApi } from '../api/products';
import { categoriesApi } from '../api/categories';
import { useAuth } from '../context/AuthContext';
import { StatsCard } from '../components/dashboard/StatsCard';
import { ActivityChart } from '../components/dashboard/ActivityChart';
import { StatusBadge, ConditionBadge } from '../components/common/Badge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { SuccessAlert } from '../components/common/SuccessAlert';
import { SellerPaymentsPanel } from '../components/dashboard/SellerPaymentsPanel';
import {
  SellerPaymentSetupPanel,
  PAYMENT_SETUP_REQUIRED_MESSAGE,
} from '../components/dashboard/SellerPaymentSetupPanel';
import { sellerPaymentSetupApi } from '../api/sellerPaymentSetup';
import { getErrorMessage } from '../api/client';
import { canCloseAuction, canCancelAuction } from '../utils/auctionActions';
import {
  addLocalDaysToDateTime,
  getMinimumAuctionEnd,
  toLocalDateTimeInput,
  toUtcISOString,
  validateAuctionSchedule,
} from '../utils/auctionScheduling';

export const SellerDashboardPage = () => {
  const { user } = useAuth();
  const [scheduleClock, setScheduleClock] = useState(() => new Date());

  const location = useLocation();
  const [activeTab, setActiveTab] = useState(location.state?.tab || 'auctions');
  const [auctions, setAuctions] = useState([]);
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Modal / Form states
  const [showProductModal, setShowProductModal] = useState(false);
  const [showAuctionModal, setShowAuctionModal] = useState(false);
  const [selectedProductForAuction, setSelectedProductForAuction] = useState(null);

  const [productForm, setProductForm] = useState({
    title: '',
    description: '',
    category_id: '',
    condition_status: 'NEW',
    image_url: '',
    thumbnail_url: '',
  });

  const [auctionForm, setAuctionForm] = useState(() => {
    const startTime = toLocalDateTimeInput(new Date());
    const endTime = addLocalDaysToDateTime(startTime, 3);
    return {
      product_id: '',
      starting_price: '10.00',
      reserve_price: '20.00',
      minimum_increment: '1.00',
      start_time: startTime,
      end_time: endTime,
    };
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [scheduleError, setScheduleError] = useState(null);
  const [paymentSetup, setPaymentSetup] = useState(null);
  const [setupLoading, setSetupLoading] = useState(true);
  const [setupError, setSetupError] = useState(null);
  const [setupSubmitting, setSetupSubmitting] = useState(false);

  const loadPaymentSetup = useCallback(async () => {
    setSetupLoading(true);
    setSetupError(null);
    try {
      setPaymentSetup(await sellerPaymentSetupApi.getStatus());
    } catch (err) {
      setSetupError(getErrorMessage(err));
    } finally {
      setSetupLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    loadPaymentSetup();
  }, [loadPaymentSetup]);

  const handleCompleteSetup = async () => {
    setSetupSubmitting(true);
    setSetupError(null);
    try {
      setPaymentSetup(await sellerPaymentSetupApi.completeDemoSetup());
      setSuccess('Simulated payment setup complete. No real payouts are enabled.');
    } catch (err) {
      setSetupError(getErrorMessage(err));
    } finally {
      setSetupSubmitting(false);
    }
  };

  // Only a confirmed "cannot list" blocks the UI; the backend remains the real enforcement.
  const setupBlocksListing = paymentSetup?.can_list === false;

  const requireSetupOrOpen = (open) => {
    if (setupBlocksListing) {
      setActiveTab('payment-setup');
      setError(PAYMENT_SETUP_REQUIRED_MESSAGE);
      return;
    }
    open();
  };

  useEffect(() => {
    const clock = setInterval(() => setScheduleClock(new Date()), 30000);
    return () => clearInterval(clock);
  }, []);

  const loadSellerData = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    setError(null);
    try {
      const [aucRes, prodRes, catRes] = await Promise.all([
        auctionsApi.listMyAuctions({ page_size: 50 }),
        productsApi.listMyProducts({ page_size: 50 }),
        categoriesApi.listCategories(),
      ]);
      setAuctions(aucRes.items || []);
      setProducts(prodRes.items || []);
      setCategories(catRes || []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    loadSellerData();
  }, [loadSellerData]);

  useEffect(() => {
    const refreshTimer = setInterval(() => loadSellerData(false), 30000);
    return () => clearInterval(refreshTimer);
  }, [loadSellerData]);

  // Actions
  const handleBatchClose = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const result = await auctionsApi.batchCloseExpired(user.id);
      setSuccess(
        `Batch sweep completed: Evaluated ${result.evaluated_count} expired auctions. Closed: ${result.closed_count}, Unsold: ${result.unsold_count}.`
      );
      loadSellerData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCloseSingleAuction = async (auctionId) => {
    if (!window.confirm(`Close auction #${auctionId} and settle final winner?`)) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await auctionsApi.closeAuction(auctionId, false);
      setSuccess(`Auction #${auctionId} closed with status ${res.status}.`);
      loadSellerData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelSingleAuction = async (auctionId) => {
    if (!window.confirm(`Cancel auction #${auctionId}?`)) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await auctionsApi.cancelAuction(auctionId);
      setSuccess(`Auction #${auctionId} was cancelled.`);
      loadSellerData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Product submission
  const handleCreateProduct = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await productsApi.createProduct({
        ...productForm,
        category_id: Number(productForm.category_id),
      });
      setSuccess(`Product '${productForm.title}' cataloged successfully!`);
      setShowProductModal(false);
      setProductForm({
        title: '',
        description: '',
        category_id: '',
        condition_status: 'NEW',
        image_url: '',
        thumbnail_url: '',
      });
      await loadSellerData();
      setActiveTab('products');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Auction launch submission
  const handleCreateAuction = async (e) => {
    e.preventDefault();
    const validationError = validateAuctionSchedule(
      auctionForm.start_time,
      auctionForm.end_time,
      new Date()
    );
    if (validationError) {
      setScheduleError(validationError);
      return;
    }
    setScheduleError(null);
    setIsSubmitting(true);
    setError(null);
    try {
      await auctionsApi.createAuction({
        product_id: Number(auctionForm.product_id),
        starting_price: Number(auctionForm.starting_price),
        reserve_price: auctionForm.reserve_price ? Number(auctionForm.reserve_price) : undefined,
        minimum_increment: Number(auctionForm.minimum_increment),
        start_time: toUtcISOString(auctionForm.start_time),
        end_time: toUtcISOString(auctionForm.end_time),
      });
      setSuccess('Auction listing launched successfully!');
      setShowAuctionModal(false);
      loadSellerData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleScheduleFieldChange = (field, value) => {
    const updatedForm = { ...auctionForm, [field]: value };
    setAuctionForm(updatedForm);
    setScheduleError(validateAuctionSchedule(
      updatedForm.start_time,
      updatedForm.end_time,
      new Date()
    ));
  };

  const openAuctionModalForProduct = (product) => {
    if (setupBlocksListing) {
      requireSetupOrOpen(() => {});
      return;
    }
    const startTime = toLocalDateTimeInput(new Date());
    setSelectedProductForAuction(product);
    setScheduleError(null);
    setAuctionForm({
      product_id: product.id,
      starting_price: '10.00',
      reserve_price: '20.00',
      minimum_increment: '1.00',
      start_time: startTime,
      end_time: addLocalDaysToDateTime(startTime, 3),
    });
    setShowAuctionModal(true);
  };

  // Computations
  const activeAuctions = auctions.filter((a) => a.status === 'ACTIVE');
  const completedAuctions = auctions.filter((a) => a.status === 'COMPLETED');
  // Analytics data for Recharts
  const statusCounts = {
    ACTIVE: 0,
    COMPLETED: 0,
    UNSOLD: 0,
    RESERVE_NOT_MET: 0,
    CANCELLED: 0,
  };
  auctions.forEach((a) => {
    const s = a.status?.toUpperCase();
    if (statusCounts[s] !== undefined) statusCounts[s]++;
  });

  const chartData = [
    { name: 'Active', count: statusCounts.ACTIVE },
    { name: 'Completed', count: statusCounts.COMPLETED },
    { name: 'Unsold', count: statusCounts.UNSOLD },
    { name: 'Reserve Missed', count: statusCounts.RESERVE_NOT_MET },
    { name: 'Cancelled', count: statusCounts.CANCELLED },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Seller Inventory Console</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage product catalog, monitor confidential reserve prices, and settle completed lots.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => requireSetupOrOpen(() => setShowProductModal(true))}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-colors shadow-sm"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Catalog New Product</span>
          </button>

          <button
            onClick={handleBatchClose}
            disabled={isSubmitting}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition-colors disabled:opacity-50"
            title="Batch sweep and settle all expired auctions"
          >
            <Clock className="w-4 h-4 text-amber-400" />
            <span>Sweep Expired Lots</span>
          </button>
        </div>
      </div>

      {success && <SuccessAlert message={success} onClose={() => setSuccess(null)} />}
      {error && <ErrorAlert message={error} onClose={() => setError(null)} />}

      {setupBlocksListing && (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
        >
          <span>
            <strong>Payment Setup required.</strong> {PAYMENT_SETUP_REQUIRED_MESSAGE} (Simulated demo
            setup; no real payouts.)
          </span>
          <button
            type="button"
            onClick={() => setActiveTab('payment-setup')}
            className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-amber-700"
          >
            Complete Payment Setup
          </button>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Active Auctions"
          value={activeAuctions.length}
          subtitle="Currently open to bidding"
          icon={Gavel}
          color="indigo"
        />
        <StatsCard
          title="Catalog Products"
          value={products.length}
          subtitle="Total inventory lots"
          icon={Package}
          color="purple"
        />
        <StatsCard
          title="Completed Auctions"
          value={completedAuctions.length}
          subtitle="Closed auction listings"
          icon={CheckCircle2}
          color="emerald"
        />
        <StatsCard
          title="Winning Bids"
          value={completedAuctions.filter((auction) => auction.current_highest_bid != null).length}
          subtitle="Not payment or payout confirmation"
          icon={Gavel}
          color="amber"
        />
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="border-b border-slate-200 flex gap-6 overflow-x-auto px-6 pt-4">
          <button
            onClick={() => setActiveTab('auctions')}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'auctions'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            My Auctions ({auctions.length})
          </button>

          <button
            onClick={() => setActiveTab('products')}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'products'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Product Catalog ({products.length})
          </button>

          <button
            onClick={() => setActiveTab('analytics')}
            className={`pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'analytics'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Performance & Analytics
          </button>
          <button
            onClick={() => setActiveTab('payment-setup')}
            className={`inline-flex shrink-0 items-center gap-1.5 pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'payment-setup'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Payment Setup{setupBlocksListing ? ' (Required)' : ''}
          </button>
          <button
            onClick={() => setActiveTab('payments')}
            className={`inline-flex shrink-0 items-center gap-1.5 pb-3 text-xs font-bold uppercase tracking-wider transition-colors border-b-2 ${
              activeTab === 'payments'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <CreditCard className="h-4 w-4" />
            Payments &amp; Earnings
          </button>
        </div>

        {/* Tab 1: Auctions */}
        {activeTab === 'auctions' && (
          <div className="p-6">
            {isLoading ? (
              <LoadingSpinner message="Fetching seller listings..." />
            ) : auctions.length === 0 ? (
              <EmptyState
                icon={Gavel}
                title="No auctions listed yet"
                description="Catalog a product first, then launch an auction with your desired starting and reserve prices."
                action={
                  <button
                    onClick={() => requireSetupOrOpen(() => setShowProductModal(true))}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-bold hover:bg-indigo-700"
                  >
                    Catalog Product Now
                  </button>
                }
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-400 font-bold uppercase border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">Lot Title</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Starting</th>
                      <th className="py-3 px-4">Reserve (Private)</th>
                      <th className="py-3 px-4">Highest Bid</th>
                      <th className="py-3 px-4">Bids</th>
                      <th className="py-3 px-4">End Time</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {auctions.map((auc) => (
                      <tr key={auc.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4 font-semibold text-slate-900 max-w-xs truncate">
                          <Link to={`/auctions/${auc.id}`} className="hover:text-indigo-600">
                            {auc.product?.title || `Auction #${auc.id}`}
                          </Link>
                        </td>
                        <td className="py-3 px-4">
                          <StatusBadge status={auc.status} />
                        </td>
                        <td className="py-3 px-4 font-mono font-medium text-slate-700">
                          ${Number(auc.starting_price).toFixed(2)}
                        </td>
                        <td className="py-3 px-4 font-mono font-medium text-slate-700">
                          {auc.reserve_price ? (
                            <span>
                              ${Number(auc.reserve_price).toFixed(2)}
                              {auc.reserve_met !== null && (
                                <span
                                  className={`ml-1 text-[10px] font-bold px-1 py-0.2 rounded ${
                                    auc.reserve_met ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                                  }`}
                                >
                                  {auc.reserve_met ? 'Met' : 'Missed'}
                                </span>
                              )}
                            </span>
                          ) : (
                            <span className="text-slate-400">None</span>
                          )}
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-slate-900">
                          {auc.current_highest_bid !== null ? `$${Number(auc.current_highest_bid).toFixed(2)}` : '—'}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-600">
                          {auc.total_bids || 0}
                        </td>
                        <td className="py-3 px-4 text-slate-400">
                          {new Date(auc.end_time).toLocaleDateString(undefined, {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </td>
                        <td className="py-3 px-4 text-right space-x-2">
                          <Link
                            to={`/auctions/${auc.id}`}
                            className="font-bold text-indigo-600 hover:text-indigo-800"
                          >
                            View
                          </Link>
                          {(canCloseAuction(auc, false) || canCancelAuction(auc, false)) && (
                            <>
                              {canCloseAuction(auc, false) && (
                                <button
                                  onClick={() => handleCloseSingleAuction(auc.id)}
                                  className="font-bold text-emerald-600 hover:text-emerald-800"
                                >
                                  Close
                                </button>
                              )}
                              {canCancelAuction(auc, false) && (
                                <button
                                  onClick={() => handleCancelSingleAuction(auc.id)}
                                  className="font-bold text-rose-600 hover:text-rose-800"
                                >
                                  Cancel
                                </button>
                              )}
                            </>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Products */}
        {activeTab === 'products' && (
          <div className="p-6">
            {isLoading ? (
              <LoadingSpinner message="Fetching catalog..." />
            ) : products.length === 0 ? (
              <EmptyState
                icon={Package}
                title="Your catalog is empty"
                description="Add products to your catalog to make them available for auction listings."
                action={
                  <button
                    onClick={() => requireSetupOrOpen(() => setShowProductModal(true))}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-bold hover:bg-indigo-700"
                  >
                    Add Product Now
                  </button>
                }
              />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {products.map((p) => (
                  <div
                    key={p.id}
                    className="p-4 rounded-xl border border-slate-200 bg-white flex flex-col justify-between space-y-3"
                  >
                    <div className="flex items-start space-x-3">
                      <img
                        src={p.image_url}
                        alt={p.title}
                        className="w-16 h-16 rounded-lg object-cover bg-slate-100 flex-shrink-0"
                      />
                      <div className="flex-1 min-w-0">
                        <ConditionBadge condition={p.condition_status} />
                        <h4 className="font-bold text-xs text-slate-900 truncate mt-1">
                          {p.title}
                        </h4>
                        <p className="text-[11px] text-slate-500 line-clamp-2 mt-0.5">
                          {p.description}
                        </p>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                      <span className="text-[11px] text-slate-400">
                        {p.has_auction ? (
                          <span className="text-emerald-600 font-semibold">Auction Attached</span>
                        ) : (
                          <span>Unlisted</span>
                        )}
                      </span>

                      {!p.has_auction && (
                        <button
                          onClick={() => openAuctionModalForProduct(p)}
                          className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-md transition-colors"
                        >
                          Launch Auction
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Analytics */}
        {activeTab === 'analytics' && (
          <div className="p-6">
            <ActivityChart
              data={chartData}
              type="bar"
              dataKey="count"
              xKey="name"
              title="Auction Listings Status Breakdown"
            />
          </div>
        )}

        {activeTab === 'payment-setup' && (
          <div className="p-4 sm:p-6">
            <SellerPaymentSetupPanel
              setup={paymentSetup}
              isLoading={setupLoading}
              error={setupError}
              isSubmitting={setupSubmitting}
              onRetry={loadPaymentSetup}
              onComplete={handleCompleteSetup}
            />
          </div>
        )}

        {activeTab === 'payments' && (
          <div className="p-4 sm:p-6">
            <SellerPaymentsPanel />
          </div>
        )}
      </div>

      {/* Modal: Catalog New Product */}
      {showProductModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900">Catalog New Product</h3>
              <button
                onClick={() => setShowProductModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateProduct} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Item Title</label>
                <input
                  type="text"
                  required
                  value={productForm.title}
                  onChange={(e) => setProductForm({ ...productForm, title: e.target.value })}
                  placeholder="e.g. 1968 Vintage Mechanical Chronograph"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Description (Min 10 characters)</label>
                <textarea
                  required
                  rows={3}
                  minLength={10}
                  value={productForm.description}
                  onChange={(e) => setProductForm({ ...productForm, description: e.target.value })}
                  placeholder="Describe item condition, provenance, and specifications..."
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Category</label>
                  <select
                    required
                    value={productForm.category_id}
                    onChange={(e) => setProductForm({ ...productForm, category_id: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs bg-white"
                  >
                    <option value="">Select Category</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Condition</label>
                  <select
                    value={productForm.condition_status}
                    onChange={(e) => setProductForm({ ...productForm, condition_status: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs bg-white"
                  >
                    <option value="NEW">Brand New</option>
                    <option value="LIKE_NEW">Like New</option>
                    <option value="USED">Used / Pre-owned</option>
                    <option value="VINTAGE">Vintage / Collectible</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Image URL (HTTP/HTTPS URL)</label>
                <input
                  type="url"
                  required
                  value={productForm.image_url}
                  onChange={(e) => setProductForm({ ...productForm, image_url: e.target.value })}
                  placeholder="https://images.unsplash.com/photo-..."
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                />
              </div>

              <div className="pt-3 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowProductModal(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-bold disabled:opacity-50"
                >
                  {isSubmitting ? 'Saving...' : 'Catalog Product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Launch Auction */}
      {showAuctionModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900">
                Launch Auction for {selectedProductForAuction?.title}
              </h3>
              <button
                onClick={() => setShowAuctionModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateAuction} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Starting Price ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    value={auctionForm.starting_price}
                    onChange={(e) => setAuctionForm({ ...auctionForm, starting_price: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Reserve Price ($) (Optional)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={auctionForm.reserve_price}
                    onChange={(e) => setAuctionForm({ ...auctionForm, reserve_price: e.target.value })}
                    placeholder="Hidden from buyers"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Minimum Increment ($)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  required
                  value={auctionForm.minimum_increment}
                  onChange={(e) => setAuctionForm({ ...auctionForm, minimum_increment: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Start Time</label>
                  <input
                    type="datetime-local"
                    min={toLocalDateTimeInput(scheduleClock)}
                    required
                    value={auctionForm.start_time}
                    onChange={(e) => handleScheduleFieldChange('start_time', e.target.value)}
                    onInvalid={() => setScheduleError(validateAuctionSchedule(
                      auctionForm.start_time,
                      auctionForm.end_time,
                      new Date()
                    ))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">End Time</label>
                  <input
                    type="datetime-local"
                    min={getMinimumAuctionEnd(auctionForm.start_time, scheduleClock)}
                    required
                    value={auctionForm.end_time}
                    onChange={(e) => handleScheduleFieldChange('end_time', e.target.value)}
                    onInvalid={() => setScheduleError(validateAuctionSchedule(
                      auctionForm.start_time,
                      auctionForm.end_time,
                      new Date()
                    ))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                  />
                </div>
              </div>
              {scheduleError && (
                <p role="alert" className="text-xs font-medium text-rose-600">
                  {scheduleError}
                </p>
              )}

              <div className="pt-3 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowAuctionModal(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-bold disabled:opacity-50"
                >
                  {isSubmitting ? 'Launching...' : 'Publish Listing'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
