import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { getDashboard } from "../../lib/api";

const dateText = (value: string | null) => value ? new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(new Date(value)) : "Chưa đặt hạn";

export function DashboardPage() {
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: getDashboard });
  if (dashboard.isPending) return <LoadingState />;
  if (dashboard.isError) return <ErrorState message={dashboard.error.message} />;
  const data = dashboard.data;
  const stats = [["Việc đang mở", data.stats.open_tasks], ["Việc quá hạn", data.stats.overdue_tasks], ["Việc được giao", data.stats.open_assigned_tasks], ["Tài liệu đã lưu", data.stats.saved_documents]];
  return <section className="page-stack" aria-labelledby="dashboard-title">
    <div className="page-heading"><p className="eyebrow">TỔNG QUAN</p><h1 id="dashboard-title">Xin chào, {data.user.full_name}</h1><p className="muted">Phòng Vận hành · {data.user.department_role === "MANAGER" ? "Manager" : "Employee"}</p></div>
    <div className="stat-grid">{stats.map(([label, value]) => <div className="stat-card surface" key={label}><span className="muted">{label}</span><strong>{value}</strong></div>)}</div>
    {data.department_summary && <div className="surface dashboard-section"><div className="panel-toolbar"><div><h2>Phòng ban</h2><p className="muted">Tổng quan công việc được giao trong phòng ban.</p></div><Link className="button-secondary dashboard-link" to="/app/team">Mở không gian phòng ban</Link></div><div className="mini-stat-grid"><div><strong>{data.department_summary.active_employee_count}</strong><span>Nhân viên hoạt động</span></div><div><strong>{data.department_summary.open_assigned_task_count}</strong><span>Việc đang mở</span></div><div><strong>{data.department_summary.overdue_assigned_task_count}</strong><span>Việc quá hạn</span></div></div></div>}
    <div className="dashboard-columns">
      <div className="surface dashboard-section"><div className="section-heading"><h2>Việc ưu tiên</h2><Link to="/app/workspace">Xem tất cả</Link></div>{data.priority_tasks.length === 0 ? <p className="muted">Bạn không có việc đang mở.</p> : <div className="dashboard-list">{data.priority_tasks.map((task) => <div className="dashboard-list-row" key={task.id}><div><strong>{task.title}</strong><small>{task.kind === "ASSIGNED" ? "Được giao" : "Cá nhân"} · {task.status}</small></div><span className={task.due_date && new Date(task.due_date) < new Date() ? "badge badge-overdue" : "muted"}>{dateText(task.due_date)}</span></div>)}</div>}</div>
      <div className="surface dashboard-section"><div className="section-heading"><h2>Thông báo mới</h2>{data.user.department_role === "MANAGER" && <Link to="/app/announcements">Quản lý</Link>}</div>{data.announcements.length === 0 ? <p className="muted">Chưa có thông báo đang hoạt động.</p> : <div className="dashboard-list">{data.announcements.map((item) => <article className="announcement-preview" key={item.id}><strong>{item.title}</strong><p>{item.body}</p><small>{new Date(item.created_at).toLocaleDateString("vi-VN")}</small></article>)}</div>}</div>
    </div>
    <div className="surface dashboard-section"><div className="section-heading"><h2>Tài liệu cập nhật gần đây</h2><Link to="/app/knowledge">Mở kho kiến thức</Link></div>{data.recent_documents.length === 0 ? <p className="muted">Chưa có tài liệu phù hợp.</p> : <div className="dashboard-document-grid">{data.recent_documents.map((doc) => <div key={doc.id}><span className="badge">{doc.category}</span><strong>{doc.title}</strong><small>Cập nhật {new Date(doc.updated_at).toLocaleDateString("vi-VN")}</small></div>)}</div>}</div>
    <div className="quick-actions"><Link to="/app/workspace">+ Tạo công việc</Link><Link to="/app/workspace">+ Tạo ghi chú</Link><Link to="/app/knowledge">Mở thư viện tài liệu</Link></div>
  </section>;
}
