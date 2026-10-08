export function LoadingState({ label = "Đang tải..." }: { label?: string }) {
  return (
    <div className="status-panel" role="status" aria-live="polite">
      <span className="loading-spinner" aria-hidden="true" />
      <p className="status-text">{label}</p>
    </div>
  );
}

