import { afterEach, describe, expect, it, vi } from "vitest";

import { clearAuthState, request } from "./api";

afterEach(() => {
  clearAuthState();
  vi.unstubAllGlobals();
});

describe("API security transport", () => {
  it("sends authenticated requests with credentials and JSON content type", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(request<{ ok: boolean }>("/health")).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/health", expect.objectContaining({
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    }));
  });

  it("clears auth state and emits a session-expired event on 401", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { message: "expired" } }), { status: 401 })));
    const expired = vi.fn();
    window.addEventListener("auth:session-expired", expired);

    await expect(request("/private")).rejects.toMatchObject({ status: 401, message: "expired" });
    expect(expired).toHaveBeenCalledTimes(1);
    window.removeEventListener("auth:session-expired", expired);
  });
});
