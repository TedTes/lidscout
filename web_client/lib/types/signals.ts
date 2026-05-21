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
};

export type Competitor = {
  id: string;
  name: string;
  website: string | null;
  category: string | null;
  description: string | null;
  created_at: string | null;
};

export type MonitoredSource = {
  id: string;
  competitor_id: string;
  locator: string;
  source_type: string;
  enabled: boolean;
  limit: number | null;
  scan_frequency: string | null;
  last_scanned_at: string | null;
  last_error: string | null;
  options: Record<string, unknown>;
};

export type CompetitorsResponse = {
  competitors: Competitor[];
};

export type MonitoredSourcesResponse = {
  sources: MonitoredSource[];
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

export type PipelineSourceRequest = {
  locator: string;
  limit?: number;
  options?: Record<string, unknown>;
};

export type PipelineRunRequest = {
  recipient: string;
  sources?: Array<{
    locator: string;
    limit?: number;
    options?: Record<string, unknown>;
  }>;
  default_limit?: number;
  similarity_threshold?: number;
};

export type PipelineRunResult = {
  fetched_count: number;
  fetch_failed_count: number;
  ingestion: {
    received_count: number;
    inserted_count: number;
    duplicate_count: number;
    failed_count: number;
  };
  extracted_count: number;
  no_signal_count: number;
  extraction_failed_count: number;
  signal_inserted_count: number;
  scoring: {
    scored_count: number;
    failed_count: number;
    average_score: number;
  };
  embedding_failed_count: number;
  clustered_count: number;
  cluster_inserted_count: number;
  opportunity_synthesis: {
    synthesized_count: number;
    inserted_count: number;
    failed_count: number;
  };
  report: MarketSignalReport;
  email: {
    recipient: string;
    subject: string;
    sent: boolean;
    error: string | null;
  };
};
