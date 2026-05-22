/**
 * API service for communicating with the LidScout API.
 * Following Single Responsibility Principle - only handles API calls.
 */
import axios from 'axios';
import { SearchCriteria, SearchResponse } from '@/lib/types/business';
import { InteractionExtractionRequest, InteractionExtractionResponse } from '@/lib/types/interaction';
import {
  Competitor,
  CompetitorsResponse,
  ClustersResponse,
  MarketSignalReport,
  MonitoredSource,
  MonitoredSourceUpdateRequest,
  MonitoredSourcesResponse,
  OpportunitiesResponse,
  SignalsResponse,
  SourceSuggestionsResponse,
} from '@/lib/types/signals';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

class BusinessApiService {
  /**
   * Search for businesses based on criteria.
   */
  async searchBusinesses(criteria: SearchCriteria): Promise<SearchResponse> {
    try {
      const response = await api.post<SearchResponse>(
        '/api/businesses/search',
        criteria
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to search businesses');
      }
      throw error;
    }
  }

  /**
   * Health check for API.
   */
  async healthCheck(): Promise<{ status: string }> {
    const response = await api.get('/api/businesses/health');
    return response.data;
  }
}

class InteractionApiService {
  /**
   * Extract page JSON, comments, negative comments, and signals.
   */
  async extractInteractions(request: InteractionExtractionRequest): Promise<InteractionExtractionResponse> {
    try {
      const response = await api.post<InteractionExtractionResponse>(
        '/api/interactions/extract',
        request
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to extract interactions');
      }
      throw error;
    }
  }

  /**
   * Health check for interaction extraction API.
   */
  async healthCheck(): Promise<{ status: string }> {
    const response = await api.get('/api/interactions/health');
    return response.data;
  }
}

class SignalApiService {
  async getCompetitors(): Promise<CompetitorsResponse> {
    try {
      const response = await api.get<CompetitorsResponse>('/competitors');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load competitors');
      }
      throw error;
    }
  }

  async createCompetitor(request: {
    id: string;
    name: string;
    website?: string | null;
    category?: string | null;
    description?: string | null;
  }): Promise<Competitor> {
    try {
      const response = await api.post<Competitor>('/competitors', request);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to create competitor');
      }
      throw error;
    }
  }

  async getCompetitorSources(competitorId: string): Promise<MonitoredSourcesResponse> {
    try {
      const response = await api.get<MonitoredSourcesResponse>(
        `/competitors/${competitorId}/sources`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load monitored sources');
      }
      throw error;
    }
  }

  async getCompetitorSourceSuggestions(
    competitorId: string
  ): Promise<SourceSuggestionsResponse> {
    try {
      const response = await api.get<SourceSuggestionsResponse>(
        `/competitors/${competitorId}/source-suggestions`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load source suggestions');
      }
      throw error;
    }
  }

  async getSources(params?: {
    competitor_id?: string;
    enabled?: boolean;
  }): Promise<MonitoredSourcesResponse> {
    try {
      const response = await api.get<MonitoredSourcesResponse>('/sources', { params });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load monitored sources');
      }
      throw error;
    }
  }

  async createCompetitorSource(
    competitorId: string,
    request: {
      locator: string;
      source_type?: string;
      enabled?: boolean;
      limit?: number | null;
      scan_frequency?: string | null;
      options?: Record<string, unknown>;
    }
  ): Promise<MonitoredSource> {
    try {
      const response = await api.post<MonitoredSource>(
        `/competitors/${competitorId}/sources`,
        request
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to create monitored source');
      }
      throw error;
    }
  }

  async updateSource(
    sourceId: string,
    request: MonitoredSourceUpdateRequest
  ): Promise<MonitoredSource> {
    try {
      const response = await api.patch<MonitoredSource>(`/sources/${sourceId}`, request);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to update monitored source');
      }
      throw error;
    }
  }

  async getSignals(): Promise<SignalsResponse> {
    try {
      const response = await api.get<SignalsResponse>('/signals');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load signals');
      }
      throw error;
    }
  }

  async deleteSignal(signalId: string): Promise<{ id: string; deleted: boolean }> {
    try {
      const response = await api.delete<{ id: string; deleted: boolean }>(
        `/signals/${signalId}`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to delete signal');
      }
      throw error;
    }
  }

  async getClusters(): Promise<ClustersResponse> {
    try {
      const response = await api.get<ClustersResponse>('/clusters');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load clusters');
      }
      throw error;
    }
  }

  async getOpportunities(): Promise<OpportunitiesResponse> {
    try {
      const response = await api.get<OpportunitiesResponse>('/opportunities');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load opportunities');
      }
      throw error;
    }
  }

  async getLatestReport(): Promise<MarketSignalReport> {
    try {
      const response = await api.get<MarketSignalReport>('/reports/latest');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load latest report');
      }
      throw error;
    }
  }
}

// Export singleton instance
export const businessApi = new BusinessApiService();
export const interactionApi = new InteractionApiService();
export const signalApi = new SignalApiService();
