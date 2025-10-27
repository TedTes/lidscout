'use client';

import { useState } from 'react';
import { SearchCriteria } from '@/types/business';

interface SearchHeaderProps {
  onSearch: (criteria: SearchCriteria) => void;
  isLoading: boolean;
  resultsCount?: number;
}

export default function SearchHeader({ onSearch, isLoading, resultsCount }: SearchHeaderProps) {
  const [industry, setIndustry] = useState('');
  const [location, setLocation] = useState('');
  const [radiusKm, setRadiusKm] = useState(10);
  const [maxResults, setMaxResults] = useState(20);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!industry.trim() || !location.trim()) {
      alert('Please fill in both industry and location');
      return;
    }

    onSearch({
      industry: industry.trim(),
      location: location.trim(),
      radius_km: radiusKm,
      max_results: maxResults,
    });
  };

  const popularIndustries = [
    'Restaurants', 'Insurance', 'Real Estate', 'Plumbers', 'Dentists', 'Lawyers'
  ];

  return (
    <header className="bg-white shadow-md border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4">
        {/* Main Header Row */}
        <div className="flex flex-col md:flex-row items-start md:items-center gap-3 md:gap-0 md:justify-between py-3">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <div className="bg-gradient-to-br from-indigo-600 to-purple-600 p-2 rounded-lg">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                LidScout
              </h1>
            </div>
          </div>

          {/* Compact Search Form */}
          <form onSubmit={handleSubmit} className="w-full lg:flex-1 lg:max-w-4xl lg:mx-6">
          <div className="flex flex-col md:flex-row items-stretch md:items-center gap-2">
              {/* Industry Input */}
              <div className="w-full md:flex-1">
                <input
                  type="text"
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  placeholder="Industry (e.g., insurance brokers)"
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  disabled={isLoading}
                  required
                />
              </div>

              {/* Location Input */}
              <div className="w-full md:flex-1">
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="Location (e.g., Toronto)"
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  disabled={isLoading}
                  required
                />
              </div>

              {/* Search Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full md:w-auto px-4 py-1.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white text-sm font-semibold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg whitespace-nowrap"
              >
                {isLoading ? (
                  <span className="flex items-center">
                    <svg className="animate-spin h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span className="hidden sm:inline">Searching...</span>
                  </span>
                ) : (
                  <span className="flex items-center">
                    <svg className="w-4 h-4 sm:mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    <span className="hidden sm:inline">Search</span>
                  </span>
                )}
              </button>

              {/* Advanced Toggle */}
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="px-3 py-1.5 text-sm text-gray-600 hover:text-indigo-600 border border-gray-300 rounded-lg hover:border-indigo-500 transition-colors"
                title="Advanced Options"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                </svg>
              </button>
            </div>
          </form>

          {/* Results Count */}
          {resultsCount !== undefined && (
            <div className="hidden lg:flex items-center bg-indigo-50 px-4 py-2 rounded-lg">
              <span className="text-indigo-600 font-bold text-lg">{resultsCount}</span>
              <span className="text-gray-600 text-sm ml-2">leads</span>
            </div>
          )}
        </div>

        {/* Quick Select Row */}
        <div className="flex items-center justify-center gap-2 pb-3 overflow-x-auto">
  <span className="text-xs text-gray-500 font-medium whitespace-nowrap">Quick:</span>
          {popularIndustries.map((ind) => (
            <button
              key={ind}
              type="button"
              onClick={() => setIndustry(ind)}
              className="text-xs px-2 py-1 bg-gray-100 hover:bg-indigo-100 text-gray-700 hover:text-indigo-700 rounded-full transition-colors whitespace-nowrap"
              disabled={isLoading}
            >
              {ind}
            </button>
          ))}
        </div>

        {/* Advanced Options Dropdown */}
        {showAdvanced && (
          <div className="pb-3 pt-2 border-t border-gray-100">
            <div className="grid grid-cols-2 gap-4 max-w-2xl">
              {/* Radius */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Radius: <span className="font-semibold text-indigo-600">{radiusKm} km</span>
                </label>
                <input
                  type="range"
                  value={radiusKm}
                  onChange={(e) => setRadiusKm(Number(e.target.value))}
                  min="1"
                  max="50"
                  className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                  disabled={isLoading}
                />
              </div>

              {/* Max Results */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Max Results
                </label>
                <select
                  value={maxResults}
                  onChange={(e) => setMaxResults(Number(e.target.value))}
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  disabled={isLoading}
                >
                  <option value="10">10 results</option>
                  <option value="20">20 results</option>
                  <option value="30">30 results</option>
                  <option value="50">50 results</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
