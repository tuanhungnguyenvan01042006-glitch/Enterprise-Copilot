export type ApiUser = {
  id: string;
  email: string;
  full_name: string;
  employee_code: string | null;
  job_title: string | null;
  account_type: "STAFF" | "ADMIN";
  department_role: "EMPLOYEE" | "MANAGER" | null;
  department_id: number | null;
  is_active: boolean;
  must_change_password: boolean;
  revision: number;
  created_at?: string;
};

export type Task = {
  id: string;
  department_id: number;
  kind: "PERSONAL" | "ASSIGNED";
  title: string;
  description: string | null;
  status: "TODO" | "IN_PROGRESS" | "DONE" | "CANCELLED";
  priority: "LOW" | "NORMAL" | "HIGH";
  assignee_id: string;
  created_by: string;
  due_date: string | null;
  completed_at: string | null;
  revision: number;
  created_at: string;
  updated_at: string;
};

export type Note = {
  id: string;
  title: string;
  content: string;
  revision: number;
  created_at: string;
  updated_at: string;
};

export type Bookmark = { document_id: string; title: string; category: string; updated_at: string };

export type DocumentFile = { original_filename: string; mime_type: string; size_bytes: number; checksum_sha256: string; uploaded_by: string; uploaded_at: string };
export type Document = { id: string; knowledge_scope: "COMPANY" | "DEPARTMENT"; department_id: number | null; title: string; description: string | null; category: "POLICY" | "SOP" | "GUIDE" | "REFERENCE"; language: "vi" | "en" | "other"; created_by: string; updated_by: string; creator_name: string | null; updater_name: string | null; revision: number; created_at: string; updated_at: string; file: DocumentFile | null; permissions: { can_edit: boolean; can_upload_file: boolean; can_bookmark: boolean } };

export type Announcement = { id: string; department_id: number; title: string; body: string; created_by: string; updated_by: string; archived_at: string | null; revision: number; created_at: string; updated_at: string };
export type Dashboard = {
  user: ApiUser;
  stats: { open_tasks: number; overdue_tasks: number; open_assigned_tasks: number; saved_documents: number };
  priority_tasks: Array<{ id: string; title: string; status: string; priority: string; kind: string; due_date: string | null }>;
  announcements: Announcement[];
  recent_documents: Array<{ id: string; title: string; category: string; updated_at: string }>;
  department_summary: { active_employee_count: number; open_assigned_task_count: number; overdue_assigned_task_count: number } | null;
};
export type AdminOverview = {
  stats: Record<string, number>;
  latest_audit_events: AuditLog[];
  readiness: { api: boolean; database: boolean; storage: boolean };
};
export type AdminUser = ApiUser;
export type AuditLog = { id: number; actor_id: string | null; actor_name: string | null; action: string; entity_type: string | null; entity_id: string | null; result: string; request_id: string; details: Record<string, unknown>; created_at: string };

export type DepartmentMember = {
  id: string;
  full_name: string;
  email: string;
  employee_code: string;
  job_title: string | null;
  department_role: "EMPLOYEE" | "MANAGER";
  is_active: boolean;
};

export type DepartmentTask = Task & {
  assignee: DepartmentMember;
  creator: DepartmentMember;
};

type Page<T> = { items: T[]; page: number; page_size: number; total: number };

