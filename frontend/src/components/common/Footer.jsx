import React from 'react';
import { Link } from 'react-router-dom';
import { Gavel, Shield, Zap, Lock, HeartHandshake } from 'lucide-react';

export const Footer = () => {
  return (
    <footer className="mt-auto bg-slate-900 text-slate-400 border-t border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Brand Info */}
          <div className="md:col-span-1 space-y-3">
            <div className="flex items-center space-x-2 text-white font-bold text-lg">
              <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
                <Gavel className="w-4 h-4 text-white" />
              </div>
              <span>BidSmart</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Enterprise AI-Powered Online Auction Marketplace with pessimistic row-locked bidding, anti-sniping protection, and automated settlement workflows.
            </p>
            <div className="flex items-center space-x-2 text-[11px] text-slate-500 font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span>FastAPI Backend Connected</span>
            </div>
          </div>

          {/* Platform Links */}
          <div>
            <h4 className="text-xs font-semibold text-slate-200 uppercase tracking-wider mb-3">Marketplace</h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link to="/catalog" className="hover:text-white transition-colors">
                  Explore Active Auctions
                </Link>
              </li>
              <li>
                <Link to="/catalog?sort_by=ending_soon" className="hover:text-white transition-colors">
                  Ending Soon
                </Link>
              </li>
              <li>
                <Link to="/catalog?sort_by=most_bids" className="hover:text-white transition-colors">
                  Popular Lots
                </Link>
              </li>
            </ul>
          </div>

          {/* Role Portals */}
          <div>
            <h4 className="text-xs font-semibold text-slate-200 uppercase tracking-wider mb-3">Portals & Roles</h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link to="/dashboard/buyer" className="hover:text-white transition-colors">
                  Buyer Workspace & Bids
                </Link>
              </li>
              <li>
                <Link to="/dashboard/seller" className="hover:text-white transition-colors">
                  Seller Catalog & Listings
                </Link>
              </li>
              <li>
                <Link to="/dashboard/admin" className="hover:text-white transition-colors">
                  Administrative Governance
                </Link>
              </li>
            </ul>
          </div>

          {/* Security & Guarantees */}
          <div>
            <h4 className="text-xs font-semibold text-slate-200 uppercase tracking-wider mb-3">Security & Integrity</h4>
            <ul className="space-y-2 text-xs">
              <li className="flex items-center space-x-2">
                <Lock className="w-3.5 h-3.5 text-indigo-400" />
                <span>Pessimistic Concurrency</span>
              </li>
              <li className="flex items-center space-x-2">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span>60s Anti-Sniping Buffer</span>
              </li>
              <li className="flex items-center space-x-2">
                <Shield className="w-3.5 h-3.5 text-emerald-400" />
                <span>Zero-Trust Reserve Masking</span>
              </li>
              <li className="flex items-center space-x-2">
                <HeartHandshake className="w-3.5 h-3.5 text-sky-400" />
                <span>Simulated Demo Settlement</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 mt-8 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500">
          <p>© {new Date().getFullYear()} BidSmart Analytics Engine. All rights reserved.</p>
          <div className="flex space-x-4 mt-4 sm:mt-0 font-mono text-[11px]">
            <span>REST API v1.0</span>
            <span>•</span>
            <span>FastAPI + MySQL + React 19</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
