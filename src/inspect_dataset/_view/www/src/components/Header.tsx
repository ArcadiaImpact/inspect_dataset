import { NavLink } from "react-router-dom";
import { useStore } from "../store";

export function Header() {
  const summary = useStore((s) => s.summary);
  const findings = useStore((s) => s.findings);

  const confirmed = findings.filter(
    (f) => f.triage_status === "confirmed",
  ).length;
  const dismissed = findings.filter(
    (f) => f.triage_status === "dismissed",
  ).length;

  return (
    <nav className="navbar navbar-expand bg-body-tertiary border-bottom px-3">
      <span className="navbar-brand fw-bold">inspect-dataset</span>
      {summary && (
        <span className="navbar-text me-auto">
          <span className="fw-semibold">{summary.dataset_name}</span>
          {summary.split && (
            <span className="text-body-secondary ms-1">
              [{summary.split}]
            </span>
          )}
          <span className="text-body-secondary ms-2">
            {summary.total_samples.toLocaleString()} samples
          </span>
        </span>
      )}

      <ul className="nav nav-pills me-3">
        <li className="nav-item">
          <NavLink
            to="/findings"
            className={({ isActive }) =>
              `nav-link${isActive ? " active" : ""}`
            }
          >
            Findings
            <span className="badge bg-secondary ms-1">{findings.length}</span>
          </NavLink>
        </li>
        <li className="nav-item">
          <NavLink
            to="/samples"
            className={({ isActive }) =>
              `nav-link${isActive ? " active" : ""}`
            }
          >
            Samples
          </NavLink>
        </li>
      </ul>

      <span className="navbar-text small text-body-secondary">
        {confirmed} confirmed · {dismissed} dismissed
      </span>
    </nav>
  );
}
