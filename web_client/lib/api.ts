/**
 * API service for communicating with the LidScout API.
 * Following Single Responsibility Principle - only handles API calls.
 */
import axios from 'axios';
import { clearToken, getToken } from '@/lib/auth';
import { SearchCriteria, SearchResponse } from '@/lib/types/business';
import { InteractionExtractionRequest, InteractionExtractionResponse } from '@/lib/types/interaction';
import {
  AgentActivityResponse,
  AgentColdStartPlan,
  AgentFeedback,
  AgentFeedbackRequest,
  AgentFeedbackResponse,
  AgentMemorySummary,
  AgentPreferences,
  AgentPreferencesUpdateRequest,
  Competitor,
  CompetitorsResponse,
  ClustersResponse,
  Market,
  MarketsResponse,
  MarketSignalReport,
  MonitoredSource,
  MonitoredSourceUpdateRequest,
  MonitoredSourcesResponse,
  NicheTemplatesResponse,
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

api.interceptors.request.use(config => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  res => res,
  err => {
    if (axios.isAxiosError(err) && err.response?.status === 401) {
      clearToken();
      if (typeof window !== 'undefined') window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth API ──────────────────────────────────────────────────────────────────

type TokenResponse = { access_token: string; token_type: string };
type UserResponse = { id: string; email: string };

class AuthApiService {
  async register(email: string, password: string): Promise<TokenResponse> {
    try {
      const res = await api.post<TokenResponse>('/auth/register', { email, password });
      return res.data;
    } catch (error) {
      if (axios.isAxiosError(error)) throw new Error(error.response?.data?.detail || 'Registration failed');
      throw error;
    }
  }

  async login(email: string, password: string): Promise<TokenResponse> {
    try {
      const res = await api.post<TokenResponse>('/auth/login', { email, password });
      return res.data;
    } catch (error) {
      if (axios.isAxiosError(error)) throw new Error(error.response?.data?.detail || 'Invalid email or password');
      throw error;
    }
  }

  async me(): Promise<UserResponse> {
    const res = await api.get<UserResponse>('/auth/me');
    return res.data;
  }

  async googleLogin(credential: string): Promise<TokenResponse> {
    try {
      const res = await api.post<TokenResponse>('/auth/google', { credential });
      return res.data;
    } catch (error) {
      if (axios.isAxiosError(error)) throw new Error(error.response?.data?.detail || 'Google sign-in failed');
      throw error;
    }
  }
}

export const authApi = new AuthApiService();

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
  async getMarkets(): Promise<MarketsResponse> {
    try {
      const response = await api.get<MarketsResponse>('/markets');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load niches');
      }
      throw error;
    }
  }

  async getMarketAgentColdStart(marketId: string): Promise<AgentColdStartPlan> {
    try {
      const response = await api.get<AgentColdStartPlan>(
        `/markets/${marketId}/agent/cold-start`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load agent setup');
      }
      throw error;
    }
  }

  async getMarketAgentPreferences(marketId: string): Promise<AgentPreferences> {
    try {
      const response = await api.get<AgentPreferences>(
        `/markets/${marketId}/agent/preferences`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load agent preferences');
      }
      throw error;
    }
  }

  async updateMarketAgentPreferences(
    marketId: string,
    request: AgentPreferencesUpdateRequest
  ): Promise<AgentPreferences> {
    try {
      const response = await api.patch<AgentPreferences>(
        `/markets/${marketId}/agent/preferences`,
        request
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to update agent preferences');
      }
      throw error;
    }
  }

  async getMarketAgentFeedback(marketId: string): Promise<AgentFeedbackResponse> {
    try {
      const response = await api.get<AgentFeedbackResponse>(
        `/markets/${marketId}/agent/feedback`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load agent feedback');
      }
      throw error;
    }
  }

  async createOpportunityFeedback(
    opportunityId: string,
    request: AgentFeedbackRequest
  ): Promise<AgentFeedback> {
    try {
      const response = await api.post<AgentFeedback>(
        `/opportunities/${opportunityId}/feedback`,
        request
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to record feedback');
      }
      throw error;
    }
  }

  async createMarket(request: {
    id: string;
    name: string;
    description?: string | null;
    target_user?: string | null;
    idea_prompt?: string | null;
  }): Promise<Market> {
    try {
      const response = await api.post<Market>('/markets', request);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to create niche');
      }
      throw error;
    }
  }

  async applyTemplate(templateId: string): Promise<Market> {
    try {
      const response = await api.post<Market>(`/templates/${templateId}/apply`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to apply template');
      }
      throw error;
    }
  }

  async getTemplates(): Promise<NicheTemplatesResponse> {
    try {
      const response = await api.get<NicheTemplatesResponse>('/templates');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load niche templates');
      }
      throw error;
    }
  }

  async getMarketSources(marketId: string): Promise<MonitoredSourcesResponse> {
    try {
      const response = await api.get<MonitoredSourcesResponse>(
        `/markets/${marketId}/sources`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load niche sources');
      }
      throw error;
    }
  }

  async createMarketSource(
    marketId: string,
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
        `/markets/${marketId}/sources`,
        request
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to create niche source');
      }
      throw error;
    }
  }

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
    market_id?: string | null;
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

  async getMarketCompetitors(marketId: string): Promise<CompetitorsResponse> {
    try {
      const response = await api.get<CompetitorsResponse>(`/markets/${marketId}/competitors`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load niche companies');
      }
      throw error;
    }
  }

  async createMarketCompetitor(
    marketId: string,
    request: {
      id: string;
      name: string;
      website?: string | null;
      category?: string | null;
      description?: string | null;
    }
  ): Promise<Competitor> {
    try {
      const response = await api.post<Competitor>(
        `/markets/${marketId}/competitors`,
        request
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to add niche company');
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

  async getMarketSourceSuggestions(
    marketId: string
  ): Promise<SourceSuggestionsResponse> {
    try {
      const response = await api.get<SourceSuggestionsResponse>(
        `/markets/${marketId}/source-suggestions`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load niche source suggestions');
      }
      throw error;
    }
  }

  async getSources(params?: {
    competitor_id?: string;
    market_id?: string;
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
      market_id?: string | null;
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

  async getSignals(params?: {
    competitor_id?: string;
    market_id?: string;
  }): Promise<SignalsResponse> {
    try {
      const response = await api.get<SignalsResponse>('/signals', { params });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load signals');
      }
      throw error;
    }
  }

  async updateMarket(
    marketId: string,
    request: { name?: string; description?: string | null; target_user?: string | null }
  ): Promise<Market> {
    try {
      const response = await api.patch<Market>(`/markets/${marketId}`, request);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to update niche');
      }
      throw error;
    }
  }

  async deleteMarket(marketId: string): Promise<{ id: string; deleted: boolean }> {
    try {
      const response = await api.delete<{ id: string; deleted: boolean }>(`/markets/${marketId}`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to delete niche');
      }
      throw error;
    }
  }

  async deleteSource(sourceId: string): Promise<{ id: string; deleted: boolean }> {
    try {
      const response = await api.delete<{ id: string; deleted: boolean }>(
        `/sources/${sourceId}`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to delete source');
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

  async getClusters(params?: {
    competitor_id?: string;
    market_id?: string;
  }): Promise<ClustersResponse> {
    try {
      const response = await api.get<ClustersResponse>('/clusters', { params });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load clusters');
      }
      throw error;
    }
  }

  async getOpportunities(params?: {
    competitor_id?: string;
    market_id?: string;
  }): Promise<OpportunitiesResponse> {
    try {
      const response = await api.get<OpportunitiesResponse>('/opportunities', { params });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load opportunities');
      }
      throw error;
    }
  }

  async getLatestReport(params?: {
    competitor_id?: string;
    market_id?: string;
  }): Promise<MarketSignalReport> {
    try {
      const response = await api.get<MarketSignalReport>('/reports/latest', { params });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load latest report');
      }
      throw error;
    }
  }

  async getMarketAgentActivity(marketId: string): Promise<AgentActivityResponse> {
    try {
      const response = await api.get<AgentActivityResponse>(
        `/markets/${marketId}/agent/activity`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load agent activity');
      }
      throw error;
    }
  }

  async getMarketAgentMemory(marketId: string): Promise<AgentMemorySummary> {
    try {
      const response = await api.get<AgentMemorySummary>(
        `/markets/${marketId}/agent/memory`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load agent memory');
      }
      throw error;
    }
  }

  async getPipelineSchedule(): Promise<{ cron: string; next_run_at: string | null }> {
    try {
      const response = await api.get<{ cron: string; next_run_at: string | null }>('/pipeline/schedule');
      return response.data;
    } catch {
      return { cron: '0 8 * * *', next_run_at: null };
    }
  }
}


// Export singleton instance
export const businessApi = new BusinessApiService();
export const interactionApi = new InteractionApiService();
export const signalApi = new SignalApiService();
