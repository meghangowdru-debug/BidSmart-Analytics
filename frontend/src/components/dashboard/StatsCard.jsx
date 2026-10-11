import React from 'react';

export const StatsCard = ({ title, value, subtitle, icon: Icon, color = 'indigo' }) => {
  const colorStyles = {
    indigo: 'bg-indigo-50 text-indigo-600 border-indigo-100',
    emerald: 'bg-emerald-50 text-emerald-600 border-emerald-100',
    amber: 'bg-amber-50 text-amber-600 border-amber-100',
    rose: 'bg-rose-50 text-rose-600 border-rose-100',
    purple: 'bg-purple-50 text-purple-600 border-purple-100',
  };

  const currentStyle = colorStyles[color] || colorStyles.indigo;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex items-center justify-between">
      <div>
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-1">
          {title}
        </span>
        <div className="text-2xl font-black text-slate-900 leading-none">
          {value}
        </div>
        {subtitle && <p className="text-xs text-slate-500 mt-1.5">{subtitle}</p>}
      </div>

      {Icon && (
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${currentStyle}`}>
          <Icon className="w-6 h-6" />
        </div>
      )}
    </div>
  );
};
