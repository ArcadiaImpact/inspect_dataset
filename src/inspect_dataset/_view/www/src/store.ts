import { create } from "zustand";
import type { Finding, Summary, TriageStatus } from "./types";
import { fetchFindings, fetchSummary, postTriage } from "./api";

type Tab = "findings" | "samples";

interface AppState {
  // Data
  summary: Summary | null;
  findings: Finding[];
  loading: boolean;
  error: string | null;

  // UI state
  activeTab: Tab;
  selectedScanner: string | null;
  selectedSeverity: string | null;
  selectedTriageFilter: string | null;
  selectedFinding: Finding | null;

  // Actions
  setActiveTab: (tab: Tab) => void;
  setSelectedScanner: (scanner: string | null) => void;
  setSelectedSeverity: (severity: string | null) => void;
  setSelectedTriageFilter: (filter: string | null) => void;
  setSelectedFinding: (finding: Finding | null) => void;
  loadData: () => Promise<void>;
  triageFinding: (findingId: number, status: TriageStatus) => Promise<void>;
  navigateFinding: (direction: "next" | "prev") => void;
}

export const useStore = create<AppState>((set, get) => ({
  summary: null,
  findings: [],
  loading: false,
  error: null,

  activeTab: "findings",
  selectedScanner: null,
  selectedSeverity: null,
  selectedTriageFilter: null,
  selectedFinding: null,

  setActiveTab: (tab) => set({ activeTab: tab }),
  setSelectedScanner: (scanner) => set({ selectedScanner: scanner }),
  setSelectedSeverity: (severity) => set({ selectedSeverity: severity }),
  setSelectedTriageFilter: (filter) => set({ selectedTriageFilter: filter }),
  setSelectedFinding: (finding) => set({ selectedFinding: finding }),

  loadData: async () => {
    set({ loading: true, error: null });
    try {
      const [summary, findings] = await Promise.all([
        fetchSummary(),
        fetchFindings(),
      ]);
      set({ summary, findings, loading: false });
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

  navigateFinding: (direction) => {
    const { selectedFinding } = get();
    const filtered = getFilteredFindings(get());
    if (!selectedFinding || filtered.length === 0) return;

    const idx = filtered.findIndex((f) => f.id === selectedFinding.id);
    const next =
      direction === "next"
        ? Math.min(idx + 1, filtered.length - 1)
        : Math.max(idx - 1, 0);
    set({ selectedFinding: filtered[next] });
  },
}));

/** Derived: apply scanner/severity/triage filters to findings. */
export function getFilteredFindings(state: AppState): Finding[] {
  let result = state.findings;
  if (state.selectedScanner) {
    result = result.filter((f) => f.scanner === state.selectedScanner);
  }
  if (state.selectedSeverity) {
    result = result.filter((f) => f.severity === state.selectedSeverity);
  }
  if (state.selectedTriageFilter) {
    result = result.filter(
      (f) => f.triage_status === state.selectedTriageFilter,
    );
  }
  return result;
}

/** Derived: scanner name → count (from full findings list). */
export function getScannerCounts(
  findings: Finding[],
): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const f of findings) {
    counts[f.scanner] = (counts[f.scanner] || 0) + 1;
  }
  return counts;
}
