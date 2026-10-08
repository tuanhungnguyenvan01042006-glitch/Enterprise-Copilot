import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App, { queryClient } from "./App";
import type { ApiUser } from "./lib/api";

const manager: ApiUser = {
  id: "00000000-0000-0000-0000-000000000001",
  email: "manager@example.test",
  full_name: "Nguyễn Quản Lý",
  employee_code: "M001",
  job_title: "Manager",
  account_type: "STAFF",
  department_role: "MANAGER",
  department_id: 1,
  is_active: true,
  must_change_password: false,
  revision: 1,
};

afterEach(() => {
  cleanup();
  queryClient.clear();
  vi.unstubAllGlobals();
});

describe("Phase 2 application shell", () => {
  it("renders the login screen", () => {
    window.history.pushState({}, "", "/login");
    render(<App />);
    expect(screen.getByRole("heading", { name: "Đăng nhập" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email công việc")).toBeInTheDocument();
  });

  it("shows the manager-only navigation to a manager", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(manager), { status: 200 })));
    window.history.pushState({}, "", "/app/team");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Quản lý phòng ban" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Quản lý phòng ban" })).toBeInTheDocument();
  });

  it("redirects required-password-change users", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...manager, must_change_password: true }), { status: 200 })));
    window.history.pushState({}, "", "/app/dashboard");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Đổi mật khẩu" })).toBeInTheDocument();
  });

  it("blocks an employee from the manager route", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...manager, department_role: "EMPLOYEE" }), { status: 200 })));
    window.history.pushState({}, "", "/app/team");
    render(<App />);
    expect(await screen.findByText("Trang này chỉ dành cho Quản lý.")).toBeInTheDocument();
  });

  it("blocks an admin from the personal workspace", async () => {
    const admin = { ...manager, email: "admin@example.test", account_type: "ADMIN", department_role: null, department_id: null, employee_code: null };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(admin), { status: 200 })));
    window.history.pushState({}, "", "/app/workspace");
    render(<App />);
    expect(await screen.findByText("Bạn không có quyền truy cập khu vực này.")).toBeInTheDocument();
  });
});
