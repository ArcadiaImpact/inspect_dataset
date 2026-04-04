import { useSearchParams } from "react-router-dom";
import clsx from "clsx";
import { useStore, getScannerCounts } from "../store";

const SEVERITY_COLORS: Record<string, string> = {
  high: "danger",
  medium: "warning",
  low: "secondary",
};

export function ScannerSidebar() {
  const findings = useStore((s) => s.findings);
  const [searchParams, setSearchParams] = useSearchParams();

  const selectedScanner = searchParams.get("scanner");
  const selectedSeverity = searchParams.get("severity");
  const selectedTriageFilter = searchParams.get("triage");

  function setParam(key: string, value: string | null) {
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev);
      if (value) p.set(key, value);
      else p.delete(key);
      return p;
    });
  }

  const counts = getScannerCounts(findings);
  const scanners = Object.entries(counts).sort(([, a], [, b]) => b - a);

  return (
    <div
      className="d-flex flex-column border-end bg-body-tertiary"
      style={{ width: 220, minWidth: 220, overflowY: "auto" }}
    >
      <div className="p-2 border-bottom">
        <small className="text-uppercase text-body-secondary fw-semibold">
          Scanners
        </small>
      </div>

      <div className="list-group list-group-flush">
        <button
          className={clsx(
            "list-group-item list-group-item-action d-flex justify-content-between align-items-center",
            !selectedScanner && "active",
          )}
          onClick={() => setParam("scanner", null)}
        >
          All
          <span className="badge bg-secondary rounded-pill">
            {findings.length}
          </span>
        </button>
        {scanners.map(([name, count]) => (
          <button
            key={name}
            className={clsx(
              "list-group-item list-group-item-action d-flex justify-content-between align-items-center",
              selectedScanner === name && "active",
            )}
            onClick={() =>
              setParam("scanner", selectedScanner === name ? null : name)
            }
          >
            <span className="text-truncate">{name}</span>
            <span className="badge bg-secondary rounded-pill">{count}</span>
          </button>
        ))}
      </div>

      <div className="p-2 border-top border-bottom mt-auto">
        <small className="text-uppercase text-body-secondary fw-semibold">
          Filters
        </small>
      </div>

      <div className="p-2">
        <label className="form-label small mb-1">Severity</label>
        <select
          className="form-select form-select-sm"
          value={selectedSeverity ?? ""}
          onChange={(e) => setParam("severity", e.target.value || null)}
        >
          <option value="">Any</option>
          {Object.keys(SEVERITY_COLORS).map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div className="p-2">
        <label className="form-label small mb-1">Triage</label>
        <select
          className="form-select form-select-sm"
          value={selectedTriageFilter ?? ""}
          onChange={(e) => setParam("triage", e.target.value || null)}
        >
          <option value="">Any</option>
          <option value="pending">Pending</option>
          <option value="confirmed">Confirmed</option>
          <option value="dismissed">Dismissed</option>
        </select>
      </div>
    </div>
  );
}
