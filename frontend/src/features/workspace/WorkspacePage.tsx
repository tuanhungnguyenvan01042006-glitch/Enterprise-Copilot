import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { Bookmark, createNote, createTask, deleteNote, deleteTask, getBookmarks, getNotes, getTasks, Note, removeBookmark, Task, updateNote, updateTask } from "../../lib/api";

type Tab = "tasks" | "notes" | "bookmarks";
const emptyTask = { title: "", description: "", priority: "NORMAL" as Task["priority"], due_date: "", status: "TODO" as Task["status"] };
const emptyNote = { title: "", content: "" };
const dateText = (value: string | null) => value ? new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(new Date(value)) : "—";

function TaskForm({ task, onSaved, onCancel }: { task?: Task; onSaved: () => void; onCancel: () => void }) {
  const queryClient = useQueryClient();
  const [values, setValues] = useState(task ? { title: task.title, description: task.description ?? "", priority: task.priority, due_date: task.due_date ?? "", status: task.status } : emptyTask);
  const save = useMutation({ mutationFn: () => task ? updateTask(task.id, { ...values, due_date: values.due_date || null, expected_revision: task.revision }) : createTask({ ...values, due_date: values.due_date || null }), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["workspace-tasks"] }); onSaved(); } });
  const set = (key: keyof typeof values, value: string) => setValues((current) => ({ ...current, [key]: value }));
  return <form className="workspace-form" onSubmit={(event: FormEvent) => { event.preventDefault(); save.mutate(); }}><div className="form-row"><label>Tiêu đề<input required maxLength={160} value={values.title} onChange={(event) => set("title", event.target.value)} /></label><label>Hạn hoàn thành<input type="date" value={values.due_date} onChange={(event) => set("due_date", event.target.value)} /></label></div><label>Mô tả<textarea rows={3} maxLength={4000} value={values.description} onChange={(event) => set("description", event.target.value)} /></label><div className="form-row"><label>Ưu tiên<select value={values.priority} onChange={(event) => set("priority", event.target.value)}><option value="LOW">Thấp</option><option value="NORMAL">Bình thường</option><option value="HIGH">Cao</option></select></label>{task && <label>Trạng thái<select value={values.status} onChange={(event) => set("status", event.target.value)}><option value="TODO">Cần làm</option><option value="IN_PROGRESS">Đang làm</option><option value="DONE">Hoàn tất</option><option value="CANCELLED">Đã hủy</option></select></label>}</div>{save.isError && <p className="form-error">{save.error.message}</p>}<div className="button-row"><button type="submit" disabled={save.isPending}>{save.isPending ? "Đang lưu..." : "Lưu"}</button><button type="button" className="button-secondary" onClick={onCancel}>Hủy</button></div></form>;
}

function TaskList() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({ kind: "", status: "", priority: "", q: "" });
  const [editing, setEditing] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const tasks = useQuery({ queryKey: ["workspace-tasks", filters], queryFn: () => getTasks(filters) });
  const remove = useMutation({ mutationFn: (task: Task) => deleteTask(task.id, task.revision), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workspace-tasks"] }) });
  if (tasks.isPending) return <LoadingState />;
  if (tasks.isError) return <ErrorState message={tasks.error.message} />;
  const setFilter = (key: keyof typeof filters, value: string) => setFilters((current) => ({ ...current, [key]: value }));
  return <div className="workspace-panel"><div className="panel-toolbar"><div><h2>Công việc của tôi</h2><p className="muted">Công việc cá nhân và công việc được giao cho bạn.</p></div><button type="button" onClick={() => { setCreating(true); setEditing(null); }}>+ Công việc mới</button></div><div className="filter-row"><input aria-label="Tìm công việc" placeholder="Tìm theo tiêu đề" value={filters.q} onChange={(event) => setFilter("q", event.target.value)} /><select aria-label="Loại công việc" value={filters.kind} onChange={(event) => setFilter("kind", event.target.value)}><option value="">Tất cả loại</option><option value="PERSONAL">Cá nhân</option><option value="ASSIGNED">Được giao</option></select><select aria-label="Trạng thái" value={filters.status} onChange={(event) => setFilter("status", event.target.value)}><option value="">Tất cả trạng thái</option><option value="TODO">Cần làm</option><option value="IN_PROGRESS">Đang làm</option><option value="DONE">Hoàn tất</option><option value="CANCELLED">Đã hủy</option></select><select aria-label="Ưu tiên" value={filters.priority} onChange={(event) => setFilter("priority", event.target.value)}><option value="">Mọi ưu tiên</option><option value="HIGH">Cao</option><option value="NORMAL">Bình thường</option><option value="LOW">Thấp</option></select></div>{creating && <div className="surface compact-form"><TaskForm onSaved={() => setCreating(false)} onCancel={() => setCreating(false)} /></div>}{tasks.data.length === 0 ? <div className="empty-card small-empty"><h2>Chưa có công việc</h2><p>Tạo công việc đầu tiên để bắt đầu theo dõi tiến độ.</p></div> : <div className="task-list">{tasks.data.map((task) => <article className="task-card" key={task.id}>{editing === task.id ? <TaskForm task={task} onSaved={() => setEditing(null)} onCancel={() => setEditing(null)} /> : <><div className="task-card-main"><div><div className="badge-row"><span className="badge">{task.kind === "PERSONAL" ? "Cá nhân" : "Được giao"}</span><span className="badge">{task.status}</span><span className="badge">{task.priority}</span></div><h3>{task.title}</h3>{task.description && <p>{task.description}</p>}</div><div className="task-meta"><span>Hạn: {dateText(task.due_date)}</span><span>Cập nhật: {dateText(task.updated_at)}</span></div></div><div className="task-actions"><button type="button" className="button-secondary" onClick={() => setEditing(task.id)}>{task.kind === "ASSIGNED" ? "Cập nhật trạng thái" : "Sửa"}</button>{task.kind === "PERSONAL" && <button type="button" className="button-danger" disabled={remove.isPending} onClick={() => window.confirm("Xóa công việc này?") && remove.mutate(task)}>Xóa</button>}</div></>}</article>)}</div>}</div>;
}

function NoteForm({ note, onSaved, onCancel }: { note?: Note; onSaved: () => void; onCancel: () => void }) {
  const queryClient = useQueryClient();
  const [values, setValues] = useState(note ? { title: note.title, content: note.content } : emptyNote);
  const save = useMutation({ mutationFn: () => note ? updateNote(note.id, { ...values, expected_revision: note.revision }) : createNote(values), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["workspace-notes"] }); onSaved(); } });
  return <form className="workspace-form" onSubmit={(event) => { event.preventDefault(); save.mutate(); }}><label>Tiêu đề<input required maxLength={160} value={values.title} onChange={(event) => setValues({ ...values, title: event.target.value })} /></label><label>Nội dung<textarea rows={8} maxLength={20000} value={values.content} onChange={(event) => setValues({ ...values, content: event.target.value })} /></label>{save.isError && <p className="form-error">{save.error.message}</p>}<div className="button-row"><button type="submit" disabled={save.isPending}>{save.isPending ? "Đang lưu..." : "Lưu ghi chú"}</button><button type="button" className="button-secondary" onClick={onCancel}>Hủy</button></div></form>;
}

