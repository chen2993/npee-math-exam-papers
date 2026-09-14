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

/** Ordering modes accepted by the paper list endpoint. */
export type PaperOrder =
  | "series"
  | "year-desc"
  | "year-asc"
  | "questions-desc"
  | "questions-asc";

export interface PaperQuery {
  seriesKeys?: string[];
  years?: number[];
  subjects?: string[];
  paperNos?: number[];
  /** Case-insensitive substring match over the paper's display fields. */
  query?: string;
  /** Result ordering; the server defaults to the natural series order. */
  order?: PaperOrder;
  offset?: number;
  limit?: number;
}

/** Filter for the bundle list; mirrors the paper filters. */
export interface BundleQuery {
  seriesKeys?: string[];
  years?: number[];
  subjects?: string[];
}

export interface CatalogGateway {
  overview(signal?: AbortSignal): Promise<Overview>;
  listSeries(signal?: AbortSignal): Promise<Series[]>;
  listBundles(query?: BundleQuery, signal?: AbortSignal): Promise<Bundle[]>;
  listPapers(query: PaperQuery, signal?: AbortSignal): Promise<PaperPage>;
  getPaper(
    seriesKey: string,
    year: number,
    subject: string,
    paperNo: number,
    withQuestions: boolean,
    signal?: AbortSignal,
  ): Promise<PaperDocument | PaperSummary>;
  search(
    query: string,
    options?: { seriesKeys?: string[]; subjects?: string[]; limit?: number; signal?: AbortSignal },
  ): Promise<SearchResult>;
  getQuestion(
    seriesKey: string,
    year: number,
    subject: string,
    paperNo: number,
    questionNo: number,
    signal?: AbortSignal,
  ): Promise<QuestionContext>;
  releaseManifest(signal?: AbortSignal): Promise<ReleaseManifest>;
  listLogs(query: LogQuery, signal?: AbortSignal): Promise<LogPage>;
  clearLogs(signal?: AbortSignal): Promise<void>;
}
