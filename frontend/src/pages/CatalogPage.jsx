import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { auctionsApi } from '../api/auctions';
import { categoriesApi } from '../api/categories';
import { AuctionCard } from '../components/auctions/AuctionCard';
import { AuctionFilters } from '../components/auctions/AuctionFilters';
import { Pagination } from '../components/common/Pagination';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorAlert } from '../components/common/ErrorAlert';

export const CatalogPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Extract initial filters from URL query parameters
  const getFiltersFromUrl = useCallback(() => ({
    search: searchParams.get('search') || '',
    category_id: searchParams.get('category_id') ? Number(searchParams.get('category_id')) : undefined,
    status_filter: searchParams.get('status_filter') || 'ACTIVE',
    condition: searchParams.get('condition') || undefined,
    sort_by: searchParams.get('sort_by') || 'ending_soon',
    page: searchParams.get('page') ? Number(searchParams.get('page')) : 1,
    page_size: 12,
  }), [searchParams]);

  const [filters, setFilters] = useState(getFiltersFromUrl);
  const [categories, setCategories] = useState([]);
  const [auctionData, setAuctionData] = useState({ items: [], total: 0, pages: 1 });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load categories taxonomy once
  useEffect(() => {
    let isMounted = true;
    const fetchCats = async () => {
      try {
        const cats = await categoriesApi.listCategories();
        if (isMounted) setCategories(cats || []);
      } catch (err) {
        console.error('Failed to load categories:', err);
      }
    };
    fetchCats();
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch auctions whenever filters change
  useEffect(() => {
    let isMounted = true;
    const fetchAuctions = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const cleanParams = { ...filters };
        // Remove empty/undefined params
        Object.keys(cleanParams).forEach((k) => {
          if (cleanParams[k] === undefined || cleanParams[k] === '') {
            delete cleanParams[k];
          }
        });

        const data = await auctionsApi.listAuctions(cleanParams);
        if (isMounted) {
          setAuctionData(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || 'Failed to retrieve auction catalog.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchAuctions();
    return () => {
      isMounted = false;
    };
  }, [filters]);

  // Sync state changes back to URL search params
  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    const newParams = {};
    if (newFilters.search) newParams.search = newFilters.search;
    if (newFilters.category_id) newParams.category_id = newFilters.category_id;
    if (newFilters.status_filter && newFilters.status_filter !== 'ACTIVE') newParams.status_filter = newFilters.status_filter;
    if (newFilters.condition) newParams.condition = newFilters.condition;
    if (newFilters.sort_by && newFilters.sort_by !== 'ending_soon') newParams.sort_by = newFilters.sort_by;
    if (newFilters.page && newFilters.page > 1) newParams.page = newFilters.page;
    setSearchParams(newParams);
  };

  const handleResetFilters = () => {
    const defaultFilters = {
      search: '',
      category_id: undefined,
      status_filter: 'ACTIVE',
      condition: undefined,
      sort_by: 'ending_soon',
      page: 1,
      page_size: 12,
    };
    setFilters(defaultFilters);
    setSearchParams({});
  };

  const handlePageChange = (newPage) => {
    handleFilterChange({ ...filters, page: newPage });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">
          Auction Marketplace Catalog
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Browse active, upcoming, and completed lots with live price updates and verified provenance.
        </p>
      </div>

      {/* Filter Component */}
      <AuctionFilters
        filters={filters}
        categories={categories}
        onFilterChange={handleFilterChange}
        onReset={handleResetFilters}
      />

      {error && <ErrorAlert message={error} onClose={() => setError(null)} />}

      {/* Results Header */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs text-slate-500 font-medium">
          Showing <span className="font-bold text-slate-800">{auctionData.items?.length || 0}</span> of{' '}
          <span className="font-bold text-slate-800">{auctionData.total || 0}</span> total auctions
        </span>
      </div>

      {/* Auction Grid */}
      {isLoading ? (
        <LoadingSpinner message="Searching marketplace lots..." />
      ) : auctionData.items?.length === 0 ? (
        <EmptyState
          title="No auctions found"
          description="We couldn't find any listings matching your search criteria. Try modifying your filters or clear them to see all lots."
          action={
            <button
              onClick={handleResetFilters}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 transition-colors"
            >
              Clear All Filters
            </button>
          }
        />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {auctionData.items.map((auction) => (
              <AuctionCard key={auction.id} auction={auction} />
            ))}
          </div>

          {/* Pagination */}
          <Pagination
            currentPage={filters.page || 1}
            totalPages={auctionData.pages || 1}
            totalItems={auctionData.total}
            onPageChange={handlePageChange}
          />
        </>
      )}
    </div>
  );
};
