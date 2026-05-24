export type Signal = {
  id: string;
  post_id: string;
  pain: string;
  user_type: string | null;
  job_to_be_done: string | null;
  current_workaround: string | null;
  urgency: 'low' | 'medium' | 'high';
  severity: 'low' | 'medium' | 'high';
  willingness_to_pay: boolean | null;
  category: string | null;
  confidence: number;
  competitor_id: string | null;
  competitor_name: string | null;
  market_id: string | null;
  market_name: string | null;
  evidence_url: string | null;
  evidence_text: string | null;
  detected_at: string | null;
};

export type SignalCluster = {
  id: string;
  theme: string;
  summary: string;
  signal_ids: string[];
  frequency: number;
  average_score: number;
  top_examples: string[];
  company_ids: string[];
  company_names: string[];
  company_count: number;
  market_company_count: number | null;
};

export type Opportunity = {
  id: string;
  cluster_id: string;
  title: string;
  target_user: string;
  pain_summary: string;
  why_it_matters: string;
  suggested_wedge: string;
  evidence_count: number;
  confidence: number;
  evidence_signal_ids: string[];
  company_ids: string[];
  company_names: string[];
  company_count: number;
  market_company_count: number | null;
};

export type Competitor = {
  id: string;
  name: string;
  website: string | null;
  category: string | null;
  description: string | null;
  market_id: string | null;
  created_at: string | null;
};

export type Market = {
  id: string;
  name: string;
  description: string | null;
  target_user: string | null;
  idea_prompt: string | null;
  created_at: string | null;
};

export type MonitoredSource = {
  id: string;
  competitor_id: string | null;
  competitor_name: string | null;
  market_id: string | null;
  market_name: string | null;
  locator: string;
  source_type: string;
  source_family: string | null;
  enabled: boolean;
  limit: number | null;
  scan_frequency: string | null;
  last_scanned_at: string | null;
  last_error: string | null;
  options: Record<string, unknown>;
};

export type SourceFamilySummary = {
  source_family: string;
  source_count: number;
  active_count: number;
  error_count: number;
  company_count: number;
};

export type SourceCoverageSummary = {
  source_count: number;
  active_count: number;
  disabled_count: number;
  error_count: number;
  company_count: number;
  by_family: SourceFamilySummary[];
};

export type SourceSuggestion = {
  locator: string;
  source_type: string;
  label: string;
  rationale: string;
  source_family: string;
  competitor_id: string | null;
  competitor_name: string | null;
  market_id: string | null;
  market_name: string | null;
  limit: number | null;
  options: Record<string, unknown>;
  template_id: string | null;
  already_monitored: boolean;
  rank_score: number;
  validation_status: 'unknown' | 'valid' | 'invalid';
  validation_error: string | null;
};

export type CompetitorsResponse = {
  competitors: Competitor[];
};

export type MarketsResponse = {
  markets: Market[];
};

export type MonitoredSourcesResponse = {
  sources: MonitoredSource[];
  summary?: SourceCoverageSummary;
};

export type SourceSuggestionsResponse = {
  suggestions: SourceSuggestion[];
};

export type MonitoredSourceUpdateRequest = {
  source_type?: string | null;
  enabled?: boolean | null;
  limit?: number | null;
  scan_frequency?: string | null;
  options?: Record<string, unknown> | null;
};

export type MarketSignalReport = {
  title: string;
  generated_at: string;
  top_clusters: SignalCluster[];
  emerging_pains: string[];
  recommended_opportunities: Opportunity[];
};

export type SignalsResponse = {
  signals: Signal[];
};

export type ClustersResponse = {
  clusters: SignalCluster[];
};

export type OpportunitiesResponse = {
  opportunities: Opportunity[];
};

export type SourceLocator = {
  id: string;
  locator: string;
  enabled: boolean;
  limit_value: number | null;
  options: Record<string, unknown>;
  inserted_at: string;
  updated_at: string;
};
