import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useStore } from "./store";
import { useKeyboard } from "./hooks/useKeyboard";
import { Header } from "./components/Header";
import { ScannerSidebar } from "./components/ScannerSidebar";
import { FindingsList } from "./components/FindingsList";
import { FindingDetail } from "./components/FindingDetail";
import { SamplesTab } from "./components/SamplesTab";
import { exportUrl } from "./api";

function FindingsPage() {
  return (
    <>
      <ScannerSidebar />
      <FindingsList />
      <FindingDetail />
    </>
  );
}

function App() {
  const loadData = useStore((s) => s.loadData);
  const loading = useStore((s) => s.loading);
  const error = useStore((s) => s.error);

  useKeyboard();

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="d-flex align-items-center justify-content-center vh-100">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="d-flex align-items-center justify-content-center vh-100">
        <div className="alert alert-danger">{error}</div>
      </div>
    );
  }

  return (
    <div className="d-flex flex-column vh-100">
      <Header />

      <div className="d-flex flex-grow-1" style={{ minHeight: 0 }}>
        <Routes>
          <Route path="/" element={<Navigate to="/findings" replace />} />
          <Route path="/findings" element={<FindingsPage />} />
          <Route path="/samples" element={<SamplesTab />} />
        </Routes>
      </div>

      <footer className="border-top bg-body-tertiary px-3 py-1 d-flex justify-content-between align-items-center small text-body-secondary">
        <span>
          Keyboard: <kbd>c</kbd> confirm · <kbd>d</kbd> dismiss ·{" "}
          <kbd>n</kbd>/<kbd>p</kbd> next/prev
        </span>
        <a
          href={exportUrl()}
          className="btn btn-sm btn-outline-secondary"
          download
        >
          Export clean_ids.txt
        </a>
      </footer>
    </div>
  );
}

export default App;