type ApiErrorPayload = {
  error?: { code?: string; message?: string; details?: unknown };
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
let csrfToken: string | null = null;

export function clearAuthState() {
  csrfToken = null;
}

async function parseError(response: Response): Promise<ApiError> {
  const payload = (await response.json().catch(() => null)) as ApiErrorPayload | null;
  return new ApiError(
    payload?.error?.message ?? "Không thể kết nối đến máy chủ.",
    response.status,
    payload?.error?.code ?? "UNKNOWN_ERROR",
    payload?.error?.details,
  );
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isMultipart = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    credentials: "include",
    headers: isMultipart ? { ...(init?.headers ?? {}) } : { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });

  if (!response.ok) {
    const error = await parseError(response);
    if (error.status === 401) {
      clearAuthState();
      window.dispatchEvent(new CustomEvent("auth:session-expired"));
    }
    throw error;
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function getCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken;
  const response = await request<{ csrf_token: string }>("/auth/csrf");
  csrfToken = response.csrf_token;
  return csrfToken;
}

async function csrfRequest<T>(path: string, init: RequestInit): Promise<T> {
  const token = await getCsrfToken();
  return request<T>(path, {
    ...init,
    headers: { ...(init.headers ?? {}), "X-CSRF-Token": token },
  });
}

export async function login(email: string, password: string) {
  clearAuthState();
  return request<{ user: ApiUser }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getCurrentUser() {
  return request<ApiUser>("/auth/me");
}

export async function logout() {
  try {
    await csrfRequest<void>("/auth/logout", { method: "POST" });
  } finally {
    clearAuthState();
  }
}

export async function changePassword(currentPassword: string, newPassword: string) {
  try {
    await csrfRequest<void>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  } finally {
    clearAuthState();
  }
}

export function updateProfile(fullName: string, expectedRevision: number) {
  return csrfRequest<ApiUser>("/me/profile", {
    method: "PATCH",
    body: JSON.stringify({ full_name: fullName, expected_revision: expectedRevision }),
  });
}

export function getTasks(filters: { kind?: string; status?: string; priority?: string; q?: string } = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
  return request<Task[]>(`/me/tasks${params.toString() ? `?${params.toString()}` : ""}`);
}

export function createTask(payload: Pick<Task, "title" | "description" | "status" | "priority" | "due_date">) {
  return csrfRequest<Task>("/me/tasks", { method: "POST", body: JSON.stringify(payload) });
}

export function updateTask(id: string, payload: Partial<Pick<Task, "title" | "description" | "status" | "priority" | "due_date">> & { expected_revision: number }) {
  return csrfRequest<Task>(`/me/tasks/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function deleteTask(id: string, expectedRevision: number) {
  return csrfRequest<void>(`/me/tasks/${id}?expected_revision=${expectedRevision}`, { method: "DELETE" });
}

export function getNotes(q?: string) {
  return request<Note[]>(q?.trim() ? `/me/notes?q=${encodeURIComponent(q.trim())}` : "/me/notes");
}

export function createNote(payload: Pick<Note, "title" | "content">) {
  return csrfRequest<Note>("/me/notes", { method: "POST", body: JSON.stringify(payload) });
}

export function updateNote(id: string, payload: Partial<Pick<Note, "title" | "content">> & { expected_revision: number }) {
  return csrfRequest<Note>(`/me/notes/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function deleteNote(id: string, expectedRevision: number) {
  return csrfRequest<void>(`/me/notes/${id}?expected_revision=${expectedRevision}`, { method: "DELETE" });
}

export function getBookmarks() {
  return request<Bookmark[]>("/me/bookmarks");
}

export function removeBookmark(documentId: string) {
  return csrfRequest<void>(`/me/bookmarks/${documentId}`, { method: "DELETE" });
}

export function addBookmark(documentId: string) { return csrfRequest<Bookmark>(`/me/bookmarks/${documentId}`, { method: "PUT" }); }
export function getDocuments(filters: { q?: string; category?: string; language?: string; knowledge_scope?: string } = {}) {
  const params = new URLSearchParams(); Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
  return request<{ items: Document[]; page: number; page_size: number; total: number }>(`/documents${params.toString() ? `?${params.toString()}` : ""}`);
}
export function getDocument(id: string) { return request<Document>(`/documents/${id}`); }
export function createDocument(metadata: Record<string, unknown>, file: File) { const form = new FormData(); form.append("metadata", JSON.stringify(metadata)); form.append("file", file); return csrfRequest<Document>("/documents", { method: "POST", body: form }); }
export function uploadDocumentFile(id: string, expectedRevision: number, file: File) { const form = new FormData(); form.append("expected_revision", String(expectedRevision)); form.append("file", file); return csrfRequest<Document>(`/documents/${id}/file`, { method: "POST", body: form }); }
async function blobRequest(path: string): Promise<Blob> { const response = await fetch(`${apiBaseUrl}${path}`, { credentials: "include" }); if (!response.ok) throw await parseError(response); return response.blob(); }
export function downloadDocumentFile(documentId: string) { return blobRequest(`/documents/${documentId}/file/download`); }
export function previewDocumentFile(documentId: string) { return blobRequest(`/documents/${documentId}/file/preview`).then((blob) => blob.text()); }

export function getDepartmentMembers() {
  return request<Page<DepartmentMember>>("/department/members?page_size=100");
}

export function getDepartmentTasks(filters: { assignee_id?: string; status?: string; priority?: string; overdue?: string } = {}) {
  const params = new URLSearchParams({ page: "1", page_size: "100" });
  Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
  return request<Page<DepartmentTask>>(`/department/tasks?${params.toString()}`);
}

export function createDepartmentTask(payload: Pick<DepartmentTask, "title" | "description" | "priority" | "due_date"> & { assignee_id: string }) {
  return csrfRequest<DepartmentTask>("/department/tasks", { method: "POST", body: JSON.stringify(payload) });
}

export function updateDepartmentTask(id: string, payload: Partial<Pick<DepartmentTask, "title" | "description" | "status" | "priority" | "due_date">> & { assignee_id?: string; expected_revision: number }) {
  return csrfRequest<DepartmentTask>(`/department/tasks/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function getDashboard() { return request<Dashboard>("/dashboard"); }
export function getAdminOverview() { return request<AdminOverview>("/admin/overview"); }

export function getAnnouncements(includeArchived = false) {
  return request<Announcement[]>(`/announcements${includeArchived ? "?include_archived=true" : ""}`);
}
export function createAnnouncement(payload: { title: string; body: string; department_id?: number }) {
  return csrfRequest<Announcement>("/announcements", { method: "POST", body: JSON.stringify(payload) });
}
export function updateAnnouncement(id: string, payload: { expected_revision: number; title?: string; body?: string; archived?: boolean }) {
  return csrfRequest<Announcement>(`/announcements/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

type AdminUserPage = { items: AdminUser[]; page: number; page_size: number; total: number };
export function getAdminUsers(filters: { q?: string; role?: string; is_active?: string } = {}) {
  const params = new URLSearchParams(); Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
  return request<AdminUserPage>(`/admin/users${params.toString() ? `?${params.toString()}` : ""}`);
}
export function createAdminUser(payload: { email: string; full_name: string; employee_code: string; job_title?: string; department_role: "EMPLOYEE" | "MANAGER"; department_id?: number }) {
  return csrfRequest<{ user: AdminUser; temporary_password: string }>("/admin/users", { method: "POST", body: JSON.stringify(payload) });
}
export function updateAdminUser(id: string, payload: { expected_revision: number; full_name?: string; employee_code?: string; job_title?: string | null; department_role?: "EMPLOYEE" | "MANAGER"; is_active?: boolean }) {
  return csrfRequest<AdminUser>(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}
export function resetAdminUserPassword(id: string, admin_password: string) {
  return csrfRequest<{ user: AdminUser; temporary_password: string }>(`/admin/users/${id}/reset-password`, { method: "POST", body: JSON.stringify({ admin_password }) });
}
export function getAuditLogs(filters: { action?: string; result?: string } = {}) {
  const params = new URLSearchParams(); Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
  return request<{ items: AuditLog[]; page: number; page_size: number; total: number }>(`/admin/audit-logs${params.toString() ? `?${params.toString()}` : ""}`);
}
