import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { changePassword } from "../../lib/api";

const schema = z
  .object({
    currentPassword: z.string().min(1, "Nhập mật khẩu hiện tại."),
    newPassword: z.string().min(12, "Mật khẩu mới cần ít nhất 12 ký tự.").max(128),
    confirmation: z.string(),
  })
  .refine((values) => values.newPassword === values.confirmation, {
    message: "Mật khẩu xác nhận chưa khớp.",
    path: ["confirmation"],
  });

type FormValues = z.infer<typeof schema>;

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (values: FormValues) => changePassword(values.currentPassword, values.newPassword),
    onSuccess: () => {
      queryClient.clear();
      navigate("/login", { replace: true, state: { passwordChanged: true } });
    },
  });
  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({ resolver: zodResolver(schema) });

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="change-password-title">
        <div className="brand-mark">EC</div>
        <p className="eyebrow">BẢO MẬT TÀI KHOẢN</p>
        <h1 id="change-password-title">Đổi mật khẩu</h1>
        <p className="muted">Sau khi đổi mật khẩu, tất cả phiên đăng nhập sẽ kết thúc.</p>
        <form className="stack-form" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
          <label>Mật khẩu hiện tại<input type="password" autoComplete="current-password" {...register("currentPassword")} />{errors.currentPassword && <span className="field-error">{errors.currentPassword.message}</span>}</label>
          <label>Mật khẩu mới<input type="password" autoComplete="new-password" {...register("newPassword")} />{errors.newPassword && <span className="field-error">{errors.newPassword.message}</span>}</label>
          <label>Xác nhận mật khẩu mới<input type="password" autoComplete="new-password" {...register("confirmation")} />{errors.confirmation && <span className="field-error">{errors.confirmation.message}</span>}</label>
          {mutation.isError && <p className="form-error">{mutation.error.message}</p>}
          <button type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Đang cập nhật..." : "Đổi mật khẩu"}</button>
        </form>
      </section>
    </main>
  );
}
