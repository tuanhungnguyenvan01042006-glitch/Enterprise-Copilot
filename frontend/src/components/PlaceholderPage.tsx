export function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <section className="page-stack" aria-labelledby="page-title">
      <div className="page-heading"><p className="eyebrow">ENTERPRISE COPILOT</p><h1 id="page-title">{title}</h1><p className="muted">{description}</p></div>
      <div className="empty-card"><span className="empty-icon">EC</span><h2>Nền tảng đã sẵn sàng</h2><p>Nội dung nghiệp vụ của khu vực này sẽ được triển khai ở phase tương ứng.</p></div>
    </section>
  );
}
