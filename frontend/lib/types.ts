export type DataStatus = "collecting" | "insufficient" | "scored";

export interface JournalistSummary {
  id: string;
  full_name: string;
  slug: string;
  primary_outlet: string | null;
  beat: string | null;
  data_status: DataStatus;
  composite_score: number | null;
  pillar_1_score: number | null;
  pillar_2_score: number | null;
  pillar_3_score: number | null;
  pillar_4_score: number | null;
  scored_at: string | null;
}

export interface PillarScores {
  pillar_1_score: number | null;
  pillar_2_score: number | null;
  pillar_3_score: number | null;
  pillar_4_score: number | null;
  composite_score: number | null;
  dimensions_scored: Record<string, boolean> | null;
  methodology_version: string;
  scored_at: string;
  score_narrative: Record<string, string> | null;
}

export interface FECRecord {
  id: string;
  contributor_name: string;
  recipient_name: string;
  recipient_type: string;
  amount: number;
  contribution_date: string;
  fec_record_id: string;
}

export interface Correction {
  id: string;
  correction_text: string;
  correction_type: string | null;
  original_published_at: string | null;
  corrected_at: string | null;
  days_to_correction: number | null;
  correction_url: string | null;
}

export interface Appeal {
  id: string;
  dimension: string | null;
  submission_text: string;
  submitted_at: string;
  outcome: string | null;
  outcome_notes: string | null;
  published: boolean;
}

export interface Citation {
  id: string;
  cited_text: string;
  dimension: string;
  flag_type: string | null;
  flag_value: number | null;
  article_id: string | null;
  article_url: string | null;
  article_headline: string | null;
}

export interface OutletSummary {
  name: string;
  slug: string;
  journalist_count: number;
  avg_composite: number | null;
  avg_pillar_1: number | null;
  avg_pillar_2: number | null;
  avg_pillar_3: number | null;
  avg_pillar_4: number | null;
}

export interface OutletProfile extends OutletSummary {
  journalists: JournalistSummary[];
}

export interface JournalistProfile extends JournalistSummary {
  bio: string | null;
  pillar_scores: PillarScores | null;
  fec_records: FECRecord[];
  corrections: Correction[];
  appeals: Appeal[];
  corpus_size: number | null;
  corpus_start: string | null;
  corpus_end: string | null;
  methodology_version: string | null;
}
