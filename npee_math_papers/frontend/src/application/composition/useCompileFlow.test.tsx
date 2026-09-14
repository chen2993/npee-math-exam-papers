import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { CompileJob } from "../../domain/catalog/models";
import { useCompileFlow } from "./useCompileFlow";
import type { CompositionExportGateway } from "./ports";

function job(overrides: Partial<CompileJob> = {}): CompileJob {
  return {
    job_id: "job-1",
    composition_id: "comp-1",
    status: "queued",
    created_at: "2026-01-01T00:00:00Z",
    started_at: "2026-01-01T00:00:00Z",
    finished_at: null,
    artifacts: [],
    error: null,
    report: {},
    ...overrides,
  };
}

function gateway(overrides: Partial<CompositionExportGateway> = {}): CompositionExportGateway {
  return {
    compile: vi.fn(),
    submit: vi.fn(async () => job({ status: "running" })),
    job: vi.fn(async () => job({ status: "running" })),
    jobs: vi.fn(async () => []),
    downloadArtifact: vi.fn(async () => ({ blob: new Blob(["x"]), filename: "a.pdf", format: "pdf" as const })),
    ...overrides,
  } as unknown as CompositionExportGateway;
}

describe("useCompileFlow", () => {
  it("starts idle and exposes no busy state", async () => {
    const { result } = renderHook(() => useCompileFlow(gateway()));
    // The hook refreshes recent jobs on mount; wait for that to settle so the
    // assertion never races the initial fetch.
    await waitFor(() => expect(result.current.history).toEqual([]));
    expect(result.current.phase).toBe("idle");
    expect(result.current.isBusy).toBe(false);
  });

  it("moves through submitting -> running after submit", async () => {
    const api = gateway();
    const { result } = renderHook(() => useCompileFlow(api));
    await act(async () => {
      await result.current.start({ composition_id: "comp-1" }, "comp-1");
    });
    await waitFor(() => expect(result.current.phase).toBe("running"));
    expect(result.current.job?.job_id).toBe("job-1");
    expect(result.current.isBusy).toBe(true);
  });

  it("reaches succeeded when the job finishes", async () => {
    const api = gateway({
      job: vi.fn(async () => job({ status: "succeeded", artifacts: ["build/out/a.pdf"] })),
    });
    const { result } = renderHook(() => useCompileFlow(api));
    await act(async () => {
      await result.current.start({ composition_id: "comp-1" }, "comp-1");
    });
    await waitFor(() => expect(result.current.phase).toBe("succeeded"), { timeout: 4000 });
    expect(result.current.isBusy).toBe(false);
    expect(result.current.job?.artifacts).toEqual(["build/out/a.pdf"]);
  });

  it("reports a failed job with its error", async () => {
    const api = gateway({
      job: vi.fn(async () => job({ status: "failed", error: "XeLaTeX pass 1 failed" })),
    });
    const { result } = renderHook(() => useCompileFlow(api));
    await act(async () => {
      await result.current.start({ composition_id: "comp-1" }, "comp-1");
    });
    await waitFor(() => expect(result.current.phase).toBe("failed"), { timeout: 4000 });
    expect(result.current.error).toContain("XeLaTeX");
  });

  it("surfaces a submit failure without polling", async () => {
    const api = gateway({ submit: vi.fn(async () => { throw new Error("网络错误"); }) });
    const { result } = renderHook(() => useCompileFlow(api));
    await act(async () => {
      await result.current.start({ composition_id: "comp-1" }, "comp-1");
    });
    expect(result.current.phase).toBe("failed");
    expect(result.current.error).toBe("网络错误");
  });

  it("resets back to idle", async () => {
    // Use a job that finishes so polling stops before we reset; otherwise the
    // interval keeps React's async act() open and the test times out.
    const api = gateway({ job: vi.fn(async () => job({ status: "succeeded" })) });
    const { result } = renderHook(() => useCompileFlow(api));
    await act(async () => {
      await result.current.start({ composition_id: "comp-1" }, "comp-1");
    });
    await waitFor(() => expect(result.current.phase).toBe("succeeded"), { timeout: 4000 });
    act(() => result.current.reset());
    expect(result.current.phase).toBe("idle");
    expect(result.current.job).toBeNull();
  });

  it("downloads the tracked job's first artifact by default", async () => {
    const downloadArtifact = vi.fn(async () => ({ blob: new Blob(["x"]), filename: "a.pdf", format: "pdf" as const }));
    const api = gateway({ downloadArtifact, job: vi.fn(async () => job({ status: "succeeded" })) });
    const { result } = renderHook(() => useCompileFlow(api));
    await act(async () => {
      await result.current.start({ composition_id: "comp-1" }, "comp-1");
    });
    await waitFor(() => expect(result.current.job).not.toBeNull(), { timeout: 4000 });
    await act(async () => {
      await result.current.download();
    });
    expect(downloadArtifact).toHaveBeenCalledWith("job-1", 0);
  });

  it("forwards the artifact index so multi-target runs can fetch each file", async () => {
    // A compile with both A3 and A4 targets produces several artifacts; the index
    // is what selects between them. Dropping it silently returned only the first.
    const downloadArtifact = vi.fn(async () => ({ blob: new Blob(["x"]), filename: "b.pdf", format: "pdf" as const }));
    const api = gateway({ downloadArtifact, job: vi.fn(async () => job({ status: "succeeded" })) });
    const { result } = renderHook(() => useCompileFlow(api));
    await act(async () => {
      await result.current.start({ composition_id: "comp-1" }, "comp-1");
    });
    await waitFor(() => expect(result.current.job).not.toBeNull(), { timeout: 4000 });
    await act(async () => {
      await result.current.download(undefined, 2);
    });
    expect(downloadArtifact).toHaveBeenCalledWith("job-1", 2);
  });
});
