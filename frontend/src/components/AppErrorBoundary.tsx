import { Component, ErrorInfo, ReactNode } from "react";

type Props = { children: ReactNode };
type State = { hasError: boolean };

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled application error", error, info.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <main className="auth-shell">
        <section className="auth-card" aria-labelledby="app-error-title">
          <div className="brand-mark">EC</div>
          <p className="eyebrow">ENTERPRISE COPILOT</p>
          <h1 id="app-error-title">Đã xảy ra lỗi</h1>
          <p className="muted">Ứng dụng gặp sự cố không mong muốn. Hãy tải lại trang để thử lại.</p>
          <button type="button" onClick={() => window.location.reload()}>Tải lại ứng dụng</button>
        </section>
      </main>
    );
  }
}
