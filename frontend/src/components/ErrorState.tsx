type ErrorStateProps = { message: string; onRetry?: () => void };

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="status-panel status-panel-error" role="alert">
      <p className="status-text status-error">{message}</p>
      {onRetry && <button type="button" className="button-secondary" onClick={onRetry}>Thử lại</button>}
    </div>
  );
}

