import React from 'react';
import { AlertCircle, X } from 'lucide-react';

export const ErrorAlert = ({ message, onClose }) => {
  if (!message) return null;

  return (
    <div
      className="flex items-start justify-between p-4 mb-4 text-sm text-rose-800 bg-rose-50 border border-rose-200 rounded-lg"
      role="alert"
      aria-atomic="true"
    >
      <div className="flex items-start space-x-3">
        <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
        <span className="font-medium leading-relaxed">{message}</span>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="text-rose-400 hover:text-rose-600 ml-3 p-0.5 rounded transition-colors"
          aria-label="Dismiss error"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
