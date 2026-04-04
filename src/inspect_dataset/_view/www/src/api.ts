import type { Finding, Sample, Summary, TriageStatus } from "./types";

const BASE = "/api";

export async function fetchSummary(): Promise<Summary> {
  const res = await fetch(`${BASE}/summary`);
  return res.json();
}

export async function fetchFindings(): Promise<Finding[]> {
  const res = await fetch(`${BASE}/findings`);
  return res.json();
}

export async function postTriage(
  findingId: number,
  status: TriageStatus,
): Promise<void> {
  await fetch(`${BASE}/triage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ finding_id: findingId, status }),
  });
}

export async function fetchSamples(): Promise<Sample[]> {
  const res = await fetch(`${BASE}/samples`);
  if (!res.ok) return [];
  return res.json();
}

export function exportUrl(): string {
  return `${BASE}/export`;
}
