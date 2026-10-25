import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Gavel,
  Shield,
  Zap,
  TrendingUp,
  Clock,
  ArrowRight,
  Layers,
  Sparkles,
  Award,
} from 'lucide-react';
import { auctionsApi } from '../api/auctions';
import { categoriesApi } from '../api/categories';
import { AuctionCard } from '../components/auctions/AuctionCard';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const HomePage = () => {
  const [featuredAuctions, setFeaturedAuctions] = useState([]);
  const [popularAuctions, setPopularAuctions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const loadHomeData = async () => {
      try {
        const [endingSoonData, popularData, categoriesData] = await Promise.all([
          auctionsApi.listAuctions({ status_filter: 'ACTIVE', sort_by: 'ending_soon', page_size: 4 }),
          auctionsApi.listAuctions({ status_filter: 'ACTIVE', sort_by: 'most_bids', page_size: 4 }),
          categoriesApi.listCategories(),
        ]);

        if (isMounted) {
          setFeaturedAuctions(endingSoonData.items || []);
          setPopularAuctions(popularData.items || []);
          setCategories(categoriesData || []);
        }
      } catch (err) {
        console.error('Failed to load homepage data:', err);
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadHomeData();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="space-y-16 pb-16">
      {/* Hero Banner */}
      <section className="relative overflow-hidden bg-gradient-to-b from-indigo-950 via-slate-900 to-slate-900 text-white py-20 px-4 sm:px-6 lg:px-8 border-b border-slate-800">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(99,102,241,0.15),transparent_50%)]" />
        <div className="relative max-w-5xl mx-auto text-center space-y-6">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-semibold backdrop-blur">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Enterprise Auction Intelligence Platform</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight leading-tight">
            Fair, Transparent & <br className="hidden sm:inline" />
            <span className="bg-gradient-to-r from-indigo-400 via-sky-300 to-indigo-300 bg-clip-text text-transparent">
              High-Velocity Online Auctions
            </span>
          </h1>

          <p className="max-w-2xl mx-auto text-base sm:text-lg text-slate-300 font-normal leading-relaxed">
            Experience atomic pessimistic row-locked bidding, automated 60-second anti-sniping protection, and zero-trust reserve masking built for enterprise integrity.
          </p>

          <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/catalog"
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-6 py-3.5 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-600/30 transition-all hover:scale-[1.02]"
            >
              <Gavel className="w-4 h-4" />
              <span>Explore Live Auctions</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Link>
            <Link
              to="/register"
              className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3.5 rounded-xl font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-all"
            >
              <span>Create Free Account</span>
            </Link>
          </div>

          {/* Quick Metrics Bar */}
          <div className="pt-10 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto text-center border-t border-slate-800/80">
            <div className="p-3">
              <div className="text-2xl font-black text-indigo-400 font-mono">100%</div>
              <div className="text-xs text-slate-400 font-medium mt-0.5">ACID Concurrency</div>
            </div>
            <div className="p-3">
              <div className="text-2xl font-black text-amber-400 font-mono">60s</div>
              <div className="text-xs text-slate-400 font-medium mt-0.5">Anti-Sniping Buffer</div>
            </div>
            <div className="p-3">
              <div className="text-2xl font-black text-emerald-400 font-mono">Zero</div>
              <div className="text-xs text-slate-400 font-medium mt-0.5">Reserve Price Leaks</div>
            </div>
            <div className="p-3">
              <div className="text-2xl font-black text-sky-400 font-mono">REST</div>
              <div className="text-xs text-slate-400 font-medium mt-0.5">Live Polling Engine</div>
            </div>
          </div>
        </div>
      </section>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-16">
        {/* Categories Section */}
        {categories.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-black text-slate-900 tracking-tight">Browse by Category</h2>
                <p className="text-xs text-slate-500">Find items curated across verified marketplace taxonomies</p>
              </div>
              <Link
                to="/catalog"
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 inline-flex items-center"
              >
                <span>View All</span>
                <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </Link>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {categories.map((c) => (
                <Link
                  key={c.id}
                  to={`/catalog?category_id=${c.id}`}
                  className="group bg-white p-4 rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all text-center flex flex-col items-center"
                >
                  <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center mb-2.5 group-hover:scale-110 transition-transform">
                    <Layers className="w-5 h-5" />
                  </div>
                  <span className="text-xs font-bold text-slate-800 group-hover:text-indigo-600 transition-colors line-clamp-1">
                    {c.name}
                  </span>
                  <span className="text-[11px] text-slate-400 mt-0.5">
                    {c.item_count || 0} listings
                  </span>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Ending Soonest Section */}
        <section>
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-2">
              <Clock className="w-5 h-5 text-amber-500" />
              <div>
                <h2 className="text-xl font-black text-slate-900 tracking-tight">Ending Soonest</h2>
                <p className="text-xs text-slate-500">Live auctions in their final hours and minutes</p>
              </div>
            </div>
            <Link
              to="/catalog?sort_by=ending_soon"
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 inline-flex items-center"
            >
              <span>See more</span>
              <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Link>
          </div>

          {isLoading ? (
            <LoadingSpinner message="Fetching live auctions..." />
          ) : featuredAuctions.length === 0 ? (
            <div className="p-8 text-center bg-white rounded-xl border border-slate-200 text-sm text-slate-500">
              No active auctions ending soon. Check back shortly!
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {featuredAuctions.map((auction) => (
                <AuctionCard key={auction.id} auction={auction} />
              ))}
            </div>
          )}
        </section>

        {/* Most Popular / Most Bids Section */}
        <section>
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-indigo-600" />
              <div>
                <h2 className="text-xl font-black text-slate-900 tracking-tight">Most Popular Auctions</h2>
                <p className="text-xs text-slate-500">High-interest lots with active bidding momentum</p>
              </div>
            </div>
            <Link
              to="/catalog?sort_by=most_bids"
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 inline-flex items-center"
            >
              <span>See more</span>
              <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Link>
          </div>

          {isLoading ? (
            <LoadingSpinner message="Fetching popular auctions..." />
          ) : popularAuctions.length === 0 ? (
            <div className="p-8 text-center bg-white rounded-xl border border-slate-200 text-sm text-slate-500">
              No popular lots listed yet.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {popularAuctions.map((auction) => (
                <AuctionCard key={auction.id} auction={auction} />
              ))}
            </div>
          )}
        </section>

        {/* Platform Pillars / Trust Callout */}
        <section className="bg-slate-900 text-white rounded-2xl p-8 lg:p-12">
          <div className="max-w-3xl mb-8">
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider">Engine Architecture</span>
            <h3 className="text-2xl lg:text-3xl font-black tracking-tight mt-1 mb-2">
              Engineered for Fairness & Zero Front-Running
            </h3>
            <p className="text-sm text-slate-300 leading-relaxed">
              BidSmart implements strict database safeguards to eliminate race conditions, last-second bid bot snipes, and unfair seller manipulation.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-5 space-y-2">
              <div className="w-9 h-9 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
                <Shield className="w-5 h-5" />
              </div>
              <h4 className="text-sm font-bold text-white">Pessimistic Concurrency</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Row-level database locks ensure all competing bids are evaluated sequentially, eliminating race conditions.
              </p>
            </div>

            <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-5 space-y-2">
              <div className="w-9 h-9 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center">
                <Zap className="w-5 h-5" />
              </div>
              <h4 className="text-sm font-bold text-white">Anti-Sniping Buffer</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Any valid bid submitted in the closing 30 seconds automatically adds 60 seconds to allow human response.
              </p>
            </div>

            <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-5 space-y-2">
              <div className="w-9 h-9 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                <Award className="w-5 h-5" />
              </div>
              <h4 className="text-sm font-bold text-white">Confidential Reserves</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Seller reserve limits remain strictly hidden from competing buyers to guarantee organic price discovery.
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
