import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { login } from "../../lib/api";

const loginSchema = z.object({
  email: z.string().email("Nhập email hợp lệ."),
  password: z.string().min(1, "Nhập mật khẩu."),
});

type LoginForm = z.infer<typeof loginSchema>;

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const routeState = location.state as { sessionExpired?: boolean; passwordChanged?: boolean } | null;
  const loginMutation = useMutation({
    mutationFn: (values: LoginForm) => login(values.email, values.password),
    onSuccess: ({ user }) => {
      queryClient.clear();
      queryClient.setQueryData(["current-user"], user);
      navigate(user.must_change_password ? "/change-password" : user.account_type === "ADMIN" ? "/admin/overview" : "/app/dashboard", {
        replace: true,
      });
    },
  });
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="login-title">
        <div className="brand-mark">EC</div>
        <p className="eyebrow">ENTERPRISE COPILOT</p>
        <h1 id="login-title">Đăng nhập</h1>
        <p className="muted">Truy cập không gian làm việc nội bộ của bạn.</p>
        {routeState?.sessionExpired && <p className="form-notice">Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.</p>}
        {routeState?.passwordChanged && <p className="form-success">Mật khẩu đã được đổi. Vui lòng đăng nhập lại.</p>}
        <form className="stack-form" onSubmit={handleSubmit((values) => loginMutation.mutate(values))}>
          <label>
            Email công việc
            <input type="email" autoComplete="email" placeholder="you@example.test" {...register("email")} />
            {errors.email && <span className="field-error">{errors.email.message}</span>}
          </label>
          <label>
            Mật khẩu
            <input type="password" autoComplete="current-password" {...register("password")} />
            {errors.password && <span className="field-error">{errors.password.message}</span>}
          </label>
          {loginMutation.isError && <p className="form-error">{loginMutation.error.message}</p>}
          <button type="submit" disabled={loginMutation.isPending}>
            {loginMutation.isPending ? "Đang đăng nhập..." : "Đăng nhập"}
          </button>
        </form>
      </section>
    </main>
  );
}
