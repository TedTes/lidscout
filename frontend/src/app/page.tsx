'use client';

/**
 * Main page component.
 * Integrates SearchForm and BusinessTable components.
 */
import { useState } from 'react';
import SearchForm from '@/components/SearchForm';
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
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Business Scraper
          </h1>
          <p className="text-gray-600">
            Find local businesses with contact information
          </p>
        </header>

        <SearchForm onSearch={handleSearch} isLoading={isLoading} />

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            <strong>Error:</strong> {error}
          </div>
        )}

        {searchResults && (
          <BusinessTable
            businesses={searchResults.businesses}
            query={searchResults.query}
          />
        )}

        {!searchResults && !isLoading && !error && (
          <div className="bg-white rounded-lg shadow-md p-12 text-center">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-xl font-semibold text-gray-700 mb-2">
              Ready to Search
            </h3>
            <p className="text-gray-500">
              Enter your search criteria above to find businesses
            </p>
          </div>
        )}
      </div>
    </main>
  );
}