import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { AdminUser, createAdminUser, getAdminUsers, resetAdminUserPassword, updateAdminUser } from "../../lib/api";

function UserForm({ user, onDone, onTemporaryPassword }: { user?: AdminUser; onDone: () => void; onTemporaryPassword: (value: string) => void }) {
  const queryClient = useQueryClient();
  const [values, setValues] = useState({ email: user?.email ?? "", full_name: user?.full_name ?? "", employee_code: user?.employee_code ?? "", job_title: user?.job_title ?? "", department_role: user?.department_role ?? "EMPLOYEE", is_active: user?.is_active ?? true });
  const save = useMutation({
    mutationFn: async (): Promise<{ temporary_password?: string }> => {
      if (user) {
        await updateAdminUser(user.id, { expected_revision: user.revision, full_name: values.full_name, employee_code: values.employee_code, job_title: values.job_title || null, department_role: values.department_role, is_active: values.is_active });
        return {};
      }
      return createAdminUser({ email: values.email, full_name: values.full_name, employee_code: values.employee_code, job_title: values.job_title || undefined, department_role: values.department_role });
    },
    onSuccess: (result) => { queryClient.invalidateQueries({ queryKey: ["admin-users"] }); if (result.temporary_password) onTemporaryPassword(result.temporary_password); onDone(); },
  });
  const set = (key: keyof typeof values, value: string | boolean) => setValues((current) => ({ ...current, [key]: value }));
  return <form className="workspace-form compact-form surface" onSubmit={(event: FormEvent) => { event.preventDefault(); save.mutate(); }}><div className="form-row">{!user && <label>Email<input type="email" required value={values.email} onChange={(event) => set("email", event.target.value)} /></label>}<label>Họ và tên<input required maxLength={120} value={values.full_name} onChange={(event) => set("full_name", event.target.value)} /></label></div><div className="form-row"><label>Mã nhân viên<input required maxLength={30} value={values.employee_code} onChange={(event) => set("employee_code", event.target.value)} /></label><label>Chức danh<input maxLength={120} value={values.job_title} onChange={(event) => set("job_title", event.target.value)} /></label></div><div className="form-row"><label>Vai trò<select value={values.department_role} onChange={(event) => set("department_role", event.target.value)}><option value="EMPLOYEE">Employee</option><option value="MANAGER">Manager</option></select></label>{user && <label>Trạng thái<select value={String(values.is_active)} onChange={(event) => set("is_active", event.target.value === "true")}><option value="true">Đang hoạt động</option><option value="false">Đã khóa</option></select></label>}</div>{save.isError && <p className="form-error">{save.error.message}</p>}<div className="button-row"><button type="submit" disabled={save.isPending}>{save.isPending ? "Đang lưu..." : "Lưu tài khoản"}</button><button type="button" className="button-secondary" onClick={onDone}>Hủy</button></div></form>;
}

export function AdminUsersPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({ q: "", role: "", is_active: "" });
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [creating, setCreating] = useState(false);
  const [temporaryPassword, setTemporaryPassword] = useState<string | null>(null);
  const users = useQuery({ queryKey: ["admin-users", filters], queryFn: () => getAdminUsers(filters) });
  const reset = useMutation({ mutationFn: ({ user, password }: { user: AdminUser; password: string }) => resetAdminUserPassword(user.id, password), onSuccess: (result) => { queryClient.invalidateQueries({ queryKey: ["admin-users"] }); setTemporaryPassword(result.temporary_password); } });
  if (users.isPending) return <LoadingState />;
  if (users.isError) return <ErrorState message={users.error.message} />;
  return <section className="page-stack" aria-labelledby="admin-users-title"><div className="page-heading"><p className="eyebrow">QUẢN TRỊ HỆ THỐNG</p><h1 id="admin-users-title">Tài khoản STAFF</h1><p className="muted">Tạo, cập nhật vai trò và kiểm soát trạng thái tài khoản nhân viên.</p></div>{temporaryPassword && <div className="form-notice"><strong>Mật khẩu tạm thời:</strong> <code>{temporaryPassword}</code><button type="button" className="button-secondary" onClick={() => setTemporaryPassword(null)}>Đã ghi lại</button></div>}<div className="filter-row"><input aria-label="Tìm STAFF" placeholder="Tìm tên, email, mã nhân viên" value={filters.q} onChange={(event) => setFilters({ ...filters, q: event.target.value })} /><select aria-label="Lọc vai trò" value={filters.role} onChange={(event) => setFilters({ ...filters, role: event.target.value })}><option value="">Tất cả vai trò</option><option value="EMPLOYEE">Employee</option><option value="MANAGER">Manager</option></select><select aria-label="Lọc trạng thái" value={filters.is_active} onChange={(event) => setFilters({ ...filters, is_active: event.target.value })}><option value="">Tất cả trạng thái</option><option value="true">Hoạt động</option><option value="false">Đã khóa</option></select><button type="button" onClick={() => { setCreating(true); setEditing(null); }}>+ Tạo STAFF</button></div>{creating && <UserForm onDone={() => setCreating(false)} onTemporaryPassword={setTemporaryPassword} />}{editing && <UserForm user={editing} onDone={() => setEditing(null)} onTemporaryPassword={setTemporaryPassword} />}<div className="admin-user-list">{users.data.items.map((user) => <article className="member-card" key={user.id}><div><h3>{user.full_name}</h3><p className="muted">{user.email} · {user.employee_code} · {user.job_title ?? "Chưa cập nhật chức danh"}</p><div className="badge-row"><span className="badge">{user.department_role}</span><span className={user.is_active ? "member-active" : "member-inactive"}>{user.is_active ? "Đang hoạt động" : "Đã khóa"}</span></div></div><div className="button-row"><button type="button" className="button-secondary" onClick={() => { setEditing(user); setCreating(false); }}>Sửa</button><button type="button" className="button-secondary" disabled={reset.isPending} onClick={() => { const password = window.prompt("Nhập lại mật khẩu Admin để reset:"); if (password) reset.mutate({ user, password }); }}>Reset mật khẩu</button></div></article>)}</div><p className="muted">{users.data.total} tài khoản STAFF</p></section>;
}
