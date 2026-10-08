import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { getCurrentUser, updateProfile } from "../../lib/api";

const schema = z.object({ fullName: z.string().trim().min(1, "Nhập họ và tên.").max(120) });
type FormValues = z.infer<typeof schema>;

export function ProfilePage() {
  const queryClient = useQueryClient();
  const currentUser = useQuery({ queryKey: ["current-user"], queryFn: getCurrentUser, retry: false });
  const user = currentUser.data!;
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { fullName: user.full_name } });
  useEffect(() => form.reset({ fullName: user.full_name }), [form, user.full_name]);
  const mutation = useMutation({ mutationFn: (values: FormValues) => updateProfile(values.fullName, user.revision), onSuccess: (updated) => { queryClient.setQueryData(["current-user"], updated); form.reset({ fullName: updated.full_name }); } });
  return <section className="page-stack" aria-labelledby="profile-title"><div className="page-heading"><p className="eyebrow">TÀI KHOẢN</p><h1 id="profile-title">Hồ sơ cá nhân</h1><p className="muted">Thông tin công việc và tên hiển thị của bạn.</p></div><div className="surface profile-grid"><div><span className="profile-avatar">{user.full_name.slice(0, 1).toUpperCase()}</span><p><strong>{user.email}</strong></p><p className="muted">{user.job_title ?? (user.account_type === "ADMIN" ? "Quản trị viên" : "Nhân viên")}</p><dl className="profile-facts"><div><dt>Mã nhân viên</dt><dd>{user.employee_code ?? "—"}</dd></div><div><dt>Vai trò</dt><dd>{user.department_role ?? "ADMIN"}</dd></div><div><dt>Phòng ban</dt><dd>{user.department_id ? "Phòng Vận hành" : "—"}</dd></div><div><dt>Ngày tạo</dt><dd>{user.created_at ? new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(new Date(user.created_at)) : "—"}</dd></div></dl></div><form className="stack-form" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}><label>Họ và tên<input {...form.register("fullName")} />{form.formState.errors.fullName && <span className="field-error">{form.formState.errors.fullName.message}</span>}</label><label>Email<input value={user.email} disabled readOnly /></label>{mutation.isError && <p className="form-error">{mutation.error.message}</p>}{mutation.isSuccess && <p className="form-success">Đã cập nhật hồ sơ.</p>}<button type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Đang lưu..." : "Lưu thay đổi"}</button></form></div></section>;
}
