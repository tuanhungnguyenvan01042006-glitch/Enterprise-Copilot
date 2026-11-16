import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { createChatConversation, deleteChatConversation, getChatConversation, getChatConversations, sendChatMessage } from "../../lib/api";

export function ChatPage() {
  const client = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const conversations = useQuery({ queryKey: ["chat-conversations"], queryFn: getChatConversations });
  const conversation = useQuery({ queryKey: ["chat-conversation", selected], queryFn: () => getChatConversation(selected!), enabled: !!selected });
  const create = useMutation({ mutationFn: createChatConversation, onSuccess: (item) => { setSelected(item.id); setQuestion(""); void client.invalidateQueries({ queryKey: ["chat-conversations"] }); } });
  const remove = useMutation({ mutationFn: deleteChatConversation, onSuccess: (_, id) => { if (selected === id) { setSelected(null); setQuestion(""); } client.removeQueries({ queryKey: ["chat-conversation", id] }); void client.invalidateQueries({ queryKey: ["chat-conversations"] }); } });
  const send = useMutation({ mutationFn: ({ id, content }: { id: string; content: string }) => sendChatMessage(id, content), onSuccess: (_, variables) => { setQuestion(""); void client.invalidateQueries({ queryKey: ["chat-conversation", variables.id] }); void client.invalidateQueries({ queryKey: ["chat-conversations"] }); } });
  const busy = create.isPending || remove.isPending || send.isPending;
  function submit(event: FormEvent) { event.preventDefault(); if (selected && question.trim() && !busy) send.mutate({ id: selected, content: question.trim() }); }
  return <section className="page-stack chat-page" aria-labelledby="chat-title">
    <div className="page-heading"><p className="eyebrow">TRỢ LÝ KIẾN THỨC</p><h1 id="chat-title">Chatbot</h1><p className="muted">Đặt câu hỏi về tài liệu công ty. Mỗi câu hỏi được xử lý độc lập, hãy cung cấp đầy đủ ngữ cảnh.</p></div>
    <div className="chat-layout">
      <aside className="surface chat-sidebar" aria-label="Cuộc hội thoại">
        <div className="chat-sidebar-header"><h2>Hội thoại</h2><button type="button" disabled={busy} onClick={() => create.mutate()}>+ Hội thoại mới</button></div>
        {create.isError && <p role="alert" className="form-error">{create.error.message}</p>}{remove.isError && <p role="alert" className="form-error">{remove.error.message}</p>}
        {conversations.isPending ? <LoadingState label="Đang tải hội thoại..." /> : conversations.isError ? <ErrorState message={conversations.error.message} onRetry={() => void conversations.refetch()} /> : conversations.data.length === 0 ? <p className="muted">Chưa có hội thoại nào.</p> : <ul className="chat-conversation-list">{conversations.data.map((item) => <li key={item.id} className={selected === item.id ? "chat-conversation selected" : "chat-conversation"}><button type="button" className="chat-select" disabled={busy} aria-current={selected === item.id ? "true" : undefined} onClick={() => { setSelected(item.id); setQuestion(""); send.reset(); }}>{item.title}</button><button type="button" className="chat-delete" disabled={busy} aria-label={`Xóa ${item.title}`} onClick={() => { if (window.confirm("Xóa cuộc hội thoại này?")) remove.mutate(item.id); }}>×</button></li>)}</ul>}
      </aside>
      <div className="surface chat-main">
        {!selected ? <div className="chat-empty"><h2>Bắt đầu cuộc hội thoại</h2><p className="muted">Tạo hoặc chọn hội thoại để đặt câu hỏi.</p></div> : conversation.isPending ? <LoadingState label="Đang tải tin nhắn..." /> : conversation.isError ? <ErrorState message={conversation.error.message} onRetry={() => void conversation.refetch()} /> : <>
          <div className="chat-messages" aria-live="polite" aria-label="Tin nhắn">
            {conversation.data.messages.length === 0 && <p className="muted">Hãy đặt câu hỏi đầu tiên của bạn.</p>}
            {conversation.data.messages.map((message) => <article key={message.id} className={`chat-message chat-message-${message.role}`}><strong>{message.role === "user" ? "Bạn" : "Chatbot"}</strong><p>{message.content}</p>{message.sources.length > 0 && <div className="chat-sources"><strong>Nguồn tham khảo</strong><ul>{message.sources.map((source) => <li key={source.number}>[{source.number}] {source.document_id ? <Link to={`/app/knowledge/${encodeURIComponent(source.document_id)}`}>{source.title || "Tài liệu"}</Link> : (source.title || "Tài liệu")}{source.section_path && <> — {Array.isArray(source.section_path) ? source.section_path.join(" > ") : source.section_path}</>}</li>)}</ul></div>}</article>)}
            {send.isPending && <p role="status" className="muted">Đang tìm kiếm và tạo câu trả lời...</p>}
          </div>
          <form className="chat-form" onSubmit={submit}><label htmlFor="chat-question">Câu hỏi</label><textarea id="chat-question" rows={3} maxLength={4000} value={question} disabled={busy} onChange={(event) => setQuestion(event.target.value)} placeholder="Nhập câu hỏi về tài liệu công ty..." />{send.isError && <p role="alert" className="form-error">{send.error.message} Bạn có thể gửi lại câu hỏi.</p>}<div className="chat-form-actions"><span className="muted">{question.length}/4000</span><button type="submit" disabled={busy || !question.trim()}>{send.isPending ? "Đang xử lý..." : "Gửi câu hỏi"}</button></div></form>
        </>}
      </div>
    </div>
  </section>;
}
