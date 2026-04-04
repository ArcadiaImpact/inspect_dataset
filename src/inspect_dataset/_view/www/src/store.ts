import { create } from "zustand";
import type { Finding, Sample, Summary, TriageStatus } from "./types";
import { fetchFindings, fetchSamples, fetchSummary, postTriage } from "./api";

interface AppState {
  // Data
  summary: Summary | null;
  findings: Finding[];
  samples: Sample[];
  loading: boolean;
  error: string | null;

  // UI state
  selectedFinding: Finding | null;

  // Actions
  setSelectedFinding: (finding: Finding | null) => void;
  loadData: () => Promise<void>;
  triageFinding: (findingId: number, status: TriageStatus) => Promise<void>;
}

export const useStore = create<AppState>((set) => ({
  summary: null,
  findings: [],
  samples: [],
  loading: false,
  error: null,

  selectedFinding: null,

  setSelectedFinding: (finding) => set({ selectedFinding: finding }),

  loadData: async () => {
    set({ loading: true, error: null });
    try {
      const [summary, findings, samples] = await Promise.all([
        fetchSummary(),
        fetchFindings(),
        fetchSamples(),
      ]);
      set({ summary, findings, samples, loading: false });
    } catch (e) {
      set({ error: String(e), loading: false });
    }
  },

  triageFinding: async (findingId, status) => {
    await postTriage(findingId, status);
    set((state) => ({
      findings: state.findings.map((f) =>
        f.id === findingId ? { ...f, triage_status: status } : f,
      ),
      selectedFinding:
        state.selectedFinding?.id === findingId
          ? { ...state.selectedFinding, triage_status: status }
          : state.selectedFinding,
    }));
  },
}));

/** Apply scanner/severity/triage filters to a findings list. */
export function getFilteredFindings(
  findings: Finding[],
  scanner: string | null,
  severity: string | null,
  triage: string | null,
): Finding[] {
  let result = findings;
  if (scanner) result = result.filter((f) => f.scanner === scanner);
  if (severity) result = result.filter((f) => f.severity === severity);
  if (triage) result = result.filter((f) => f.triage_status === triage);
  return result;
}

/** Scanner name → finding count (from full findings list). */
export function getScannerCounts(
  findings: Finding[],
): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const f of findings) {
    counts[f.scanner] = (counts[f.scanner] || 0) + 1;
  }
  return counts;
}
