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

export type MarketSignalReport = {
  title: string;
  generated_at: string;
  top_clusters: SignalCluster[];
  emerging_pains: string[];
  recommended_opportunities: string[];
};

export type SignalsResponse = {
  signals: Signal[];
};

export type ClustersResponse = {
  clusters: SignalCluster[];
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
  report: MarketSignalReport;
  email: {
    recipient: string;
    subject: string;
    sent: boolean;
    error: string | null;
  };
};
