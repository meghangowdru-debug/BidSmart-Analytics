import React from 'react';

export const StatusBadge = ({ status }) => {
  const normalized = (status || '').toUpperCase();

  const styles = {
    ACTIVE: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    SCHEDULED: 'bg-blue-100 text-blue-800 border-blue-300',
    COMPLETED: 'bg-purple-100 text-purple-800 border-purple-300',
    UNSOLD: 'bg-slate-100 text-slate-700 border-slate-300',
    RESERVE_NOT_MET: 'bg-amber-100 text-amber-800 border-amber-300',
    CANCELLED: 'bg-rose-100 text-rose-800 border-rose-300',
  };

  const labels = {
    ACTIVE: 'Active',
    SCHEDULED: 'Upcoming',
    COMPLETED: 'Completed',
    UNSOLD: 'Unsold',
    RESERVE_NOT_MET: 'Reserve Not Met',
    CANCELLED: 'Cancelled',
  };

  const styleClass = styles[normalized] || 'bg-slate-100 text-slate-800 border-slate-300';
  const labelText = labels[normalized] || normalized;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styleClass}`}
    >
      <span
        className={`w-1.5 h-1.5 mr-1.5 rounded-full ${
          normalized === 'ACTIVE'
            ? 'bg-emerald-500 animate-pulse'
            : normalized === 'COMPLETED'
            ? 'bg-purple-500'
            : normalized === 'CANCELLED'
            ? 'bg-rose-500'
            : 'bg-slate-400'
        }`}
      />
      {labelText}
    </span>
  );
};

export const RoleBadge = ({ role }) => {
  const normalized = (role || '').toUpperCase();

  const styles = {
    ADMIN: 'bg-rose-100 text-rose-800 border-rose-300',
    SELLER: 'bg-indigo-100 text-indigo-800 border-indigo-300',
    BUYER: 'bg-cyan-100 text-cyan-800 border-cyan-300',
  };

  const styleClass = styles[normalized] || 'bg-slate-100 text-slate-800 border-slate-300';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider border ${styleClass}`}>
      {normalized}
    </span>
  );
};

export const ConditionBadge = ({ condition }) => {
  const normalized = (condition || '').toUpperCase();

  const labels = {
    NEW: 'Brand New',
    LIKE_NEW: 'Like New',
    USED: 'Used / Pre-owned',
    VINTAGE: 'Vintage / Collectible',
  };

  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
      {labels[normalized] || normalized}
    </span>
  );
};
