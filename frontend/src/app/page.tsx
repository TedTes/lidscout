'use client';

/**
 * LidScout - Lead Generation Tool
 * Compact search in header
 */
import { useState } from 'react';
import SearchHeader from '@/components/SearchHeader';
import BusinessTable from '@/components/BusinessTable';
import { businessApi } from '@/services/api';
import { SearchCriteria, SearchResponse } from '@/types/business';

export default function Home() {
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (criteria: SearchCriteria) => {
    setIsLoading(true);
    setError(null);

    try {
      const results = await businessApi.searchBusinesses(criteria);
      setSearchResults(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setSearchResults(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      {/* Compact Header with Search */}
      <SearchHeader 
        onSearch={handleSearch} 
        isLoading={isLoading}
        resultsCount={searchResults?.total_results}
      />

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Error Message */}
        {error && (
          <div className="mb-4 bg-red-50 border-l-4 border-red-500 p-4 rounded-lg shadow-sm">
            <div className="flex items-start">
              <svg className="w-5 h-5 text-red-500 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Search Error</h3>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="bg-white rounded-xl shadow-lg p-12 text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-indigo-200 border-t-indigo-600 mb-4"></div>
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Searching for leads...</h3>
            <p className="text-gray-600">This may take a few seconds</p>
          </div>
        )}

        {/* Results */}
        {searchResults && !isLoading && (
          <BusinessTable
            businesses={searchResults.businesses}
            query={searchResults.query}
          />
        )}

        {/* Empty State */}
        {!searchResults && !isLoading && !error && (
          <div className="bg-white rounded-xl shadow-lg p-12 text-center">
            <div className="max-w-md mx-auto">
              <div className="bg-gradient-to-br from-indigo-100 to-purple-100 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6">
                <svg className="w-10 h-10 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold text-gray-800 mb-3">
                Ready to Find Your Next Leads?
              </h3>
              <p className="text-gray-600 mb-6">
                Enter your target industry and location in the search bar above to discover businesses with verified contact information.
              </p>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl mb-2">🎯</div>
                  <div className="font-semibold text-gray-800">Targeted</div>
                  <div className="text-gray-600 text-xs">Find exact matches</div>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl mb-2">📞</div>
                  <div className="font-semibold text-gray-800">Verified</div>
                  <div className="text-gray-600 text-xs">Real phone numbers</div>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="text-2xl mb-2">⚡</div>
                  <div className="font-semibold text-gray-800">Fast</div>
                  <div className="text-gray-600 text-xs">Results in seconds</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="mt-16 border-t border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <p>© 2024 LidScout. All rights reserved.</p>
            <div className="flex items-center space-x-4">
              <a href="#" className="hover:text-indigo-600 transition-colors">About</a>
              <a href="#" className="hover:text-indigo-600 transition-colors">Privacy</a>
              <a href="#" className="hover:text-indigo-600 transition-colors">Terms</a>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}