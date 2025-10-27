'use client';

import { Business } from '@/types/business';
import { useState } from 'react';

interface BusinessTableProps {
  businesses: Business[];
  query: string;
}

export default function BusinessTable({ businesses, query }: BusinessTableProps) {
  const [selectedBusinesses, setSelectedBusinesses] = useState<Set<number>>(new Set());

  if (businesses.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-8 text-center border border-gray-100">
        <div className="text-6xl mb-4">🔍</div>
        <h3 className="text-xl font-semibold text-gray-800 mb-2">No Results Found</h3>
        <p className="text-gray-600">Try adjusting your search criteria or location</p>
      </div>
    );
  }

  const handleCall = (phone: string) => {
    window.location.href = `tel:${phone}`;
  };

  const handleEmail = (email: string) => {
    window.location.href = `mailto:${email}`;
  };

  const toggleSelect = (index: number) => {
    const newSelected = new Set(selectedBusinesses);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedBusinesses(newSelected);
  };

  const selectAll = () => {
    if (selectedBusinesses.size === businesses.length) {
      setSelectedBusinesses(new Set());
    } else {
      setSelectedBusinesses(new Set(businesses.map((_, i) => i)));
    }
  };

  const exportSelected = () => {
    const selected = businesses.filter((_, i) => selectedBusinesses.has(i));
    const csv = [
      ['Name', 'Phone', 'Email', 'Address', 'Rating', 'Reviews'],
      ...selected.map(b => [
        b.name,
        b.phone || '',
        b.email || '',
        b.address || '',
        b.rating?.toString() || '',
        b.reviews_count?.toString() || ''
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `lidscout-leads-${Date.now()}.csv`;
    a.click();
  };

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-100">
      {/* Header */}
      <div className="px-6 py-4 bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-800 mb-1">
              Search Results
            </h2>
            <p className="text-sm text-gray-600">{query}</p>
          </div>
          <div className="flex items-center space-x-3">
            <div className="bg-white px-4 py-2 rounded-lg shadow-sm border border-gray-200">
              <span className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                {businesses.length}
              </span>
              <span className="text-sm text-gray-600 ml-2">leads</span>
            </div>
          </div>
        </div>

        {/* Bulk Actions */}
        {selectedBusinesses.size > 0 && (
          <div className="mt-4 flex items-center justify-between bg-white rounded-lg p-3 border border-indigo-200">
            <span className="text-sm font-medium text-gray-700">
              {selectedBusinesses.size} selected
            </span>
            <div className="flex space-x-2">
              <button
                onClick={exportSelected}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                📥 Export Selected
              </button>
              <button
                onClick={() => setSelectedBusinesses(new Set())}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 text-sm font-medium rounded-lg transition-colors"
              >
                Clear
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-4 text-left">
                <input
                  type="checkbox"
                  checked={selectedBusinesses.size === businesses.length}
                  onChange={selectAll}
                  className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                />
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Business
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Contact
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Location
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Rating
              </th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {businesses.map((business, index) => (
              <tr key={index} className="hover:bg-gray-50 transition-colors">
                {/* Checkbox */}
                <td className="px-6 py-4">
                  <input
                    type="checkbox"
                    checked={selectedBusinesses.has(index)}
                    onChange={() => toggleSelect(index)}
                    className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                  />
                </td>

                {/* Business Name */}
                <td className="px-6 py-4">
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-lg flex items-center justify-center text-white font-bold">
                      {business.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="ml-3">
                      <div className="text-sm font-semibold text-gray-900">
                        {business.name}
                      </div>
                      {business.website && (
                        <a 
                          href={business.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-indigo-600 hover:text-indigo-800 flex items-center mt-1"
                        >
                          <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                            <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                          </svg>
                          Visit website
                        </a>
                      )}
                    </div>
                  </div>
                </td>

                {/* Contact */}
                <td className="px-6 py-4">
                  <div className="space-y-1">
                    {business.phone && (
                      <div className="flex items-center text-sm text-gray-900">
                        <svg className="w-4 h-4 text-gray-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z" />
                        </svg>
                        {business.phone}
                      </div>
                    )}
                    {business.email && (
                      <div className="flex items-center text-sm text-gray-900">
                        <svg className="w-4 h-4 text-gray-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                          <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
                        </svg>
                        {business.email}
                      </div>
                    )}
                    {!business.phone && !business.email && (
                      <span className="text-sm text-gray-400">No contact info</span>
                    )}
                  </div>
                </td>

                {/* Address */}
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-900 max-w-xs">
                    {business.address || (
                      <span className="text-gray-400">No address</span>
                    )}
                  </div>
                </td>

                {/* Rating */}
                <td className="px-6 py-4">
                  {business.rating ? (
                    <div>
                      <div className="flex items-center">
                        <span className="text-yellow-400 mr-1">★</span>
                        <span className="text-sm font-semibold text-gray-900">
                          {business.rating.toFixed(1)}
                        </span>
                      </div>
                      {business.reviews_count && (
                        <div className="text-xs text-gray-500 mt-1">
                          {business.reviews_count} reviews
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="text-sm text-gray-400">No rating</span>
                  )}
                </td>

                {/* Actions */}
                <td className="px-6 py-4">
                  <div className="flex space-x-2">
                    {business.phone && (
                      <button
                        onClick={() => handleCall(business.phone!)}
                        className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center"
                        title="Call"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z" />
                        </svg>
                      </button>
                    )}
                    {business.email && (
                      <button
                        onClick={() => handleEmail(business.email!)}
                        className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center"
                        title="Email"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                          <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
                        </svg>
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}