import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { ErrorState } from "./ErrorState";
import { LoadingState } from "./LoadingState";
import { getCurrentUser, logout } from "../lib/api";

const staffLinks = [
  { to: "/app/dashboard", label: "Tổng quan" },
  { to: "/app/workspace", label: "Không gian cá nhân" },
  { to: "/app/knowledge", label: "Kho kiến thức" },
];

const adminLinks = [
  { to: "/admin/overview", label: "Tổng quan quản trị" },
  { to: "/admin/users", label: "Tài khoản" },
  { to: "/admin/documents", label: "Tài liệu" },
  { to: "/admin/announcements", label: "Thông báo" },
  { to: "/admin/audit-logs", label: "Nhật ký hệ thống" },
];

export function AppShell({ admin = false }: { admin?: boolean }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const currentUser = useQuery({ queryKey: ["current-user"], queryFn: getCurrentUser, retry: false });
  const logoutMutation = useMutation({
    mutationFn: logout,
    onSettled: () => {
      queryClient.clear();
      navigate("/login", { replace: true });
    },
  });
  if (currentUser.isPending) return <LoadingState label="Đang tải không gian làm việc..." />;
  if (currentUser.isError || !currentUser.data) return <ErrorState message="Không thể tải thông tin tài khoản." onRetry={() => void currentUser.refetch()} />;
  const user = currentUser.data;
  const links = admin ? adminLinks : user.department_role === "MANAGER"
    ? [...staffLinks, { to: "/app/team", label: "Quản lý phòng ban" }, { to: "/app/announcements", label: "Thông báo" }]
    : staffLinks;

  return (
    <div className="dashboard-shell">
      <aside className="sidebar">
        <div className="sidebar-brand"><span className="brand-mark brand-mark-small">EC</span><span>Enterprise<br />Copilot</span></div>
        <nav aria-label="Điều hướng chính">
          {links.map((link) => <NavLink key={link.to} to={link.to} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>{link.label}</NavLink>)}
        </nav>
        <div className="sidebar-meta">{admin ? "Khu vực quản trị" : user.department_role === "MANAGER" ? "Quản lý" : "Nhân viên"}</div>
      </aside>
      <div className="main-column">
        <header className="topbar">
          <div><p className="topbar-kicker">ENTERPRISE COPILOT</p><strong>{admin ? "Quản trị hệ thống" : "Không gian làm việc"}</strong></div>
          <details className="account-menu">
            <summary aria-label="Mở menu tài khoản"><span className="avatar">{user.full_name.slice(0, 1).toUpperCase()}</span><span className="account-copy"><strong>{user.full_name}</strong><small>{user.email}</small></span></summary>
            <div className="account-popover">
              <NavLink to={admin ? "/admin/profile" : "/app/profile"}>Hồ sơ cá nhân</NavLink>
              <NavLink to="/change-password">Đổi mật khẩu</NavLink>
              <button type="button" disabled={logoutMutation.isPending} onClick={() => logoutMutation.mutate()}>Đăng xuất</button>
            </div>
          </details>
        </header>
        <main className="content"><Outlet /></main>
      </div>
    </div>
  );
}
