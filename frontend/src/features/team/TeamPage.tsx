import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { createDepartmentTask, DepartmentMember, DepartmentTask, getDepartmentMembers, getDepartmentTasks, updateDepartmentTask } from "../../lib/api";

type Tab = "tasks" | "members";
type Filters = { assignee_id: string; status: string; priority: string; overdue: string };
const emptyTask = { title: "", description: "", assignee_id: "", priority: "NORMAL" as DepartmentTask["priority"], due_date: "" };
const dateText = (value: string | null) => value ? new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(new Date(value)) : "—";

function TaskForm({ task, members, onSaved, onCancel }: { task?: DepartmentTask; members: DepartmentMember[]; onSaved: () => void; onCancel: () => void }) {
  const queryClient = useQueryClient();
  const [values, setValues] = useState(task ? { title: task.title, description: task.description ?? "", assignee_id: task.assignee_id, priority: task.priority, due_date: task.due_date ?? "", status: task.status } : { ...emptyTask, status: "TODO" as DepartmentTask["status"] });
  const save = useMutation({
    mutationFn: () => task ? updateDepartmentTask(task.id, { ...values, due_date: values.due_date || null, expected_revision: task.revision }) : createDepartmentTask({ ...values, due_date: values.due_date || null }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["department-tasks"] }); onSaved(); },
  });
  const set = (key: keyof typeof values, value: string) => setValues((current) => ({ ...current, [key]: value }));
  return <form className="workspace-form" onSubmit={(event: FormEvent) => { event.preventDefault(); save.mutate(); }}>
    <div className="form-row"><label>Tiêu đề<input required maxLength={160} value={values.title} onChange={(event) => set("title", event.target.value)} /></label><label>Hạn hoàn thành<input type="date" value={values.due_date} onChange={(event) => set("due_date", event.target.value)} /></label></div>
    <label>Mô tả<textarea rows={3} maxLength={4000} value={values.description} onChange={(event) => set("description", event.target.value)} /></label>
    <div className="form-row"><label>Người nhận<select required value={values.assignee_id} onChange={(event) => set("assignee_id", event.target.value)}><option value="">Chọn nhân viên</option>{members.filter((member) => member.department_role === "EMPLOYEE" && (member.is_active || member.id === values.assignee_id)).map((member) => <option key={member.id} value={member.id}>{member.full_name} · {member.employee_code}{member.is_active ? "" : " (đã khóa)"}</option>)}</select></label><label>Ưu tiên<select value={values.priority} onChange={(event) => set("priority", event.target.value)}><option value="LOW">Thấp</option><option value="NORMAL">Bình thường</option><option value="HIGH">Cao</option></select></label>{task && <label>Trạng thái<select value={values.status} onChange={(event) => set("status", event.target.value)}><option value="TODO">Cần làm</option><option value="IN_PROGRESS">Đang làm</option><option value="DONE">Hoàn tất</option><option value="CANCELLED">Đã hủy</option></select></label>}</div>
    {save.isError && <p className="form-error">{save.error.message}</p>}<div className="button-row"><button type="submit" disabled={save.isPending}>{save.isPending ? "Đang lưu..." : "Lưu"}</button><button type="button" className="button-secondary" onClick={onCancel}>Hủy</button></div>
  </form>;
}

