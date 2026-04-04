export interface ScannerStats {
  total: number;
  high: number;
  medium: number;
  low: number;
}

export interface Summary {
  dataset_name: string;
  split: string | null;
  total_samples: number;
  total_findings: number;
  by_scanner: Record<string, ScannerStats>;
  by_severity: Record<string, number>;
}

export type TriageStatus = "pending" | "confirmed" | "dismissed";

export interface Finding {
  id: number;
  scanner: string;
  severity: "high" | "medium" | "low";
  category: string;
  explanation: string;
  sample_index: number;
  sample_id: string | number | null;
  metadata: Record<string, unknown>;
  triage_status: TriageStatus;
}
