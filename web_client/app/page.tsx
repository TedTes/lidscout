'use client';

import { useState } from 'react';
import InteractionForm from '@/components/InteractionForm';
import InteractionResults from '@/components/InteractionResults';
import { interactionApi } from '@/lib/api';
import { InteractionExtractionRequest, InteractionExtractionResponse } from '@/lib/types/interaction';

export default function Home() {
  const [results, setResults] = useState<InteractionExtractionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExtract = async (request: InteractionExtractionRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await interactionApi.extractInteractions(request);
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Extraction failed. Check the URL and try again.');
      setResults(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-4xl px-4 py-4">
          <span className="text-xs font-bold uppercase tracking-widest text-sky-700">LidScout</span>
        </div>
      </header>

      <div className="mx-auto max-w-4xl space-y-4 px-4 py-6">
        {/* Input card */}
        <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-4">
            <h2 className="text-sm font-semibold text-gray-800">Extract from a page</h2>
            <p className="mt-0.5 text-xs text-gray-500">
              Enter a public URL to extract structured data, comments, and negative signals.
            </p>
          </div>
          <InteractionForm onExtract={handleExtract} isLoading={isLoading} />
        </section>

        {/* Error banner */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
            <p className="text-sm font-semibold text-red-800">Extraction failed</p>
            <p className="mt-0.5 text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Loading state */}
        {isLoading ? (
          <div className="flex items-start gap-3 rounded-xl border border-sky-100 bg-sky-50 px-5 py-4">
            <span className="mt-0.5 h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-sky-200 border-t-sky-600" />
            <div>
              <p className="text-sm font-medium text-sky-900">Extracting page signals</p>
              <p className="mt-0.5 text-xs text-sky-700">
                Fetching the page, identifying comments, and grouping negative signals…
              </p>
            </div>
          </div>
        ) : (
          <InteractionResults results={results} />
        )}
      </div>
    </main>
  );
}