function DepartmentTasks({ members }: { members: DepartmentMember[] }) {
  const [filters, setFilters] = useState<Filters>({ assignee_id: "", status: "", priority: "", overdue: "" });
  const [editing, setEditing] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const tasks = useQuery({ queryKey: ["department-tasks", filters], queryFn: () => getDepartmentTasks(filters) });
  const setFilter = (key: keyof Filters, value: string) => setFilters((current) => ({ ...current, [key]: value }));
  if (tasks.isPending) return <LoadingState />;
  if (tasks.isError) return <ErrorState message={tasks.error.message} />;
  const taskItems = tasks.data.items ?? [];
  return <div className="workspace-panel"><div className="panel-toolbar"><div><h2>Công việc phòng ban</h2><p className="muted">Chỉ hiển thị công việc được giao trong phòng ban.</p></div><button type="button" onClick={() => { setCreating(true); setEditing(null); }}>+ Giao việc</button></div>
    <div className="filter-row"><select aria-label="Người nhận" value={filters.assignee_id} onChange={(event) => setFilter("assignee_id", event.target.value)}><option value="">Tất cả nhân viên</option>{members.map((member) => <option key={member.id} value={member.id}>{member.full_name}</option>)}</select><select aria-label="Trạng thái" value={filters.status} onChange={(event) => setFilter("status", event.target.value)}><option value="">Tất cả trạng thái</option><option value="TODO">Cần làm</option><option value="IN_PROGRESS">Đang làm</option><option value="DONE">Hoàn tất</option><option value="CANCELLED">Đã hủy</option></select><select aria-label="Ưu tiên" value={filters.priority} onChange={(event) => setFilter("priority", event.target.value)}><option value="">Mọi ưu tiên</option><option value="HIGH">Cao</option><option value="NORMAL">Bình thường</option><option value="LOW">Thấp</option></select><select aria-label="Quá hạn" value={filters.overdue} onChange={(event) => setFilter("overdue", event.target.value)}><option value="">Mọi hạn</option><option value="true">Quá hạn</option><option value="false">Chưa quá hạn</option></select></div>
    {creating && <div className="surface compact-form"><TaskForm members={members} onSaved={() => setCreating(false)} onCancel={() => setCreating(false)} /></div>}
    {taskItems.length === 0 ? <div className="empty-card small-empty"><h2>Chưa có công việc được giao</h2><p>Tạo nhiệm vụ đầu tiên cho một nhân viên đang hoạt động.</p></div> : <div className="task-list">{taskItems.map((task) => <article className="task-card" key={task.id}>{editing === task.id ? <TaskForm task={task} members={members} onSaved={() => setEditing(null)} onCancel={() => setEditing(null)} /> : <><div className="task-card-main"><div><div className="badge-row"><span className="badge">{task.assignee.full_name}</span><span className="badge">{task.status}</span><span className="badge">{task.priority}</span></div><h3>{task.title}</h3>{task.description && <p>{task.description}</p>}</div><div className="task-meta"><span>Hạn: {dateText(task.due_date)}</span><span>Người giao: {task.creator.full_name}</span><span>Cập nhật: {dateText(task.updated_at)}</span></div></div><div className="task-actions"><button type="button" className="button-secondary" onClick={() => setEditing(task.id)}>Sửa / đổi người nhận</button>{task.due_date && task.status !== "DONE" && task.status !== "CANCELLED" && new Date(`${task.due_date}T23:59:59`) < new Date() && <span className="badge badge-overdue">Quá hạn</span>}</div></>}</article>)}</div>}
    <p className="muted">{tasks.data.total ?? 0} công việc · Trang {tasks.data.page ?? 1}</p>
  </div>;
}

function Members({ members }: { members: DepartmentMember[] }) {
  return <div className="workspace-panel"><div className="panel-toolbar"><div><h2>Thành viên phòng ban</h2><p className="muted">Thông tin công việc tối thiểu, không bao gồm dữ liệu riêng tư.</p></div></div>{members.length === 0 ? <div className="empty-card small-empty"><h2>Chưa có thành viên</h2></div> : <div className="member-list">{members.map((member) => <article className="member-card" key={member.id}><div><h3>{member.full_name}</h3><p className="muted">{member.email} · {member.employee_code}</p></div><div className="task-meta"><span>{member.job_title ?? "Chưa cập nhật chức danh"}</span><span>{member.department_role}</span><span className={member.is_active ? "member-active" : "member-inactive"}>{member.is_active ? "Đang hoạt động" : "Đã khóa"}</span></div></article>)}</div>}</div>;
}

export function TeamPage() {
  const [active, setActive] = useState<Tab>("tasks");
  const members = useQuery({ queryKey: ["department-members"], queryFn: getDepartmentMembers });
  if (members.isPending) return <section className="page-stack" aria-labelledby="team-title"><div className="page-heading"><p className="eyebrow">PHÒNG BAN</p><h1 id="team-title">Quản lý phòng ban</h1><p className="muted">Điều phối công việc được giao và thành viên trong phòng ban.</p></div><LoadingState /></section>;
  if (members.isError) return <section className="page-stack" aria-labelledby="team-title"><div className="page-heading"><p className="eyebrow">PHÒNG BAN</p><h1 id="team-title">Quản lý phòng ban</h1></div><ErrorState message={members.error.message} /></section>;
  const memberItems = members.data.items ?? [];
  return <section className="page-stack" aria-labelledby="team-title"><div className="page-heading"><p className="eyebrow">PHÒNG BAN</p><h1 id="team-title">Quản lý phòng ban</h1><p className="muted">Điều phối công việc được giao và thành viên trong phòng ban.</p></div><div className="workspace-tabs" role="tablist"><button type="button" role="tab" aria-selected={active === "tasks"} className={active === "tasks" ? "tab active" : "tab"} onClick={() => setActive("tasks")}>Công việc phòng ban</button><button type="button" role="tab" aria-selected={active === "members"} className={active === "members" ? "tab active" : "tab"} onClick={() => setActive("members")}>Thành viên</button></div>{active === "tasks" ? <DepartmentTasks members={memberItems} /> : <Members members={memberItems} />}</section>;
}
