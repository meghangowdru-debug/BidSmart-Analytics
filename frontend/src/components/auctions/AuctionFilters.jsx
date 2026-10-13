import React from 'react';
import { Search, Filter, RotateCcw } from 'lucide-react';

export const AuctionFilters = ({
  filters,
  categories = [],
  onFilterChange,
  onReset,
}) => {
  const handleChange = (key, value) => {
    onFilterChange({ ...filters, [key]: value, page: 1 });
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm mb-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {/* Search input */}
        <div className="lg:col-span-2 relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            placeholder="Search auctions by title or keyword..."
            value={filters.search || ''}
            onChange={(e) => handleChange('search', e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {/* Category Dropdown */}
        <div>
          <select
            value={filters.category_id || ''}
            onChange={(e) => handleChange('category_id', e.target.value || undefined)}
            className="w-full py-2 px-3 text-xs rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} {c.item_count !== undefined ? `(${c.item_count})` : ''}
              </option>
            ))}
          </select>
        </div>

        {/* Status Filter */}
        <div>
          <select
            value={filters.status_filter || 'AVAILABLE'}
            onChange={(e) => handleChange('status_filter', e.target.value)}
            className="w-full py-2 px-3 text-xs rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="AVAILABLE">Status: Active & Upcoming</option>
            <option value="ACTIVE">Status: Active Only</option>
            <option value="SCHEDULED">Status: Upcoming Only</option>
            <option value="COMPLETED">Status: Completed</option>
            <option value="ALL">Status: All Statuses</option>
          </select>
        </div>

        {/* Sort Order */}
        <div>
          <select
            value={filters.sort_by || 'ending_soon'}
            onChange={(e) => handleChange('sort_by', e.target.value)}
            className="w-full py-2 px-3 text-xs rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="ending_soon">Sort: Ending Soonest</option>
            <option value="ending_latest">Sort: Ending Latest</option>
            <option value="price_asc">Sort: Price (Low to High)</option>
            <option value="price_desc">Sort: Price (High to Low)</option>
            <option value="most_bids">Sort: Most Bids</option>
            <option value="newest">Sort: Newly Listed</option>
          </select>
        </div>
      </div>

      {/* Filter Row 2: Condition + Reset */}
      <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2 text-xs">
          <span className="text-slate-400 font-medium">Condition:</span>
          {['ALL', 'NEW', 'LIKE_NEW', 'USED', 'VINTAGE'].map((cond) => {
            const isSelected = (!filters.condition && cond === 'ALL') || filters.condition === cond;
            return (
              <button
                key={cond}
                type="button"
                onClick={() => handleChange('condition', cond === 'ALL' ? undefined : cond)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                  isSelected
                    ? 'bg-indigo-600 text-white font-semibold'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {cond.replace('_', ' ')}
              </button>
            );
          })}
        </div>

        <button
          type="button"
          onClick={onReset}
          className="inline-flex items-center space-x-1 text-xs text-slate-500 hover:text-slate-800 transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Filters</span>
        </button>
      </div>
    </div>
  );
};
