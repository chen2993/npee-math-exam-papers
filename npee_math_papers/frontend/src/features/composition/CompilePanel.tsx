/**
 * Compile progress panel.
 *
 * Typesetting a full paper set is a long job, so instead of a spinner the user
 * gets: the current phase, elapsed time, the job id (useful when reporting a
 * problem), the produced artifacts with download buttons, and any error text.
 */

import { AlertCircle, CheckCircle2, Download, LoaderCircle, X } from "lucide-react";

import type { CompilePhase } from "../../application/composition/useCompileFlow";
import type { CompileJob } from "../../domain/catalog/models";
import { Button, IconButton, classNames } from "../../shared/ui";

const PHASE_LABEL: Record<CompilePhase, string> = {
  idle: "尚未编译",
  submitting: "正在提交任务",
  running: "正在排版",
  succeeded: "编译完成",
  failed: "编译失败",
};

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds} 秒`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes} 分 ${String(seconds % 60).padStart(2, "0")} 秒`;
}

export function CompilePanel({
  phase,
  job,
  error,
  elapsedSeconds,
  onDownload,
  onDismiss,
}: {
  phase: CompilePhase;
  job: CompileJob | null;
  error: string;
  elapsedSeconds: number;
  onDownload: (index: number) => void;
  onDismiss: () => void;
}) {
  if (phase === "idle" && !job) return null;

  const busy = phase === "submitting" || phase === "running";
  const ok = phase === "succeeded";

  return (
    <section className={classNames("compile-panel surface", ok && "is-ok", phase === "failed" && "is-error")}>
      {/*
        A long typeset run finishes while the user is looking elsewhere, so the
        outcome is announced rather than only drawn. `polite` waits for a pause;
        the visible panel is unchanged.
      */}
      <p className="visually-hidden" role="status" aria-live="polite">
        {ok
          ? `编译完成，生成 ${job?.artifacts.length ?? 0} 份 PDF。`
          : phase === "failed"
            ? `编译失败：${error || "未知原因"}`
            : ""}
      </p>
      <header className="compile-panel-head">
        <span className="compile-panel-icon">
          {busy ? <LoaderCircle size={18} className="is-spinning" /> : ok ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
        </span>
        <div className="compile-panel-title">
          <strong>{PHASE_LABEL[phase]}</strong>
          <small>
            {busy && elapsedSeconds > 0 ? `已用 ${formatElapsed(elapsedSeconds)}` : null}
            {phase === "submitting" ? "正在排队…" : null}
            {job ? `任务 ${job.job_id}` : null}
            {job?.composition_id ? ` · ${job.composition_id}` : null}
          </small>
        </div>
        {!busy ? (
          <IconButton label="关闭" size="sm" onClick={onDismiss}>
            <X size={14} />
          </IconButton>
        ) : null}
      </header>

      {busy ? (
        <div className="compile-progress" role="progressbar" aria-label="编译进度">
          <span className="compile-progress-bar" />
        </div>
      ) : null}

      {busy ? (
        <p className="compile-hint">编译在服务端后台执行，可以离开此页面；完成后可在下方下载。</p>
      ) : null}

      {phase === "failed" && error ? <p className="compile-error">{error}</p> : null}

      {ok && job && job.artifacts.length > 0 ? (
        <ul className="compile-artifacts">
          {job.artifacts.map((artifact, index) => (
            <li key={artifact}>
              <span className="compile-artifact-name" title={artifact}>
                {artifact.split("/").pop()}
              </span>
              <Button size="sm" icon={<Download size={13} />} onClick={() => onDownload(index)}>
                下载
              </Button>
            </li>
          ))}
        </ul>
      ) : null}

      {ok && job && job.artifacts.length === 0 ? <p className="compile-hint">编译完成，但本次没有产物文件。</p> : null}
    </section>
  );
}
