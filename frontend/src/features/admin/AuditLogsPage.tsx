import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { getAuditLogs } from "../../lib/api";

export function AuditLogsPage() {
  const [filters, setFilters] = useState({ action: "", result: "" });
  const logs = useQuery({ queryKey: ["audit-logs", filters], queryFn: () => getAuditLogs(filters) });
  if (logs.isPending) return <LoadingState />;
  if (logs.isError) return <ErrorState message={logs.error.message} />;
  return <section className="page-stack" aria-labelledby="audit-title"><div className="page-heading"><p className="eyebrow">QUẢN TRỊ HỆ THỐNG</p><h1 id="audit-title">Nhật ký hệ thống</h1><p className="muted">Theo dõi các hành động quản trị và nghiệp vụ quan trọng.</p></div><div className="filter-row"><input aria-label="Lọc action" placeholder="Action, ví dụ USER_CREATED" value={filters.action} onChange={(event) => setFilters({ ...filters, action: event.target.value })} /><select aria-label="Lọc kết quả" value={filters.result} onChange={(event) => setFilters({ ...filters, result: event.target.value })}><option value="">Mọi kết quả</option><option value="SUCCESS">Thành công</option><option value="FAILURE">Thất bại</option><option value="DENIED">Từ chối</option></select></div>{logs.data.items.length === 0 ? <div className="empty-card small-empty"><h2>Chưa có nhật ký</h2></div> : <div className="surface audit-table"><div className="audit-table-head"><span>Thời gian</span><span>Actor</span><span>Action</span><span>Đối tượng</span><span>Kết quả</span><span>Request ID</span></div>{logs.data.items.map((item) => <div className="audit-table-row" key={item.id}><time>{new Date(item.created_at).toLocaleString("vi-VN")}</time><span>{item.actor_name ?? "Hệ thống"}</span><strong>{item.action}</strong><span>{item.entity_type ?? "—"} · {item.entity_id ?? "—"}</span><span className="badge">{item.result}</span><code>{item.request_id}</code></div>)}</div>}<p className="muted">{logs.data.total} sự kiện</p></section>;
}
