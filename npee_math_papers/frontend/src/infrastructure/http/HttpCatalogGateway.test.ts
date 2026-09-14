import { afterEach, describe, expect, it, vi } from "vitest";

import { HttpCatalogGateway } from "./HttpCatalogGateway";
import { HttpError } from "./HttpError";

const gateway = new HttpCatalogGateway("/api");

afterEach(() => vi.unstubAllGlobals());

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("HttpCatalogGateway", () => {
  it("unwraps the series envelope", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ series: [{ series_key: "demo" }] })));
    await expect(gateway.listSeries()).resolves.toEqual([{ series_key: "demo" }]);
  });

  it("builds repeatable filter query parameters", async () => {
    const fetchMock = vi.fn<(input: RequestInfo | URL) => Promise<Response>>(async () =>
      jsonResponse({ total: 0, offset: 0, count: 0, papers: [] }),
    );
    vi.stubGlobal("fetch", fetchMock);
    await gateway.listPapers({ seriesKeys: ["a", "b"], years: [2024], subjects: ["math1"], offset: 20, limit: 40 });
    const url = String(fetchMock.mock.calls[0]?.[0] ?? "");
    expect(url).toContain("series_key=a&series_key=b");
    expect(url).toContain("year=2024");
    expect(url).toContain("subject=math1");
    expect(url).toContain("offset=20");
    expect(url).toContain("limit=40");
  });

  it("sends the library-wide search and ordering parameters", async () => {
    const fetchMock = vi.fn<(input: RequestInfo | URL) => Promise<Response>>(async () =>
      jsonResponse({ total: 0, offset: 0, count: 0, papers: [] }),
    );
    vi.stubGlobal("fetch", fetchMock);
    await gateway.listPapers({ query: "张宇 2024", order: "year-desc" });
    const url = String(fetchMock.mock.calls[0]?.[0] ?? "");
    // `q` is what makes the box search the whole library rather than the page.
    expect(url).toContain("q=%E5%BC%A0%E5%AE%87+2024");
    expect(url).toContain("order=year-desc");
  });

  it("omits query and order when they are not set", async () => {
    const fetchMock = vi.fn<(input: RequestInfo | URL) => Promise<Response>>(async () =>
      jsonResponse({ total: 0, offset: 0, count: 0, papers: [] }),
    );
    vi.stubGlobal("fetch", fetchMock);
    await gateway.listPapers({ limit: 10 });
    const url = String(fetchMock.mock.calls[0]?.[0] ?? "");
    expect(url).toBe("/api/papers?limit=10");
  });

  it("requests the question-level endpoint", async () => {
    const fetchMock = vi.fn<(input: RequestInfo | URL) => Promise<Response>>(async () =>
      jsonResponse({ natural_key: "2024/math1/demo/1", question: {} }),
    );
    vi.stubGlobal("fetch", fetchMock);
    await gateway.getQuestion("demo", 2024, "math1", 1, 7);
    expect(String(fetchMock.mock.calls[0]?.[0] ?? "")).toBe("/api/papers/demo/2024/math1/1/questions/7");
  });

  it("reads the release manifest", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ library_hash: "abc", paper_count: 1, papers: {} })));
    await expect(gateway.releaseManifest()).resolves.toMatchObject({ library_hash: "abc" });
  });

  it("throws an HttpError carrying the status", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("nope", { status: 404 })));
    await expect(gateway.listSeries()).rejects.toBeInstanceOf(HttpError);
    try {
      await gateway.listSeries();
    } catch (error) {
      expect((error as HttpError).status).toBe(404);
      expect((error as HttpError).isNotFound).toBe(true);
    }
  });

  it("unwraps a FastAPI detail object into the message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: "paper not found" }), { status: 404 })),
    );
    try {
      await gateway.listSeries();
    } catch (error) {
      expect((error as HttpError).detail).toBe("paper not found");
      expect((error as Error).message).toContain("paper not found");
    }
  });
});
