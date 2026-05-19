export type SourceType = 'url' | 'text';

export interface PageSourceInput {
  source_type: SourceType;
  url?: string | null;
  text?: string | null;
  label?: string | null;
}

export interface InteractionExtractionRequest {
  sources: PageSourceInput[];
}

export interface PageStats {
  line_count: number;
  word_count: number;
  character_count: number;
}

export interface ExtractedPage {
  source_id: string;
  label: string;
  source_url?: string | null;
  title?: string | null;
  content: {
    text_excerpt: string;
    lines: string[];
  };
  stats: PageStats;
}

export interface PublicInteraction {
  interaction_id: string;
  source_id: string;
  body: string;
  title?: string | null;
  author?: string | null;
  rating?: number | null;
  published_at?: string | null;
  sentiment: 'negative' | 'neutral' | 'positive' | 'mixed' | 'unknown';
  topics: string[];
  evidence_terms: string[];
}

export interface NegativeSignal {
  theme: string;
  frequency: number;
  severity: 'low' | 'medium' | 'high';
  interaction_ids: string[];
  excerpts: string[];
}

export interface InteractionExtractionResponse {
  total_sources: number;
  pages: ExtractedPage[];
  interactions: PublicInteraction[];
  negative_comments: PublicInteraction[];
  negative_signals: NegativeSignal[];
}
