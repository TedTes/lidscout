/**
 * API service for communicating with the LidScout API.
 * Following Single Responsibility Principle - only handles API calls.
 */
import axios from 'axios';
import { SearchCriteria, SearchResponse } from '@/lib/types/business';
import { InteractionExtractionRequest, InteractionExtractionResponse } from '@/lib/types/interaction';
import {
  ClustersResponse,
  MarketSignalReport,
  PipelineRunRequest,
  PipelineRunResult,
  SignalsResponse,
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

  async runPipeline(request: PipelineRunRequest): Promise<PipelineRunResult> {
    try {
      const response = await api.post<PipelineRunResult>('/pipeline/run', request);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to run pipeline');
      }
      throw error;
    }
  }
}

// Export singleton instance
export const businessApi = new BusinessApiService();
export const interactionApi = new InteractionApiService();
export const signalApi = new SignalApiService();
