export type SourceFamilyBreakdownItem = {
  source_family: string;
  count: number;
};

export type EvidenceItem = {
  id: string;
  signal_id: string | null;
  post_id: string | null;
  quote: string | null;
  pain: string | null;
  url: string | null;
  source_label: string | null;
  source_family: string | null;
  source_type: string | null;
  company_id: string | null;
  company_name: string | null;
  category: string | null;
  urgency: 'low' | 'medium' | 'high' | null;
  severity: 'low' | 'medium' | 'high' | null;
  confidence: number | null;
  detected_at: string | null;
};

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
  company_id: string | null;
  company_name: string | null;
  market_id: string | null;
  market_name: string | null;
  evidence_url: string | null;
  evidence_text: string | null;
  detected_at: string | null;
  source_label: string | null;
  source_family: string | null;
  source_type: string | null;
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
  qualification_status?: 'qualified' | 'not_promoted';
  qualification_rejection_reason?: string | null;
  qualification?: {
    finding_count: number;
    source_count: number;
    company_count: number;
    general_finding_count: number;
  };
  source_family_breakdown?: SourceFamilyBreakdownItem[];
};

export type AccumulatedTheme = SignalCluster & {
  status: 'emerging' | 'qualified' | 'rejected' | 'archived';
  finding_ids: string[];
  evidence_source_count: number;
  evidence_items?: EvidenceItem[];
  latest_finding_at: string | null;
  last_qualified_at: string | null;
};

export type Opportunity = {
  id: string;
  cluster_id: string | null;
  source_theme_id?: string | null;
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
  evidence_source_count: number;
  evidence_strength: 'early' | 'moderate' | 'strong' | 'emerging' | 'validated';
  unmet_need_type?: 'time' | 'money' | 'effort' | 'capability' | 'fit' | null;
  verification_note?: string | null;
  evidence_items?: EvidenceItem[];
  source_family_breakdown?: SourceFamilyBreakdownItem[];
};

export type NicheCompany = {
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
  display_label: string;
  template_niche_id?: string | null;
  description: string | null;
  target_user: string | null;
  idea_prompt: string | null;
  created_at: string | null;
  source_summary?: SourceCoverageSummary | null;
  source_coverage?: SourceCoverageSummary | null;
};

export type NicheTemplate = {
  id: string;
  name: string;
  display_label: string;
  category: string;
  description: string;
  company_count: number;
  company_names: string[];
  source_families: string[];
};

export type NicheTemplatesResponse = {
  templates: NicheTemplate[];
};

export type AgentResearchBrief = {
  market_id: string;
  niche_name: string;
  target_user: string;
  objective: string;
  company_count: number;
  source_family_priorities: string[];
};

export type AgentColdStartPlan = {
  market_id: string;
  status: 'setup_needed' | 'ready_for_scan';
  brief: AgentResearchBrief;
  monitored_source_count: number;
  active_source_count: number;
  suggested_source_count: number;
  next_actions: string[];
  source_explanations: string[];
  expected_result_window: string;
  no_result_guidance: string[];
};

