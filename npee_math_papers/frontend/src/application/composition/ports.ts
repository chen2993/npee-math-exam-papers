import type { CompileJob } from "../../domain/catalog/models";
import type { CompositionDownload, CompositionDraft } from "../../domain/composition/models";

/**
 * 服务端组卷包（``composition/<id>/composition.json``）。
 *
 * 浏览器的草稿存在 localStorage 里，只属于当前这台机器；组卷包是仓库里的真实
 * 文件。把两者都放在同一个界面里，才能"打开线下的正式组卷、改完存回去"。
 */
export interface CompositionPackageSummary {
  composition_id: string;
  title: string;
  group_count: number;
  reference_count: number;
  paper_count: number;
  subjects: string[];
  target_count: number;
  layout?: string | null;
  theme?: string | null;
  spacing?: string | null;
  has_cover: boolean;
}

export interface CompositionPackageDocument {
  composition_id: string;
  path: string;
  composition: Record<string, unknown>;
  validation: { ok: boolean };
}

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
  /** 列出仓库里的组卷包。 */
  packages(signal?: AbortSignal): Promise<CompositionPackageSummary[]>;
  /** 读取一个组卷包的完整文档。 */
  openPackage(compositionId: string, signal?: AbortSignal): Promise<CompositionPackageDocument>;
  /** 把组卷文档写回包内（服务端先校验再落盘）。 */
  savePackage(compositionId: string, composition: Record<string, unknown>): Promise<CompositionPackageDocument>;
}
