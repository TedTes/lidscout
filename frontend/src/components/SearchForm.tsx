'use client';

import { useState } from 'react';
import { SearchCriteria } from '@/types/business';

interface SearchFormProps {
  onSearch: (criteria: SearchCriteria) => void;
  isLoading: boolean;
}

export default function SearchForm({ onSearch, isLoading }: SearchFormProps) {
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
    'Restaurants', 'Insurance Brokers', 'Real Estate Agents', 
    'Plumbers', 'Dentists', 'Law Firms'
  ];

  return (
    <div className="bg-white rounded-xl shadow-md border border-gray-200 mb-6">
      <form onSubmit={handleSubmit} className="p-6">
        {/* Compact Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-gray-800">Find Your Leads</h2>
            <p className="text-xs text-gray-600">Search by industry and location</p>
          </div>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
          >
            {showAdvanced ? '− Less' : '+ Advanced'}
          </button>
        </div>
        
        {/* Compact Main Search - Single Row */}
        <div className="flex flex-col md:flex-row gap-3 mb-3">
          {/* Industry */}
          <div className="flex-1">
            <label htmlFor="industry" className="block text-xs font-semibold text-gray-700 mb-1">
              Industry *
            </label>
            <input
              type="text"
              id="industry"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              placeholder="e.g., insurance brokers"
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              disabled={isLoading}
              required
            />
          </div>

          {/* Location */}
          <div className="flex-1">
            <label htmlFor="location" className="block text-xs font-semibold text-gray-700 mb-1">
              Location *
            </label>
            <input
              type="text"
              id="location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g., Toronto"
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              disabled={isLoading}
              required
            />
          </div>

          {/* Search Button - Inline */}
          <div className="flex items-end">
            <button
              type="submit"
              disabled={isLoading}
              className="px-6 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white text-sm font-semibold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg whitespace-nowrap h-[38px]"
            >
              {isLoading ? (
                <span className="flex items-center">
                  <svg className="animate-spin h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Searching...
                </span>
              ) : (
                <span className="flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  Search
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Quick Select Buttons - Compact */}
        <div className="flex flex-wrap gap-2 mb-3">
          {popularIndustries.map((ind) => (
            <button
              key={ind}
              type="button"
              onClick={() => setIndustry(ind)}
              className="text-xs px-3 py-1 bg-gray-100 hover:bg-indigo-100 text-gray-700 hover:text-indigo-700 rounded-full transition-colors"
              disabled={isLoading}
            >
              {ind}
            </button>
          ))}
        </div>

        {/* Advanced Options - Collapsible */}
        {showAdvanced && (
          <div className="pt-3 border-t border-gray-200">
            <div className="grid grid-cols-2 gap-4">
              {/* Radius */}
              <div>
                <label htmlFor="radius" className="block text-xs font-medium text-gray-700 mb-2">
                  Radius: <span className="font-semibold text-indigo-600">{radiusKm} km</span>
                </label>
                <input
                  type="range"
                  id="radius"
                  value={radiusKm}
                  onChange={(e) => setRadiusKm(Number(e.target.value))}
                  min="1"
                  max="50"
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                  disabled={isLoading}
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>1 km</span>
                  <span>50 km</span>
                </div>
              </div>

              {/* Max Results */}
              <div>
                <label htmlFor="maxResults" className="block text-xs font-medium text-gray-700 mb-2">
                  Max Results
                </label>
                <select
                  id="maxResults"
                  value={maxResults}
                  onChange={(e) => setMaxResults(Number(e.target.value))}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  disabled={isLoading}
                >
                  <option value="10">10 results</option>
                  <option value="20">20 results</option>
                  <option value="30">30 results</option>
                  <option value="50">50 results</option>
                  <option value="100">100 results</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}