import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { addBookmark, downloadDocumentFile, getDocument, previewDocumentFile, uploadDocumentFile } from "../../lib/api";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";

export function DocumentDetailPage({ admin = false }: { admin?: boolean }) {
  const { documentId = "" } = useParams();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const client = useQueryClient();
  const document = useQuery({ queryKey: ["document", documentId], queryFn: () => getDocument(documentId), enabled: Boolean(documentId) });
  const bookmark = useMutation({ mutationFn: () => addBookmark(documentId) });
  const upload = useMutation({
    mutationFn: () => uploadDocumentFile(documentId, document.data!.revision, file!),
    onSuccess: () => {
      setFile(null);
      client.invalidateQueries({ queryKey: ["document", documentId] });
    },
  });

  if (document.isPending) return <LoadingState />;
  if (document.isError) return <ErrorState message={document.error.message} />;

  const item = document.data;
  const currentFile = item.file;
  const download = async (filename: string) => {
    const blob = await downloadDocumentFile(item.id);
    const url = URL.createObjectURL(blob);
    const anchor = window.document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  };
  const previewFile = async () => setPreview(await previewDocumentFile(item.id));

  return (
    <section className="page-stack" aria-labelledby="document-title">
      <Link to={admin ? "/admin/documents" : "/app/knowledge"}>← Quay lại thư viện</Link>
      <div className="page-heading">
        <div className="badge-row"><span className="badge">{item.category}</span><span className="badge">{item.knowledge_scope}</span></div>
        <h1 id="document-title">{item.title}</h1>
        <p className="muted">{item.description || "Không có mô tả."}</p>
      </div>
      <div className="surface document-detail">
        <dl className="document-facts">
          <div><dt>Người tạo</dt><dd>{item.creator_name || "—"}</dd></div>
          <div><dt>Cập nhật</dt><dd>{new Date(item.updated_at).toLocaleString("vi-VN")}</dd></div>
          <div><dt>Revision</dt><dd>{item.revision}</dd></div>
          {currentFile && <div><dt>File hiện tại</dt><dd>{currentFile.original_filename}</dd></div>}
          {currentFile && <div><dt>Dung lượng</dt><dd>{Math.ceil(currentFile.size_bytes / 1024)} KB</dd></div>}
        </dl>
        <div className="button-row">
          {currentFile && <button type="button" onClick={() => download(currentFile.original_filename)}>Tải xuống</button>}
          {currentFile && /\.(md|txt)$/i.test(currentFile.original_filename) && <button type="button" className="button-secondary" onClick={previewFile}>Preview</button>}
          {item.permissions.can_bookmark && <button type="button" className="button-secondary" onClick={() => bookmark.mutate()}>Lưu tài liệu</button>}
        </div>
      </div>
      {item.permissions.can_upload_file && <form className="surface compact-form workspace-form" onSubmit={(event) => { event.preventDefault(); if (file) upload.mutate(); }}>
        <h2>Thay thế file</h2>
        <label>Tệp<input type="file" accept=".pdf,.md,.txt" onChange={(event) => setFile(event.target.files?.[0] ?? null)} required /></label>
        <button disabled={upload.isPending || !file}>{upload.isPending ? "Đang tải..." : "Thay thế file"}</button>
        {upload.isError && <p className="form-error">{upload.error.message}</p>}
      </form>}
      {preview !== null && <pre className="document-preview">{preview}</pre>}
    </section>
  );
}
