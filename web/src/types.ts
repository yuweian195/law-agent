export type RiskLevel = "high" | "medium" | "low";

export interface ReviewListItem {
  id: string;
  contract_title: string;
  contract_type: string;
  overall_risk: RiskLevel;
  risk_score: number;
  findings_count: number;
  created_at: string;
}

export interface LegalBasis {
  article_id: string;
  law: string;
  article: string;
  title: string;
  text: string;
}

export interface RiskFinding {
  rule_id: string;
  clause_index: number;
  clause_title: string;
  risk_level: RiskLevel;
  issue: string;
  suggestion: string;
  matched_text: string;
  legal_basis: LegalBasis[];
}

export interface TraceStep {
  node: string;
  label: string;
  status: string;
  duration_ms: number;
  summary: string;
}

export interface ReviewDetail extends ReviewListItem {
  findings: RiskFinding[];
  clauses: { index: number; title: string; text: string }[];
  summary: string;
  trace: TraceStep[];
  llm_mode: string;
}
