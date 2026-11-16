import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ChatPage } from "./ChatPage";
import * as api from "../../lib/api";

vi.mock("../../lib/api", () => ({
  getChatConversations: vi.fn(),
  getChatConversation: vi.fn(),
  createChatConversation: vi.fn(),
  deleteChatConversation: vi.fn(),
  sendChatMessage: vi.fn(),
}));

const item = { id: "chat-1", title: "Hội thoại", created_at: "2026-01-01", updated_at: "2026-01-01" };
const source = { number: 1, document_id: "doc-1", title: "Chính sách", section_path: "Nghỉ phép" };

beforeEach(() => {
  vi.mocked(api.getChatConversations).mockResolvedValue([item]);
  vi.mocked(api.getChatConversation).mockResolvedValue({ ...item, messages: [] });
});
afterEach(() => { cleanup(); vi.resetAllMocks(); });

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter><ChatPage /></MemoryRouter></QueryClientProvider>);
}

it("opens saved history and renders source links", async () => {
  vi.mocked(api.getChatConversation).mockResolvedValue({ ...item, messages: [{ id: "m1", role: "assistant", content: "Trả lời [1]", sources: [source], created_at: item.created_at }] });
  renderPage();
  await userEvent.click(await screen.findByRole("button", { name: "Hội thoại" }));
  expect(await screen.findByText("Trả lời [1]")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Chính sách" })).toHaveAttribute("href", "/app/knowledge/doc-1");
});

it("keeps a failed question for retry and shows the waiting state", async () => {
  let rejectRequest!: (error: Error) => void;
  vi.mocked(api.sendChatMessage).mockImplementation(() => new Promise((_, reject) => { rejectRequest = reject; }));
  renderPage();
  await userEvent.click(await screen.findByRole("button", { name: "Hội thoại" }));
  await userEvent.type(await screen.findByLabelText("Câu hỏi"), "Nghỉ phép?");
  await userEvent.click(screen.getByRole("button", { name: "Gửi câu hỏi" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Đang tìm kiếm");
  expect(screen.getByRole("button", { name: "Đang xử lý..." })).toBeDisabled();
  rejectRequest(new Error("Dịch vụ không khả dụng"));
  expect(await screen.findByRole("alert")).toHaveTextContent("Dịch vụ không khả dụng");
  expect(screen.getByLabelText("Câu hỏi")).toHaveValue("Nghỉ phép?");
  await waitFor(() => expect(screen.getByRole("button", { name: "Gửi câu hỏi" })).toBeEnabled());
});

it("creates and selects a conversation", async () => {
  vi.mocked(api.createChatConversation).mockResolvedValue(item);
  renderPage();
  await userEvent.click(await screen.findByRole("button", { name: "+ Hội thoại mới" }));
  expect(await screen.findByLabelText("Câu hỏi")).toBeInTheDocument();
  expect(api.createChatConversation).toHaveBeenCalledOnce();
});

it("sends a question and reloads the saved response", async () => {
  const answer = { id: "m2", role: "assistant" as const, content: "Đã trả lời", sources: [], created_at: item.created_at };
  const question = { id: "m1", role: "user" as const, content: "Câu hỏi", sources: [], created_at: item.created_at };
  vi.mocked(api.sendChatMessage).mockImplementation(async () => {
    vi.mocked(api.getChatConversation).mockResolvedValue({ ...item, messages: [question, answer] });
    return { user_message: question, assistant_message: answer };
  });
  renderPage();
  await userEvent.click(await screen.findByRole("button", { name: "Hội thoại" }));
  await userEvent.type(await screen.findByLabelText("Câu hỏi"), "Câu hỏi");
  await userEvent.click(screen.getByRole("button", { name: "Gửi câu hỏi" }));
  expect(await screen.findByText("Đã trả lời")).toBeInTheDocument();
  expect(screen.getByLabelText("Câu hỏi")).toHaveValue("");
  expect(api.sendChatMessage).toHaveBeenCalledWith("chat-1", "Câu hỏi");
});

it("deletes a conversation after confirmation", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  vi.mocked(api.deleteChatConversation).mockResolvedValue(undefined);
  renderPage();
  await userEvent.click(await screen.findByRole("button", { name: "Xóa Hội thoại" }));
  await waitFor(() => expect(vi.mocked(api.deleteChatConversation).mock.calls[0]?.[0]).toBe("chat-1"));
  vi.restoreAllMocks();
});
