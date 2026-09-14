import type { CompileJob } from "../../domain/catalog/models";
import type { CompositionDownload, CompositionDraft } from "../../domain/composition/models";

export interface CompositionDraftRepository {
  load(): CompositionDraft[];
  save(drafts: CompositionDraft[]): void;
}

export interface CompilePayload {
  [key: string]: unknown;
}

export interface CompositionExportGateway {
  compile(payload: CompilePayload): Promise<CompositionDownload>;
  /** 提交后台编译，立即返回任务 ID（长编译不阻塞界面）。 */
  submit(payload: CompilePayload): Promise<CompileJob>;
  /** 轮询某个编译任务。 */
  job(jobId: string, signal?: AbortSignal): Promise<CompileJob>;
  /** 最近编译任务列表。 */
  jobs(limit?: number, signal?: AbortSignal): Promise<CompileJob[]>;
  /** 下载某个已完成任务的产物。 */
  downloadArtifact(jobId: string, index?: number): Promise<CompositionDownload>;
}
