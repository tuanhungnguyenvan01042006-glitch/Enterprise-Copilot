import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const employeeEmail = process.env.E2E_EMPLOYEE_EMAIL ?? "employee01@example.test";
const employeePassword = process.env.E2E_EMPLOYEE_PASSWORD;
const managerEmail = process.env.E2E_MANAGER_EMAIL ?? "manager@example.test";
const managerPassword = process.env.E2E_MANAGER_PASSWORD;
const employeeTaskTitle = `E2E assignment ${Date.now()}`;

async function login(page: Page, email: string, password: string | undefined) {
  test.skip(!password, "Set E2E_EMPLOYEE_PASSWORD and E2E_MANAGER_PASSWORD for the seeded environment.");
  await page.goto("/login");
  await page.getByLabel("Email công việc").fill(email);
  await page.getByLabel("Mật khẩu").fill(password!);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
}

test.describe.serial("critical application flows", () => {
  test("Flow A: employee data survives refresh", async ({ page }) => {
    await login(page, employeeEmail, employeePassword);
    await page.goto("/app/workspace");
    await page.getByRole("button", { name: "+ Công việc mới" }).click();
    await page.getByLabel("Tiêu đề").fill(`E2E personal ${Date.now()}`);
    await page.getByRole("button", { name: "Lưu", exact: true }).click();
    await expect(page.getByText(/E2E personal/)).toBeVisible();

    await page.getByRole("tab", { name: "Ghi chú" }).click();
    await page.getByRole("button", { name: "+ Ghi chú mới" }).click();
    await page.getByLabel("Tiêu đề").fill(`E2E note ${Date.now()}`);
    await page.getByLabel("Nội dung").fill("Persistence smoke test");
    await page.getByRole("button", { name: "Lưu ghi chú" }).click();
    await expect(page.getByText("Persistence smoke test")).toBeVisible();
    await page.reload();
    await expect(page.getByText("Persistence smoke test")).toBeVisible();
  });

  test("Flow B: manager assignment is visible to the employee", async ({ browser }) => {
    test.skip(!employeePassword || !managerPassword, "Seed credentials are required.");
    const manager = await browser.newPage();
    await login(manager, managerEmail, managerPassword);
    await manager.goto("/app/team");
    await manager.getByRole("button", { name: "+ Giao việc" }).click();
    await manager.getByLabel("Tiêu đề").fill(employeeTaskTitle);
    await manager.getByLabel("Người nhận").selectOption({ label: "Operations Employee 01 · E001" });
    await manager.getByRole("button", { name: "Lưu", exact: true }).click();
    await expect(manager.getByText(employeeTaskTitle)).toBeVisible();

    const employee = await browser.newPage();
    await login(employee, employeeEmail, employeePassword);
    await employee.goto("/app/workspace");
    await expect(employee.getByText(employeeTaskTitle)).toBeVisible();
    await employee.getByRole("button", { name: "Cập nhật trạng thái" }).click();
    await employee.getByLabel("Trạng thái").selectOption("DONE");
    await employee.getByRole("button", { name: "Lưu", exact: true }).click();
    await expect(employee.getByText("DONE")).toBeVisible();
    await manager.reload();
    await expect(manager.getByText("DONE")).toBeVisible();
    await manager.close();
    await employee.close();
  });

  test("health endpoint and SPA deep links are available", async ({ page, request }) => {
    const health = await request.get("/api/v1/health/live");
    expect(health.ok()).toBeTruthy();
    expect(await health.json()).toEqual({ status: "ok" });
    const response = await page.goto("/app/knowledge");
    expect(response?.ok()).toBeTruthy();
    await expect(page).toHaveTitle(/Enterprise Copilot/i);
  });
});
