import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
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
  DollarSign,
  Layers,
  X,
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
import { getErrorMessage } from '../api/client';
import { canCloseAuction, canCancelAuction } from '../utils/auctionActions';

export const SellerDashboardPage = () => {
  const { user } = useAuth();

  const [activeTab, setActiveTab] = useState('auctions'); // 'auctions' | 'products' | 'analytics'
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

  const [auctionForm, setAuctionForm] = useState({
    product_id: '',
    starting_price: '10.00',
    reserve_price: '20.00',
    minimum_increment: '1.00',
    start_time: new Date().toISOString().slice(0, 16),
    end_time: new Date(Date.now() + 86400000 * 3).toISOString().slice(0, 16),
  });

  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadSellerData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [aucRes, prodRes, catRes] = await Promise.all([
        auctionsApi.listMyAuctions({ page_size: 50 }),
        productsApi.listProducts({ seller_id: user?.id, page_size: 50 }),
        categoriesApi.listCategories(),
      ]);
      setAuctions(aucRes.items || []);
      setProducts(prodRes.items || []);
      setCategories(catRes || []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    loadSellerData();
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
      loadSellerData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Auction launch submission
  const handleCreateAuction = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await auctionsApi.createAuction({
        product_id: Number(auctionForm.product_id),
        starting_price: Number(auctionForm.starting_price),
        reserve_price: auctionForm.reserve_price ? Number(auctionForm.reserve_price) : undefined,
        minimum_increment: Number(auctionForm.minimum_increment),
        start_time: new Date(auctionForm.start_time).toISOString(),
        end_time: new Date(auctionForm.end_time).toISOString(),
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

  const openAuctionModalForProduct = (product) => {
    setSelectedProductForAuction(product);
    setAuctionForm((prev) => ({
      ...prev,
      product_id: product.id,
    }));
    setShowAuctionModal(true);
  };

  // Computations
  const activeAuctions = auctions.filter((a) => a.status === 'ACTIVE');
  const completedAuctions = auctions.filter((a) => a.status === 'COMPLETED');
  const totalRevenue = completedAuctions.reduce(
    (acc, a) => acc + Number(a.current_highest_bid || 0),
    0
  );

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
            onClick={() => setShowProductModal(true)}
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
          title="Completed Sales"
          value={completedAuctions.length}
          subtitle="Successfully settled items"
          icon={CheckCircle2}
          color="emerald"
        />
        <StatsCard
          title="Total Gross Volume"
          value={`$${totalRevenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          subtitle="Simulated settlement value"
          icon={DollarSign}
          color="amber"
        />
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="border-b border-slate-200 flex space-x-6 px-6 pt-4">
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
                    onClick={() => setShowProductModal(true)}
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
                    onClick={() => setShowProductModal(true)}
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
                    required
                    value={auctionForm.start_time}
                    onChange={(e) => setAuctionForm({ ...auctionForm, start_time: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">End Time</label>
                  <input
                    type="datetime-local"
                    required
                    value={auctionForm.end_time}
                    onChange={(e) => setAuctionForm({ ...auctionForm, end_time: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                  />
                </div>
              </div>

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
