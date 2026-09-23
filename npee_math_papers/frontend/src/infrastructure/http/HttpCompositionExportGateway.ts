import type {
  CompilePayload,
  CompositionExportGateway,
  CompositionPackageDocument,
  CompositionPackageSummary,
} from "../../application/composition/ports";
import type { CompileJob } from "../../domain/catalog/models";
import type { CompositionDownload } from "../../domain/composition/models";
import { readError } from "./HttpError";
import { resolveApiBaseUrl } from "./apiBaseUrl";

export class HttpCompositionExportGateway implements CompositionExportGateway {
  constructor(private readonly apiBaseUrl: string = resolveApiBaseUrl()) {}

  async compile(payload: CompilePayload): Promise<CompositionDownload> {
    const response = await fetch(`${this.apiBaseUrl}/compositions/compile`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/pdf, application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw await readError(response, "组卷编译失败");
    }
    const contentType = response.headers.get("Content-Type") || "";
    if (contentType.includes("application/json")) {
      // 试编译（dry-run）返回报告而不是文件。
      const report = await response.json();
      const artifacts = (report.artifacts || []) as string[];
      throw new Error(`已生成 TeX（dry-run）。产物：${artifacts.join(", ") || "见 build 目录"}`);
    }
    const compositionId = String(payload.composition_id || "composition");
    return {
      blob: await response.blob(),
      filename: this.filename(response.headers.get("Content-Disposition"), `${compositionId}.pdf`),
      format: contentType.includes("zip") ? "zip" : "pdf",
    };
  }

  async submit(payload: CompilePayload): Promise<CompileJob> {
    const response = await fetch(`${this.apiBaseUrl}/compositions/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw await readError(response, "提交编译任务失败");
    return (await response.json()) as CompileJob;
  }

  async job(jobId: string, signal?: AbortSignal): Promise<CompileJob> {
    const response = await fetch(`${this.apiBaseUrl}/compositions/jobs/${encodeURIComponent(jobId)}`, {
      cache: "no-store",
      signal,
    });
    if (!response.ok) throw await readError(response, "读取编译任务失败");
    return (await response.json()) as CompileJob;
  }

  async jobs(limit = 20, signal?: AbortSignal): Promise<CompileJob[]> {
    const response = await fetch(`${this.apiBaseUrl}/compositions/jobs?limit=${limit}`, { cache: "no-store", signal });
    if (!response.ok) throw await readError(response, "读取编译任务列表失败");
    const payload = (await response.json()) as { jobs?: CompileJob[] };
    return payload.jobs ?? [];
  }

  async downloadArtifact(jobId: string, index = 0): Promise<CompositionDownload> {
    const response = await fetch(
      `${this.apiBaseUrl}/compositions/jobs/${encodeURIComponent(jobId)}/artifact?index=${index}`,
      { cache: "no-store" },
    );
    if (!response.ok) throw await readError(response, "下载编译产物失败");
    const contentType = response.headers.get("Content-Type") || "";
    return {
      blob: await response.blob(),
      filename: this.filename(response.headers.get("Content-Disposition"), `${jobId}.pdf`),
      format: contentType.includes("zip") ? "zip" : "pdf",
    };
  }

  async packages(signal?: AbortSignal): Promise<CompositionPackageSummary[]> {
    const response = await fetch(`${this.apiBaseUrl}/compositions/packages`, { cache: "no-store", signal });
    if (!response.ok) throw await readError(response, "读取组卷包列表失败");
    const payload = (await response.json()) as { packages?: CompositionPackageSummary[] };
    return payload.packages ?? [];
  }

  async openPackage(compositionId: string, signal?: AbortSignal): Promise<CompositionPackageDocument> {
    const response = await fetch(`${this.apiBaseUrl}/compositions/packages/${encodeURIComponent(compositionId)}`, {
      cache: "no-store",
      signal,
    });
    if (!response.ok) throw await readError(response, "读取组卷包失败");
    return (await response.json()) as CompositionPackageDocument;
  }

  async savePackage(
    compositionId: string,
    composition: Record<string, unknown>,
  ): Promise<CompositionPackageDocument> {
    const response = await fetch(`${this.apiBaseUrl}/compositions/packages/${encodeURIComponent(compositionId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(composition),
    });
    if (!response.ok) throw await readError(response, "保存组卷包失败");
    return (await response.json()) as CompositionPackageDocument;
  }

  private filename(header: string | null, fallback: string): string {
    const encoded = header?.match(/filename\*=UTF-8''([^;]+)/i);
    if (encoded?.[1]) return decodeURIComponent(encoded[1]);
    const match = header?.match(/filename="?([^";]+)"?/i);
    return match?.[1] || fallback;
  }
}
