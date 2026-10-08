import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { getAdminOverview } from "../../lib/api";

export function AdminOverviewPage() {
  const overview = useQuery({ queryKey: ["admin-overview"], queryFn: getAdminOverview });
  if (overview.isPending) return <LoadingState />;
  if (overview.isError) return <ErrorState message={overview.error.message} />;
  const data = overview.data;
  const stats = [
    ["STAFF hoạt động", data.stats.active_staff_count],
    ["Nhân viên", data.stats.employee_count],
    ["Manager", data.stats.manager_count],
    ["Tài khoản bị khóa", data.stats.locked_account_count],
    ["Tài liệu có file", data.stats.total_document_file_count],
    ["Dung lượng lưu trữ", `${Math.ceil(data.stats.total_stored_file_bytes / 1024)} KB`],
  ];
  return <section className="page-stack" aria-labelledby="admin-overview-title">
    <div className="page-heading"><p className="eyebrow">QUẢN TRỊ HỆ THỐNG</p><h1 id="admin-overview-title">Tổng quan quản trị</h1><p className="muted">Theo dõi tài khoản, tài liệu và nhật ký vận hành.</p></div>
    <div className="stat-grid">{stats.map(([label, value]) => <div className="stat-card surface" key={label}><span className="muted">{label}</span><strong>{value}</strong></div>)}</div>
    <div className="dashboard-columns">
      <div className="surface dashboard-section"><div className="section-heading"><h2>Kho tài liệu</h2><Link to="/admin/documents">Quản lý tài liệu</Link></div><p className="muted">Mỗi tài liệu hiện lưu một file hiện tại.</p></div>
      <div className="surface dashboard-section"><div className="section-heading"><h2>Sẵn sàng hệ thống</h2></div><div className="readiness-list">{Object.entries(data.readiness).map(([key, ready]) => <div key={key}><span>{key.toUpperCase()}</span><strong className={ready ? "member-active" : "member-inactive"}>{ready ? "Sẵn sàng" : "Kiểm tra"}</strong></div>)}</div></div>
    </div>
    <div className="surface dashboard-section"><div className="section-heading"><h2>Audit gần đây</h2><Link to="/admin/audit-logs">Xem nhật ký</Link></div>{data.latest_audit_events.length === 0 ? <p className="muted">Chưa có sự kiện.</p> : <div className="audit-list">{data.latest_audit_events.map((event) => <div className="audit-row" key={event.id}><div><strong>{event.action}</strong><small>{event.actor_name ?? "Hệ thống"} · {event.entity_type ?? "—"}</small></div><time>{new Date(event.created_at).toLocaleString("vi-VN")}</time></div>)}</div>}</div>
  </section>;
}
