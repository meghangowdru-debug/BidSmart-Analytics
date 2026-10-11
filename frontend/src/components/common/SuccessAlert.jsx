import React from 'react';
import { CheckCircle2, X } from 'lucide-react';

export const SuccessAlert = ({ message, onClose }) => {
  if (!message) return null;

  return (
    <div className="flex items-start justify-between p-4 mb-4 text-sm text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg">
      <div className="flex items-start space-x-3">
        <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
        <span className="font-medium leading-relaxed">{message}</span>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="text-emerald-400 hover:text-emerald-600 ml-3 p-0.5 rounded transition-colors"
          aria-label="Dismiss success message"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
