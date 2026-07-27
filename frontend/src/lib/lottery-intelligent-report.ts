/** Types for Intelligent Analysis Report (UI-safe, no engine codes). */

export type IntelligentReportConfirmer = {
  number?: number | null;
  lottery?: string | null;
  position?: string | null;
};

export type IntelligentReportComparison = {
  number: number;
  table1_support: boolean;
  table2_support: boolean;
  same_day_cross: boolean;
  historical_equivalent_cases?: number | null;
  historical_label?: string;
  evidence_level_label?: string;
};

export type IntelligentReportRoute = {
  kind: string;
  label: string;
  from_number?: number;
  to_number?: number;
  via?: string;
  lottery_from?: string | null;
  lottery_to?: string | null;
};

export type IntelligentReportTimelineStep = {
  step: number;
  title: string;
  detail: string;
};

export type IntelligentReportCase = {
  date?: string;
  primary_number?: number;
  confirmer?: number | null;
  observed?: number | null;
  lotteries?: string | null;
  result_number?: number | null;
  result_label?: string | null;
  window?: string | null;
  result_lottery?: string | null;
};

export type IntelligentAnalysisReport = {
  title?: string;
  observed_numbers?: number[];
  analysis_date?: string | null;
  analysis_date_label?: string | null;
  origin_lottery?: string | null;
  origin_position?: string | null;
  confirmer?: IntelligentReportConfirmer | null;
  primary_candidate?: number | null;
  alternatives?: number[];
  evidence_level?: string;
  evidence_level_label?: string;
  evidence_level_help?: string;
  evidence_level_reason?: string | null;
  brief_conclusion?: string | null;
  why_evidence?: string[];
  table1_evidence?: { present?: boolean; sources?: number[]; target?: number | null };
  table2_evidence?: { present?: boolean; confirmers?: number[]; target?: number | null };
  same_day_evidence?: {
    present?: boolean;
    crosses?: {
      observed?: number;
      companion?: number;
      confirmer?: number;
      lottery_origin?: string | null;
      lottery_confirmer?: string | null;
    }[];
  };
  independent_evidence_count?: number;
  participating_lotteries?: string[];
  historical_metrics?: {
    exact_cases?: number;
    exact_hits?: number;
    t1_family_hits?: number;
    t2_neighbor_hits?: number;
    d1_hits?: number;
    d3_hits?: number;
    d7_hits?: number;
    period_label?: string;
    behavior_label?: string;
    behavior_note?: string;
  } | null;
  historical_sample_quality?: {
    key?: string;
    label?: string;
    cases?: number;
    message?: string;
  } | null;
  historical_unavailable?: boolean;
  candidate_comparison?: IntelligentReportComparison[];
  comparison_explanation?: string | null;
  reasoning_timeline?: IntelligentReportTimelineStep[];
  mathematical_routes?: IntelligentReportRoute[];
  routes_converge_text?: string | null;
  recent_equivalent_cases?: IntelligentReportCase[];
  recent_cases_total_hint?: number;
  deterministic_explanation?: string;
  special_notes?: string[];
  disclaimer?: string;
};