export type AgentPreferences = {
  market_id: string;
  preferred_source_families: string[];
  ignored_themes: string[];
  ignored_categories: string[];
  muted_source_ids: string[];
  extra_instructions: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AgentPreferencesUpdateRequest = {
  preferred_source_families?: string[] | null;
  ignored_themes?: string[] | null;
  ignored_categories?: string[] | null;
  muted_source_ids?: string[] | null;
  extra_instructions?: string | null;
};

export type AgentFeedbackAction = 'save' | 'dismiss' | 'more_like_this' | 'less_like_this';

export type AgentFeedback = {
  id: string;
  market_id: string;
  opportunity_id: string;
  action: AgentFeedbackAction;
  reason: string | null;
  comment: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AgentFeedbackRequest = {
  market_id: string;
  action: AgentFeedbackAction;
  reason?: string | null;
  comment?: string | null;
};

export type AgentFeedbackResponse = {
  feedback: AgentFeedback[];
};

export type MonitoredSource = {
  id: string;
  company_id: string | null;
  company_name: string | null;
  market_id: string | null;
  market_name: string | null;
  locator: string;
  source_type: string;
  source_family: string | null;
  enabled: boolean;
  muted?: boolean;
  excluded?: boolean;
  limit: number | null;
  scan_frequency: string | null;
  last_scanned_at: string | null;
  last_error: string | null;
  health: SourceHealth | null;
  contribution?: SourceContribution;
  findings_count?: number;
  themes_count?: number;
  opportunities_count?: number;
  lifecycle?: string;
  lifecycle_reason?: string;
  quality_status?: 'productive' | 'noisy' | 'blocked' | 'untested' | 'stale';
  quality_reason?: string;
  scan_eligible?: boolean;
  scan_ineligible_reason?: string | null;
  management?: {
    can_enable: boolean;
    can_disable: boolean;
    can_exclude?: boolean;
    can_restore?: boolean;
    can_delete: boolean;
    recommended_action:
      | 'enable_or_remove'
      | 'fix_or_replace'
      | 'keep_monitoring'
      | 'monitor_next_scan'
      | 'restore';
  };
  replacement_suggestions?: SourceReplacementSuggestion[];
  is_gate_free?: boolean;
  buyer_voice_verified?: boolean;
  tier?: number | null;
  signal_quality_score?: number | null;
  access_mode?: string;
  requires_proxy?: boolean;
  requires_auth?: boolean;
  recommended_cadence?: string | null;
  options: Record<string, unknown>;
};

export type SourceContribution = {
  findings_count: number;
  themes_count: number;
  opportunities_count: number;
};

export type SourceHealth = {
  total_runs: number;
  success_count: number;
  failure_count: number;
  consecutive_failures: number;
  posts_fetched_count: number;
  relevant_posts_count: number;
  extracted_signals_count: number;
  opportunity_count: number;
  last_status: 'unknown' | 'healthy' | 'failing';
  last_error: string | null;
  last_fetched_count: number;
  last_relevant_count: number;
  last_extracted_count: number;
  last_opportunity_count: number;
  fetch_success_rate: number;
  relevance_yield_rate: number;
  signal_yield_rate: number;
  last_scanned_at: string | null;
  updated_at: string | null;
};

export type SourceFamilySummary = {
  source_family: string;
  source_count: number;
  active_count: number;
  excluded_count?: number;
  paused_count?: number;
  error_count: number;
  failing_count?: number;
  company_count: number;
};

export type SourceCoverageSummary = {
  source_count: number;
  active_count: number;
  excluded_count?: number;
  paused_count?: number;
  disabled_count: number;
  error_count: number;
  failing_count?: number;
  last_scanned_at?: string | null;
  coverage_status?: 'healthy' | 'degraded' | 'no_active_sources';
  company_count: number;
  by_family: SourceFamilySummary[];
};

export type SourceSuggestion = {
  locator: string;
  source_type: string;
  label: string;
  rationale: string;
  source_family: string;
  company_id: string | null;
  company_name: string | null;
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

export type SourceReplacementSuggestion = {
  candidate: SourceSuggestion;
  trigger: 'blocked_source' | 'low_yield' | 'stale_source' | 'missing_family';
  reason: string;
  replaces_source_id: string | null;
};

export type CompaniesResponse = {
  companies: NicheCompany[];
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

export type ThemesResponse = {
  themes: AccumulatedTheme[];
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

export type AgentActivity = {
  id: string;
  market_id: string;
  event_type: string;
  title: string;
  detail: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string | null;
};

export type AgentActivityResponse = {
  activity: AgentActivity[];
};

export type PipelineLiveFeedResponse = {
  current_item: AgentActivity | null;
  recent_decisions: AgentActivity[];
};

export type AgentMemorySummary = {
  market_id: string;
  headline: string;
  learned_preferences: string[];
  source_notes: string[];
  feedback_notes: string[];
};

export type AgentActionType =
  | 'scan_sources'
  | 'pause_source'
  | 'source_needs_attention'
  | 'suggest_source'
  | 'answer_follow_up'
  | 'send_alert'
  | 'wait';

export type AgentActionStatus =
  | 'proposed'
  | 'approved'
  | 'dismissed'
  | 'completed'
  | 'failed';

export type AgentAction = {
  id: string;
  market_id: string;
  action_type: AgentActionType;
  status: AgentActionStatus;
  reason: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
  completed_at: string | null;
};

export type AgentPlan = {
  actions: AgentAction[];
};

export type AgentActionsResponse = {
  actions: AgentAction[];
};

export type AgentRunsResponse = {
  runs: AgentActivity[];
};

export type AgentFollowUp = {
  id: string;
  market_id: string;
  question: string;
  opportunity_id: string | null;
  cluster_id: string | null;
  status: 'queued' | 'answered' | 'dismissed';
  response: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

export type AgentFollowUpsResponse = {
  follow_ups: AgentFollowUp[];
};

export type AgentFollowUpRequest = {
  question: string;
  opportunity_id?: string | null;
  cluster_id?: string | null;
};
