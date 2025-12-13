'use client';

import { AlertCircle, AlertTriangle, CheckCircle2 } from 'lucide-react';
import type { ValidationError } from '@/lib/api';

interface ValidationPanelProps {
  isValid: boolean | null;
  errors: ValidationError[];
  warnings: ValidationError[];
  isLoading: boolean;
}

export default function ValidationPanel({
  isValid,
  errors,
  warnings,
  isLoading,
}: ValidationPanelProps) {
  if (isLoading) {
    return (
      <div className="p-4 text-gray-400 text-sm">
        Validating...
      </div>
    );
  }

  if (isValid === null) {
    return (
      <div className="p-4 text-gray-500 text-sm">
        Enter a PSDL scenario to validate
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Status header */}
      <div className="flex items-center gap-2">
        {isValid ? (
          <>
            <CheckCircle2 className="w-5 h-5 text-green-500" />
            <span className="text-green-500 font-medium">Valid</span>
          </>
        ) : (
          <>
            <AlertCircle className="w-5 h-5 text-red-500" />
            <span className="text-red-500 font-medium">Invalid</span>
          </>
        )}
        {warnings.length > 0 && (
          <span className="text-yellow-500 text-sm ml-2">
            ({warnings.length} warning{warnings.length !== 1 ? 's' : ''})
          </span>
        )}
      </div>

      {/* Errors */}
      {errors.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-red-400">Errors</h3>
          <ul className="space-y-1">
            {errors.map((error, index) => (
              <li key={index} className="flex items-start gap-2 text-sm">
                <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                <div>
                  {error.line && (
                    <span className="text-gray-500">Line {error.line}: </span>
                  )}
                  <span className="text-red-400">{error.message}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-yellow-400">Warnings</h3>
          <ul className="space-y-1">
            {warnings.map((warning, index) => (
              <li key={index} className="flex items-start gap-2 text-sm">
                <AlertTriangle className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                <div>
                  {warning.line && (
                    <span className="text-gray-500">Line {warning.line}: </span>
                  )}
                  <span className="text-yellow-400">{warning.message}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Success message when valid with no warnings */}
      {isValid && errors.length === 0 && warnings.length === 0 && (
        <p className="text-sm text-gray-400">
          Scenario is valid with no warnings.
        </p>
      )}
    </div>
  );
}
