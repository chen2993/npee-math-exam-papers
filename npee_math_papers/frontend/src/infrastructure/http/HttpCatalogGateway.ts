import type { BundleQuery, CatalogGateway, PaperQuery } from "../../application/catalog/ports";
import type {
  Bundle,
  LogPage,
  LogQuery,
  Overview,
  PaperDocument,
  PaperPage,
  PaperSummary,
  QuestionContext,
  ReleaseManifest,
  SearchResult,
  Series,
} from "../../domain/catalog/models";
import { readError } from "./HttpError";
import { resolveApiBaseUrl } from "./apiBaseUrl";

export class HttpCatalogGateway implements CatalogGateway {
  constructor(private readonly apiBaseUrl: string = resolveApiBaseUrl()) {}

  overview(signal?: AbortSignal): Promise<Overview> {
    return this.request<Overview>("/overview", { signal });
  }

  async listSeries(signal?: AbortSignal): Promise<Series[]> {
    const payload = await this.request<{ series: Series[] }>("/series", { signal });
    return payload.series || [];
  }

  async listBundles(query: BundleQuery = {}, signal?: AbortSignal): Promise<Bundle[]> {
    const params = new URLSearchParams();
    (query.seriesKeys || []).forEach((key) => params.append("series_key", key));
    (query.years || []).forEach((year) => params.append("year", String(year)));
    (query.subjects || []).forEach((subject) => params.append("subject", subject));
    const suffix = params.size ? `?${params.toString()}` : "";
    const payload = await this.request<{ bundles: Bundle[] }>(`/bundles${suffix}`, { signal });
    return payload.bundles || [];
  }

  listPapers(query: PaperQuery, signal?: AbortSignal): Promise<PaperPage> {
    const params = new URLSearchParams();
    (query.seriesKeys || []).forEach((key) => params.append("series_key", key));
    (query.years || []).forEach((year) => params.append("year", String(year)));
    (query.subjects || []).forEach((subject) => params.append("subject", subject));
    (query.paperNos || []).forEach((paperNo) => params.append("paper_no", String(paperNo)));
    if (query.query) params.set("q", query.query);
    if (query.order) params.set("order", query.order);
    if (query.offset) params.set("offset", String(query.offset));
    if (query.limit) params.set("limit", String(query.limit));
    const suffix = params.size ? `?${params.toString()}` : "";
    return this.request<PaperPage>(`/papers${suffix}`, { signal });
  }

  getPaper(
    seriesKey: string,
    year: number,
    subject: string,
    paperNo: number,
    withQuestions: boolean,
    signal?: AbortSignal,
  ): Promise<PaperDocument | PaperSummary> {
    const suffix = withQuestions ? "" : "?with_questions=false";
    return this.request<PaperDocument | PaperSummary>(`/papers/${seriesKey}/${year}/${subject}/${paperNo}${suffix}`, { signal });
  }

  search(
    query: string,
    options: { seriesKeys?: string[]; subjects?: string[]; limit?: number; signal?: AbortSignal } = {},
  ): Promise<SearchResult> {
    const params = new URLSearchParams({ q: query });
    (options.seriesKeys || []).forEach((key) => params.append("series_key", key));
    (options.subjects || []).forEach((subject) => params.append("subject", subject));
    if (options.limit) params.set("limit", String(options.limit));
    return this.request<SearchResult>(`/search?${params.toString()}`, { signal: options.signal });
  }

  getQuestion(
    seriesKey: string,
    year: number,
    subject: string,
    paperNo: number,
    questionNo: number,
    signal?: AbortSignal,
  ): Promise<QuestionContext> {
    return this.request<QuestionContext>(`/papers/${seriesKey}/${year}/${subject}/${paperNo}/questions/${questionNo}`, {
      signal,
    });
  }

  releaseManifest(signal?: AbortSignal): Promise<ReleaseManifest> {
    return this.request<ReleaseManifest>("/release", { signal });
  }

  listLogs(query: LogQuery, signal?: AbortSignal): Promise<LogPage> {
    const params = new URLSearchParams();
    if (query.limit) params.set("limit", String(query.limit));
    if (query.surface) params.set("surface", query.surface);
    if (query.kind) params.set("kind", query.kind);
    if (query.status) params.set("status", query.status);
    if (query.q) params.set("q", query.q);
    const suffix = params.size ? `?${params.toString()}` : "";
    return this.request<LogPage>(`/logs${suffix}`, { signal });
  }

  async clearLogs(signal?: AbortSignal): Promise<void> {
    await fetch(`${this.apiBaseUrl}/logs/clear`, { method: "POST", signal });
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const response = await fetch(`${this.apiBaseUrl}${path}`, { cache: "no-store", ...init });
    if (!response.ok) {
      throw await readError(response, "NPEE 服务");
    }
    return response.json() as Promise<T>;
  }
}
