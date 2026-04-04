import { useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { useStore } from "../store";
import type { Finding } from "../types";
import type { ColDef, ICellRendererParams } from "ag-grid-community";
import { AllCommunityModule, ModuleRegistry, themeQuartz } from "ag-grid-community";

ModuleRegistry.registerModules([AllCommunityModule]);

interface SampleRow {
  index: number;
  findings: Finding[];
}

const SEVERITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

function FindingsBadges({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) return <span className="text-body-secondary">—</span>;

  const sorted = [...findings].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 3) - (SEVERITY_ORDER[b.severity] ?? 3),
  );

  const badgeCls: Record<string, string> = {
    high: "bg-danger",
    medium: "bg-warning text-dark",
    low: "bg-secondary",
  };

  return (
    <span>
      {sorted.map((f) => (
        <span key={f.id} className={`badge ${badgeCls[f.severity] ?? "bg-secondary"} me-1`}>
          {f.scanner}
        </span>
      ))}
    </span>
  );
}

export function SamplesTab() {
  const findings = useStore((s) => s.findings);
  const summary = useStore((s) => s.summary);
  const setSelectedFinding = useStore((s) => s.setSelectedFinding);
  const setActiveTab = useStore((s) => s.setActiveTab);

  const rows: SampleRow[] = useMemo(() => {
    const totalSamples = summary?.total_samples ?? 0;
    const byIndex = new Map<number, Finding[]>();
    for (const f of findings) {
      const list = byIndex.get(f.sample_index) ?? [];
      list.push(f);
      byIndex.set(f.sample_index, list);
    }
    const result: SampleRow[] = [];
    for (let i = 0; i < totalSamples; i++) {
      result.push({ index: i, findings: byIndex.get(i) ?? [] });
    }
    return result;
  }, [findings, summary]);

  const columnDefs: ColDef<SampleRow>[] = useMemo(
    () => [
      {
        headerName: "Index",
        field: "index",
        width: 90,
        sort: "asc" as const,
      },
      {
        headerName: "Findings",
        field: "findings",
        flex: 1,
        cellRenderer: (params: ICellRendererParams<SampleRow>) => {
          const row = params.data;
          if (!row) return null;
          return <FindingsBadges findings={row.findings} />;
        },
        comparator: (a: Finding[], b: Finding[]) => a.length - b.length,
      },
      {
        headerName: "Count",
        width: 90,
        valueGetter: (params: { data?: SampleRow }) =>
          params.data?.findings.length ?? 0,
      },
    ],
    [],
  );

  const onRowClicked = (event: { data?: SampleRow }) => {
    const row = event.data;
    if (row && row.findings.length > 0) {
      setSelectedFinding(row.findings[0]);
      setActiveTab("findings");
    }
  };

  return (
    <div className="flex-grow-1 d-flex flex-column" style={{ minHeight: 0 }}>
      <div style={{ width: "100%", height: "100%", flex: 1, minHeight: 0 }}>
        <AgGridReact<SampleRow>
          theme={themeQuartz}
          rowData={rows}
          columnDefs={columnDefs}
          onRowClicked={onRowClicked}
          rowSelection="single"
          getRowStyle={(params) => {
            if (params.data && params.data.findings.length === 0) {
              return { opacity: "0.5" };
            }
            return undefined;
          }}
        />
      </div>
    </div>
  );
}
