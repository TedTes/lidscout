/**
 * API service for communicating with backend.
 * Following Single Responsibility Principle - only handles API calls.
 */
import axios from 'axios';
import { SearchCriteria, SearchResponse } from '@/types/business';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class BusinessApiService {
  private api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  /**
   * Search for businesses based on criteria.
   */
  async searchBusinesses(criteria: SearchCriteria): Promise<SearchResponse> {
    try {
      const response = await this.api.post<SearchResponse>(
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
    const response = await this.api.get('/api/businesses/health');
    return response.data;
  }
}

// Export singleton instance
export const businessApi = new BusinessApiService();