function NoteList() {
  const queryClient = useQueryClient();
  const [q, setQ] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const notes = useQuery({ queryKey: ["workspace-notes", q], queryFn: () => getNotes(q) });
  const remove = useMutation({ mutationFn: (note: Note) => deleteNote(note.id, note.revision), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workspace-notes"] }) });
  if (notes.isPending) return <LoadingState />;
  if (notes.isError) return <ErrorState message={notes.error.message} />;
  return <div className="workspace-panel"><div className="panel-toolbar"><div><h2>Ghi chú riêng tư</h2><p className="muted">Chỉ bạn có thể xem nội dung ghi chú này.</p></div><button type="button" onClick={() => { setCreating(true); setEditing(null); }}>+ Ghi chú mới</button></div><div className="filter-row"><input aria-label="Tìm ghi chú" placeholder="Tìm theo tiêu đề" value={q} onChange={(event) => setQ(event.target.value)} /></div>{creating && <div className="surface compact-form"><NoteForm onSaved={() => setCreating(false)} onCancel={() => setCreating(false)} /></div>}{notes.data.length === 0 ? <div className="empty-card small-empty"><h2>Chưa có ghi chú</h2><p>Lưu nhanh những điều bạn muốn ghi nhớ.</p></div> : <div className="note-list">{notes.data.map((note) => <article className="note-card" key={note.id}>{editing === note.id ? <NoteForm note={note} onSaved={() => setEditing(null)} onCancel={() => setEditing(null)} /> : <><h3>{note.title}</h3><p className="note-content">{note.content}</p><div className="task-actions"><span className="muted">Cập nhật {dateText(note.updated_at)}</span><button type="button" className="button-secondary" onClick={() => setEditing(note.id)}>Sửa</button><button type="button" className="button-danger" disabled={remove.isPending} onClick={() => window.confirm("Xóa ghi chú này?") && remove.mutate(note)}>Xóa</button></div></>}</article>)}</div>}</div>;
}

function BookmarkList() {
  const queryClient = useQueryClient();
  const bookmarks = useQuery({ queryKey: ["workspace-bookmarks"], queryFn: getBookmarks });
  const remove = useMutation({ mutationFn: removeBookmark, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workspace-bookmarks"] }) });
  if (bookmarks.isPending) return <LoadingState />;
  if (bookmarks.isError) return <ErrorState message={bookmarks.error.message} />;
  return <div className="workspace-panel"><div className="panel-toolbar"><div><h2>Tài liệu đã lưu</h2><p className="muted">Chỉ tài liệu bạn còn quyền đọc được hiển thị.</p></div></div>{bookmarks.data.length === 0 ? <div className="empty-card small-empty"><h2>Chưa có tài liệu đã lưu</h2><p>Bookmark tài liệu từ Kho kiến thức sẽ xuất hiện ở đây.</p></div> : <div className="bookmark-list">{bookmarks.data.map((bookmark: Bookmark) => <article className="bookmark-card" key={bookmark.document_id}><div><span className="badge">{bookmark.category}</span><h3>{bookmark.title}</h3><p className="muted">Cập nhật {dateText(bookmark.updated_at)}</p></div><button type="button" className="button-secondary" onClick={() => remove.mutate(bookmark.document_id)}>Bỏ lưu</button></article>)}</div>}</div>;
}

export function WorkspacePage() {
  const [active, setActive] = useState<Tab>("tasks");
  return <section className="page-stack" aria-labelledby="workspace-title"><div className="page-heading"><p className="eyebrow">KHÔNG GIAN CÁ NHÂN</p><h1 id="workspace-title">Công việc và ghi chú</h1><p className="muted">Tổ chức việc cần làm và lưu lại những điều quan trọng trong ngày.</p></div><div className="workspace-tabs" role="tablist">{([["tasks", "Công việc"], ["notes", "Ghi chú"], ["bookmarks", "Tài liệu đã lưu"]] as const).map(([key, label]) => <button key={key} type="button" role="tab" aria-selected={active === key} className={active === key ? "tab active" : "tab"} onClick={() => setActive(key)}>{label}</button>)}</div>{active === "tasks" && <TaskList />}{active === "notes" && <NoteList />}{active === "bookmarks" && <BookmarkList />}</section>;
}
