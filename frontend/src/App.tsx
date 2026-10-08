import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { AppErrorBoundary } from "./components/AppErrorBoundary";
import { AuthGuard } from "./features/auth/AuthGuard";
import { ChangePasswordPage } from "./features/auth/ChangePasswordPage";
import { LoginPage } from "./features/auth/LoginPage";
import { ProfilePage } from "./features/profile/ProfilePage";
import { TeamPage } from "./features/team/TeamPage";
import { WorkspacePage } from "./features/workspace/WorkspacePage";
import { KnowledgePage } from "./features/knowledge/KnowledgePage";
import { DocumentDetailPage } from "./features/knowledge/DocumentDetailPage";
import { DashboardPage } from "./features/dashboard/DashboardPage";
import { AnnouncementsPage } from "./features/announcements/AnnouncementsPage";
import { AdminOverviewPage } from "./features/admin/AdminOverviewPage";
import { AdminUsersPage } from "./features/admin/AdminUsersPage";
import { AuditLogsPage } from "./features/admin/AuditLogsPage";

export const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false } },
});

function SessionLifecycle() {
  const navigate = useNavigate();
  useEffect(() => {
    const handleExpired = () => {
      queryClient.clear();
      navigate("/login", { replace: true, state: { sessionExpired: true } });
    };
    window.addEventListener("auth:session-expired", handleExpired);
    return () => window.removeEventListener("auth:session-expired", handleExpired);
  }, [navigate]);
  return null;
}

function AppRoutes() {
  return (
    <>
      <SessionLifecycle />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<AuthGuard allowPasswordChange />}><Route path="/change-password" element={<ChangePasswordPage />} /></Route>

        <Route element={<AuthGuard accountType="STAFF" />}>
          <Route path="/app" element={<AppShell />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="workspace" element={<WorkspacePage />} />
            <Route path="knowledge" element={<KnowledgePage />} />
            <Route path="knowledge/:documentId" element={<DocumentDetailPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route element={<AuthGuard accountType="STAFF" managerOnly />}><Route path="team" element={<TeamPage />} /><Route path="announcements" element={<AnnouncementsPage />} /></Route>
          </Route>
        </Route>

        <Route element={<AuthGuard accountType="ADMIN" />}>
          <Route path="/admin" element={<AppShell admin />}>
            <Route index element={<Navigate to="overview" replace />} />
            <Route path="overview" element={<AdminOverviewPage />} />
            <Route path="users" element={<AdminUsersPage />} />
            <Route path="documents" element={<KnowledgePage admin />} />
            <Route path="documents/:documentId" element={<DocumentDetailPage admin />} />
            <Route path="announcements" element={<AnnouncementsPage admin />} />
            <Route path="audit-logs" element={<AuditLogsPage />} />
            <Route path="profile" element={<ProfilePage />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </>
  );
}

export default function App() {
  return <AppErrorBoundary><QueryClientProvider client={queryClient}><BrowserRouter><AppRoutes /></BrowserRouter></QueryClientProvider></AppErrorBoundary>;
}
