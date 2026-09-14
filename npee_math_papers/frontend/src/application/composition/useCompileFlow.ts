/**
 * The asynchronous compile flow: submit → poll → download.
 *
 * A full paper set takes tens of seconds to several minutes to typeset, so the
 * synchronous endpoint would leave the UI frozen behind a bare spinner. This hook
 * drives the background-job API instead and exposes a plain state machine the UI
 * can render:
 *
 *   idle -> submitting -> running -> succeeded | failed
 *
 * It also keeps recent jobs so a user who navigates away and back can still see
 * the result, and exposes a download action for a finished job.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { CompileJob } from "../../domain/catalog/models";
import type { CompilePayload, CompositionExportGateway } from "./ports";

export type CompilePhase = "idle" | "submitting" | "running" | "succeeded" | "failed";

export interface CompileFlowState {
  phase: CompilePhase;
  job: CompileJob | null;
  error: string;
  /** Seconds since the job started running. */
  elapsedSeconds: number;
  /** Recent jobs, newest first. */
  history: CompileJob[];
  /** The draft id a job belongs to, for scoping the panel. */
  compositionId: string;
}

const POLL_MS = 1500;

export function useCompileFlow(exportGateway: CompositionExportGateway) {
  const [state, setState] = useState<CompileFlowState>({
    phase: "idle",
    job: null,
    error: "",
    elapsedSeconds: 0,
    history: [],
    compositionId: "",
  });
  const jobIdRef = useRef<string | null>(null);

  /** Refresh the recent-jobs list; failures are non-fatal. */
  const refreshHistory = useCallback(async () => {
    try {
      const jobs = await exportGateway.jobs(10);
      setState((current) => ({ ...current, history: jobs }));
    } catch {
      /* history is a convenience, not a requirement */
    }
  }, [exportGateway]);

  useEffect(() => {
    void refreshHistory();
  }, [refreshHistory]);

  /** Submit a payload and begin polling. */
  const start = useCallback(
    async (payload: CompilePayload, compositionId: string) => {
      setState((current) => ({
        ...current,
        phase: "submitting",
        error: "",
        elapsedSeconds: 0,
        compositionId,
      }));
      try {
        const job = await exportGateway.submit(payload);
        jobIdRef.current = job.job_id;
        setState((current) => ({
          ...current,
          phase: job.status === "failed" ? "failed" : "running",
          job,
          error: job.error ?? "",
        }));
      } catch (reason) {
        setState((current) => ({
          ...current,
          phase: "failed",
          error: reason instanceof Error ? reason.message : "提交编译任务失败",
        }));
      }
    },
    [exportGateway],
  );

  // Poll the in-flight job until it reaches a terminal state.
  useEffect(() => {
    if (state.phase !== "running" && state.phase !== "submitting") return undefined;
    const jobId = state.job?.job_id;
    if (!jobId) return undefined;
    let cancelled = false;
    const timer = window.setInterval(() => {
      void (async () => {
        try {
          const job = await exportGateway.job(jobId);
          if (cancelled) return;
          setState((current) => ({
            ...current,
            job,
            error: job.error ?? "",
            phase: job.status === "succeeded" ? "succeeded" : job.status === "failed" ? "failed" : "running",
          }));
          if (job.status === "succeeded" || job.status === "failed") {
            void refreshHistory();
          }
        } catch (reason) {
          if (cancelled) return;
          setState((current) => ({ ...current, phase: "failed", error: reason instanceof Error ? reason.message : "读取编译任务失败" }));
        }
      })();
    }, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [state.phase, state.job?.job_id, exportGateway, refreshHistory]);

  // A 1-second tick powers the elapsed-time readout without re-rendering on data change.
  useEffect(() => {
    if (state.phase !== "running") return undefined;
    const started = state.job?.started_at ? Date.parse(state.job.started_at) : Date.now();
    const timer = window.setInterval(() => {
      setState((current) => ({ ...current, elapsedSeconds: Math.round((Date.now() - started) / 1000) }));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [state.phase, state.job?.started_at]);

  const reset = useCallback(() => {
    jobIdRef.current = null;
    setState((current) => ({ ...current, phase: "idle", job: null, error: "", elapsedSeconds: 0 }));
  }, []);

  /**
   * Download one artifact of a finished job.
   *
   * Defaults to the tracked job and its first artifact. ``index`` selects which
   * artifact to fetch: a multi-target compile produces one file per layout /
   * theme / spacing combination, so "download" has to be per-file or the user
   * silently gets only the first one.
   */
  const download = useCallback(
    async (jobId?: string, index = 0) => {
      const target = jobId ?? state.job?.job_id;
      if (!target) return null;
      return exportGateway.downloadArtifact(target, index);
    },
    [exportGateway, state.job?.job_id],
  );

  return useMemo(
    () => ({
      ...state,
      isBusy: state.phase === "submitting" || state.phase === "running",
      start,
      reset,
      download,
      refreshHistory,
    }),
    [state, start, reset, download, refreshHistory],
  );
}
