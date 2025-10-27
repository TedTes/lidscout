'use client';

/**
 * Search form component for business criteria input.
 * Following Single Responsibility Principle - only handles form UI and validation.
 */
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

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-2xl font-bold mb-4 text-gray-800">Search Businesses</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label htmlFor="industry" className="block text-sm font-medium text-gray-700 mb-1">
            Industry / Business Type *
          </label>
          <input
            type="text"
            id="industry"
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            placeholder="e.g., restaurants, plumbers, dentists"
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading}
            required
          />
        </div>

        <div>
          <label htmlFor="location" className="block text-sm font-medium text-gray-700 mb-1">
            Location *
          </label>
          <input
            type="text"
            id="location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g., New York, NY"
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading}
            required
          />
        </div>

        <div>
          <label htmlFor="radius" className="block text-sm font-medium text-gray-700 mb-1">
            Radius (km)
          </label>
          <input
            type="number"
            id="radius"
            value={radiusKm}
            onChange={(e) => setRadiusKm(Number(e.target.value))}
            min="1"
            max="100"
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading}
          />
        </div>

        <div>
          <label htmlFor="maxResults" className="block text-sm font-medium text-gray-700 mb-1">
            Max Results
          </label>
          <input
            type="number"
            id="maxResults"
            value={maxResults}
            onChange={(e) => setMaxResults(Number(e.target.value))}
            min="1"
            max="100"
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading}
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="w-full bg-blue-600 text-white py-3 px-6 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
      >
        {isLoading ? 'Searching...' : 'Search Businesses'}
      </button>
    </form>
  );
}