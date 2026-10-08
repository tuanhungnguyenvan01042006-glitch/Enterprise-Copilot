import { useQuery } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { ApiUser, getCurrentUser } from "../../lib/api";

type GuardProps = {
  accountType?: ApiUser["account_type"];
  managerOnly?: boolean;
  allowPasswordChange?: boolean;
};

export function AuthGuard({ accountType, managerOnly = false, allowPasswordChange = false }: GuardProps) {
  const location = useLocation();
  const currentUser = useQuery({ queryKey: ["current-user"], queryFn: getCurrentUser, retry: false });

  if (currentUser.isPending) return <LoadingState />;
  if (currentUser.isError) return <Navigate to="/login" replace state={{ sessionExpired: true, from: `${location.pathname}${location.search}` }} />;

  const user = currentUser.data;
  if (user.must_change_password && !allowPasswordChange) return <Navigate to="/change-password" replace />;
  if (accountType && user.account_type !== accountType) {
    return <ErrorState message="Bạn không có quyền truy cập khu vực này." />;
  }
  if (managerOnly && user.department_role !== "MANAGER") {
    return <ErrorState message="Trang này chỉ dành cho Quản lý." />;
  }
  return <Outlet />;
}
