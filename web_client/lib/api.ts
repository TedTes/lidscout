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
  AgentRunsResponse,
  PipelineLiveFeedResponse,
  AgentColdStartPlan,
  AgentFeedback,
  AgentFeedbackAction,
  AgentFeedbackRequest,
  AgentFeedbackResponse,
  AgentMemorySummary,
  AgentPreferences,
  AgentPreferencesUpdateRequest,
  NicheCompany,
  CompaniesResponse,
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
  ThemesResponse,
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
  private _marketCache = new Map<string, { data: Market; exp: number }>();
  private _marketsCache: { data: MarketsResponse; exp: number } | null = null;
  private _marketsInFlight: Promise<MarketsResponse> | null = null;

  private invalidateMarketListCache() {
    this._marketsCache = null;
    this._marketsInFlight = null;
  }

  async getMarket(marketId: string, options?: { force?: boolean }): Promise<Market> {
    const hit = this._marketCache.get(marketId);
    if (!options?.force && hit && hit.exp > Date.now()) return hit.data;
    try {
      const response = await api.get<Market>(`/markets/${marketId}`);
      this._marketCache.set(marketId, { data: response.data, exp: Date.now() + 30_000 });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) throw new Error(error.response?.data?.detail || 'Failed to load watchlist');
      throw error;
    }
  }

  async getMarkets(options?: { force?: boolean }): Promise<MarketsResponse> {
    const now = Date.now();
    if (!options?.force && this._marketsCache && this._marketsCache.exp > now) {
      return this._marketsCache.data;
    }
    if (!options?.force && this._marketsInFlight) {
      return this._marketsInFlight;
    }

    const request = api.get<MarketsResponse>('/markets')
      .then(response => {
        this._marketsCache = {
          data: response.data,
          exp: Date.now() + 30_000,
        };
        return response.data;
      })
      .finally(() => {
        this._marketsInFlight = null;
      });
    this._marketsInFlight = request;

    try {
      return await request;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load watchlists');
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

  async deleteOpportunityFeedback(
    opportunityId: string,
    params: { market_id: string; action: AgentFeedbackAction }
  ): Promise<{ deleted: boolean }> {
    try {
      const response = await api.delete<{ deleted: boolean }>(
        `/opportunities/${opportunityId}/feedback`,
        { params }
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to remove feedback');
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
      this.invalidateMarketListCache();
      this._marketCache.set(response.data.id, { data: response.data, exp: Date.now() + 30_000 });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to create watchlist');
      }
      throw error;
    }
  }

  async applyTemplate(templateId: string): Promise<Market> {
    try {
      const response = await api.post<Market>(`/templates/${templateId}/apply`);
      this.invalidateMarketListCache();
      this._marketCache.set(response.data.id, { data: response.data, exp: Date.now() + 30_000 });
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
        throw new Error(error.response?.data?.detail || 'Failed to load watchlist templates');
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
        throw new Error(error.response?.data?.detail || 'Failed to load watchlist sources');
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
        throw new Error(error.response?.data?.detail || 'Failed to create watchlist source');
      }
      throw error;
    }
  }

  async getCompanies(): Promise<CompaniesResponse> {
    try {
      const response = await api.get<CompaniesResponse>('/companies');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load companies');
      }
      throw error;
    }
  }

  async createCompany(request: {
    id: string;
    name: string;
    website?: string | null;
    category?: string | null;
    description?: string | null;
    market_id?: string | null;
  }): Promise<NicheCompany> {
    try {
      const response = await api.post<NicheCompany>('/companies', request);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to create company');
      }
      throw error;
    }
  }

  async getMarketCompanies(marketId: string): Promise<CompaniesResponse> {
    try {
      const response = await api.get<CompaniesResponse>(`/markets/${marketId}/companies`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load watchlist products');
      }
      throw error;
    }
  }

  async createMarketCompany(
    marketId: string,
    request: {
      id: string;
      name: string;
      website?: string | null;
      category?: string | null;
      description?: string | null;
    }
  ): Promise<NicheCompany> {
    try {
      const response = await api.post<NicheCompany>(
        `/markets/${marketId}/companies`,
        request
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to add watchlist product');
      }
      throw error;
    }
  }

  async getCompanySources(companyId: string): Promise<MonitoredSourcesResponse> {
    try {
      const response = await api.get<MonitoredSourcesResponse>(
        `/companies/${companyId}/sources`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load monitored sources');
      }
      throw error;
    }
  }

  async createCompanySource(
    companyId: string,
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
        `/companies/${companyId}/sources`,
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

  async excludeMarketSource(marketId: string, sourceId: string): Promise<MonitoredSource> {
    try {
      const response = await api.post<MonitoredSource>(
        `/markets/${marketId}/sources/${sourceId}/exclude`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to exclude source');
      }
      throw error;
    }
  }

  async restoreMarketSource(marketId: string, sourceId: string): Promise<MonitoredSource> {
    try {
      const response = await api.post<MonitoredSource>(
        `/markets/${marketId}/sources/${sourceId}/restore`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to restore source');
      }
      throw error;
    }
  }

  async getSignals(params?: {
    company_id?: string;
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
      this.invalidateMarketListCache();
      this._marketCache.set(marketId, { data: response.data, exp: Date.now() + 30_000 });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to update watchlist');
      }
      throw error;
    }
  }

  async deleteMarket(marketId: string): Promise<{ id: string; deleted: boolean }> {
    try {
      const response = await api.delete<{ id: string; deleted: boolean }>(`/markets/${marketId}`);
      this.invalidateMarketListCache();
      this._marketCache.delete(marketId);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to delete watchlist');
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
    company_id?: string;
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

  async getThemes(params?: {
    company_id?: string;
    market_id?: string;
    status?: string;
  }): Promise<ThemesResponse> {
    try {
      const response = await api.get<ThemesResponse>('/themes', { params });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load themes');
      }
      throw error;
    }
  }

  async getOpportunities(params?: {
    company_id?: string;
    market_id?: string;
    recency_days?: number | null;
    feedback_filter?: 'all' | 'saved' | 'dismissed' | null;
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
    company_id?: string;
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

  async getMarketPipelineStatus(marketId: string): Promise<{ status: 'pending' | 'running' | 'done'; last_event_type: string | null; last_event_at: string | null }> {
    try {
      const response = await api.get(`/markets/${marketId}/pipeline/status`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load pipeline status');
      }
      throw error;
    }
  }

  async getMarketPipelineLiveFeed(marketId: string): Promise<PipelineLiveFeedResponse> {
    try {
      const response = await api.get<PipelineLiveFeedResponse>(
        `/markets/${marketId}/pipeline/live-feed`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || 'Failed to load pipeline live feed');
      }
      throw error;
    }
  }

  async getMarketAgentActivity(
    marketId: string,
    options?: { includeDiagnostics?: boolean }
  ): Promise<AgentActivityResponse> {
    try {
      const params = options?.includeDiagnostics ? { include_diagnostics: true } : undefined;
      const response = await api.get<AgentActivityResponse>(
        `/markets/${marketId}/agent/activity`,
        { params }
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

  async triggerMarketPipeline(marketId: string): Promise<{ status: string }> {
    try {
      const response = await api.post<{ status: string }>(`/markets/${marketId}/pipeline/trigger`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) throw new Error(error.response?.data?.detail || 'Failed to trigger scan');
      throw error;
    }
  }

  async getMarketAgentRuns(marketId: string): Promise<AgentRunsResponse> {
    try {
      const response = await api.get<AgentRunsResponse>(`/markets/${marketId}/agent/runs`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) throw new Error(error.response?.data?.detail || 'Failed to load agent runs');
      throw error;
    }
  }

}


// Export singleton instance
export const businessApi = new BusinessApiService();
export const interactionApi = new InteractionApiService();
export const signalApi = new SignalApiService();
