import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { Announcement, createAnnouncement, getAnnouncements, updateAnnouncement } from "../../lib/api";

function AnnouncementForm({ item, onDone }: { item?: Announcement; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(item?.title ?? "");
  const [body, setBody] = useState(item?.body ?? "");
  const save = useMutation({
    mutationFn: () => item ? updateAnnouncement(item.id, { expected_revision: item.revision, title, body }) : createAnnouncement({ title, body }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["announcements"] }); onDone(); },
  });
  return <form className="workspace-form compact-form surface" onSubmit={(event: FormEvent) => { event.preventDefault(); save.mutate(); }}><label>Tiêu đề<input required maxLength={160} value={title} onChange={(event) => setTitle(event.target.value)} /></label><label>Nội dung<textarea required rows={6} maxLength={6000} value={body} onChange={(event) => setBody(event.target.value)} /></label>{save.isError && <p className="form-error">{save.error.message}</p>}<div className="button-row"><button type="submit" disabled={save.isPending}>{save.isPending ? "Đang lưu..." : "Lưu thông báo"}</button><button type="button" className="button-secondary" onClick={onDone}>Hủy</button></div></form>;
}

export function AnnouncementsPage({ admin = false }: { admin?: boolean }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<Announcement | null>(null);
  const [creating, setCreating] = useState(false);
  const announcements = useQuery({ queryKey: ["announcements", admin], queryFn: () => getAnnouncements(true) });
  const toggle = useMutation({ mutationFn: (item: Announcement) => updateAnnouncement(item.id, { expected_revision: item.revision, archived: !item.archived_at }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["announcements"] }) });
  if (announcements.isPending) return <LoadingState />;
  if (announcements.isError) return <ErrorState message={announcements.error.message} />;
  return <section className="page-stack" aria-labelledby="announcements-title"><div className="page-heading"><p className="eyebrow">VẬN HÀNH</p><h1 id="announcements-title">Thông báo</h1><p className="muted">Chia sẻ các cập nhật quan trọng với phòng ban.</p></div><div className="panel-toolbar"><div /><button type="button" onClick={() => { setCreating(true); setEditing(null); }}>+ Thông báo mới</button></div>{creating && <AnnouncementForm onDone={() => setCreating(false)} />}{editing && <AnnouncementForm item={editing} onDone={() => setEditing(null)} />}{announcements.data.length === 0 ? <div className="empty-card small-empty"><h2>Chưa có thông báo</h2><p>Tạo thông báo đầu tiên cho phòng ban.</p></div> : <div className="announcement-list">{announcements.data.map((item) => <article className={item.archived_at ? "announcement-card archived" : "announcement-card"} key={item.id}><div className="badge-row"><span className="badge">{item.archived_at ? "Đã lưu trữ" : "Đang hoạt động"}</span><small className="muted">{new Date(item.updated_at).toLocaleString("vi-VN")}</small></div><h2>{item.title}</h2><p>{item.body}</p><div className="button-row"><button type="button" className="button-secondary" onClick={() => { setEditing(item); setCreating(false); }}>Sửa</button><button type="button" className="button-secondary" disabled={toggle.isPending} onClick={() => toggle.mutate(item)}>{item.archived_at ? "Khôi phục" : "Lưu trữ"}</button></div></article>)}</div>}</section>;
}
